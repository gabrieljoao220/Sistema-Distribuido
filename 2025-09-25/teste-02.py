import http.server
import socketserver
import json
import requests
import threading
import uuid
import time
from typing import Dict, List, Set, Optional

# ========= CONFIG =========
NODE_ID = 3  # identifique este nó (inteiro único)
PORT = 8000  # porta local deste nó
nos_conectados: Dict[str, str] = {  # outros nós: id -> base_url
    "1": "http://10.80.31.122:8000",
}
L: int = 0  # Nosso relógio lógico (Lamport)
# ==========================

# ========= DADOS =========
lista: List[dict] = []  # mural local
seen_msgs: Set[str] = set()  # mensagens já vistas (para deduplicar)
lock = threading.Lock()
# ==========================


# ========= ELEIÇÃO (NOVO) =========
COORDENADOR_ATUAL: Optional[int] = None
EM_ELEICAO = threading.Event() # Usamos um Event para sinalizar estado de eleição
# ==================================

DEFAULT_TTL = 5
TIMEOUT_S = 3

# ================= Cuidando do relógio de Lamport =================
# (Sem alterações aqui, seu código já estava correto)
def lamport_event_internal() -> int:
    global L
    with lock:
        L += 1
        return L

def lamport_on_send() -> int:
    global L
    with lock:
        L += 1
        return L

def lamport_on_receive(incoming_ts: int | None) -> int:
    global L
    with lock:
        if incoming_ts is None:
            L += 1
        else:
            L = max(L, int(incoming_ts)) + 1
        return L

# ================= Net helpers =================
def safe_post(url: str, payload: dict) -> Optional[requests.Response]:
    """Tenta enviar um POST, retorna a resposta ou None em caso de falha."""
    try:
        # Adiciona o timestamp de Lamport a todas as mensagens enviadas
        ts = lamport_on_send()
        pacote = dict(payload)
        pacote["lc"] = ts
        pacote["remetente"] = NODE_ID

        response = requests.post(url, json=pacote, timeout=TIMEOUT_S)
        response.raise_for_status() # Lança exceção para códigos de erro HTTP
        return response
    except requests.RequestException as e:
        print(f"[WARN] Falha ao enviar para {url}: {e}")
        return None

# ================= Lógica de Eleição (NOVO) =================

def anunciar_vitoria():
    """Anuncia para todos os nós que este nó é o novo coordenador."""
    global COORDENADOR_ATUAL

    with lock:
        COORDENADOR_ATUAL = NODE_ID
        EM_ELEICAO.clear() # Finaliza o estado de eleição

    print(f"👑 EU, NÓ {NODE_ID}, SOU O NOVO COORDENADOR!")

    payload = {"coordenador_id": NODE_ID}
    for node_id, base_url in nos_conectados.items():
        if int(node_id) != NODE_ID:
            safe_post(f"{base_url}/coordenador", payload)

def iniciar_eleicao():
    """Inicia um processo de eleição enviando mensagens para nós com ID maior."""
    if EM_ELEICAO.is_set():
        print("Já existe uma eleição em andamento.")
        return

    print(f"[ELEIÇÃO] Nó {NODE_ID} iniciando uma eleição.")
    EM_ELEICAO.set() # Marca que estamos em eleição

    nos_superiores = [
        (int(id_str), base) for id_str, base in nos_conectados.items() if int(id_str) > NODE_ID
    ]

    if not nos_superiores:
        # Não há ninguém maior, então eu ganho por padrão
        anunciar_vitoria()
        return

    respostas_ok = 0
    threads = []

    def enviar_msg_eleicao(url):
        nonlocal respostas_ok
        response = safe_post(url, {"tipo": "eleicao"})
        if response and response.status_code == 200:
            with lock:
                respostas_ok += 1

    for _, base_url in nos_superiores:
        t = threading.Thread(target=enviar_msg_eleicao, args=(f"{base_url}/eleicao",))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=TIMEOUT_S)

    if respostas_ok == 0:
        # Ninguém superior respondeu, eu ganhei!
        anunciar_vitoria()
    else:
        # Alguém superior respondeu, ele vai continuar a eleição.
        print(f"[ELEIÇÃO] Recebi resposta de um nó superior. Vou aguardar.")
        # Aguarda um tempo para um novo coordenador ser anunciado
        time.sleep(TIMEOUT_S * 2)
        if EM_ELEICAO.is_set(): # Se ninguém foi eleito, tenta de novo
            EM_ELEICAO.clear()
            print("[ELEIÇÃO] Nenhum coordenador anunciado. Tentando novamente...")
            iniciar_eleicao()

def health_check_coordenador():
    """Thread que verifica periodicamente se o coordenador está ativo."""
    while True:
        time.sleep(10) # Verifica a cada 10 segundos

        with lock:
            coord_id = COORDENADOR_ATUAL

        if coord_id is None or coord_id == NODE_ID:
            continue # Não há coordenador ou eu sou o coordenador

        url_coord = nos_conectados.get(str(coord_id))
        if not url_coord:
            continue

        try:
            requests.get(f"{url_coord}/ping", timeout=TIMEOUT_S)
        except requests.RequestException:
            print(f"🚨 Coordenador {coord_id} parece estar offline! Iniciando nova eleição.")
            iniciar_eleicao()

# ================= Sincronização inicial =================
# (Sem alterações aqui)
def sync_with_peers():
    global lista, seen_msgs, L
    for id_str, base in nos_conectados.items():
        try:
            r = requests.get(f"{base}/dados?ordenado=1", timeout=TIMEOUT_S)
            if r.status_code == 200:
                dados_remotos = r.json()
                with lock:
                    for msg in dados_remotos:
                        msg_id = msg.get("msg_id")
                        if msg_id and msg_id not in seen_msgs:
                            seen_msgs.add(msg_id)
                            lista.append(msg)
                            L = max(L, msg.get("lc", 0)) + 1
                print(f"[SYNC] Sincronizado com nó {id_str}, {len(dados_remotos)} msgs")
        except Exception as e:
            print(f"[SYNC] Falha ao sincronizar com nó {id_str}: {e}")

# ================= HTTP Handler =================
class NossoHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict | list):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_simple_response(self, code: int, msg: str = ""):
        self.send_response(code)
        self.end_headers()
        if msg:
            self.wfile.write(msg.encode('utf-8'))

    def do_GET(self):
        if self.path.startswith("/dados"):
            with lock:
                if "ordenado=1" in self.path:
                    ordenada = sorted(
                        lista,
                        key=lambda x: (
                            x.get("lc", 0),
                            x.get("origem", 0),
                            x.get("msg_id", ""),
                        ),
                    )
                    self._send_json(200, ordenada)
                else:
                    self._send_json(200, lista)
        elif self.path == "/ping":
            self._send_json(200, {"status": "ok", "node": NODE_ID, "lc": L})
        ### NOVO: Endpoint para ver o status e o coordenador
        elif self.path == "/status":
            with lock:
                self._send_json(200, {"node_id": NODE_ID, "coordenador": COORDENADOR_ATUAL, "em_eleicao": EM_ELEICAO.is_set(), "clock": L})
        else:
            self._send_simple_response(404, "Not Found")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            dado = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            return self._send_simple_response(400, "Bad Request")

        # Atualiza o relógio de Lamport ao receber QUALQUER mensagem
        incoming_ts = dado.get("lc")
        lamport_on_receive(incoming_ts)

        ### NOVO: Roteamento de POSTs para diferentes lógicas
        if self.path == "/eleicao":
            # Recebi uma mensagem de eleição de um nó com ID menor
            print(f"Recebi pedido de eleição de {dado.get('remetente')}. Respondendo OK e iniciando minha eleição.")
            self._send_simple_response(200, "OK") # Responde OK para o "valentão" menor
            threading.Thread(target=iniciar_eleicao, daemon=True).start() # Inicia minha própria eleição

        elif self.path == "/coordenador":
            novo_coordenador = dado.get("coordenador_id")
            with lock:
                global COORDENADOR_ATUAL
                COORDENADOR_ATUAL = novo_coordenador
                EM_ELEICAO.clear() # Fim da eleição
            print(f"👑 Nó {novo_coordenador} é o novo coordenador!")
            self._send_json(200, {"status": "ok"})

        elif self.path == "/dados":
            self.handle_dados_post(dado)

        else:
            self._send_simple_response(404, "Not Found")

    def handle_dados_post(self, dado: dict):
        # Lógica original de manipulação de dados
        remetente = int(dado.get("remetente", NODE_ID))
        origem = int(dado.get("origem", remetente))
        msg_id = dado.get("msg_id") or f"{origem}-{uuid.uuid4().hex}"

        dado.update({
            "remetente": remetente,
            "origem": origem,
            "msg_id": msg_id,
            "lc": L, # Usa o valor já atualizado do relógio
        })

        with lock:
            if msg_id in seen_msgs:
                self._send_json(200, {"status": "duplicate"})
                return

            seen_msgs.add(msg_id)
            lista.append(dado)

        self._send_json(202, {"status": "accepted", "msg_id": msg_id})

        # Replicação para outros nós
        # A lógica de broadcast agora é mais simples
        def broadcast(payload, exclude_id):
            for id_str, base_url in nos_conectados.items():
                if int(id_str) != exclude_id and int(id_str) != NODE_ID:
                    safe_post(f"{base_url}/dados", payload)

        threading.Thread(target=broadcast, args=(dado, remetente), daemon=True).start()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    sync_with_peers()

    # Inicia a primeira eleição ao iniciar o nó
    print("Iniciando processo de eleição inicial...")
    iniciar_eleicao()

    # Inicia a thread de health check para monitorar o coordenador
    health_checker = threading.Thread(target=health_check_coordenador, daemon=True)
    health_checker.start()

    with ThreadingTCPServer(("", PORT), NossoHandler) as httpd:
        print(f"Node {NODE_ID} servindo em 0.0.0.0:{PORT}")
        httpd.serve_forever()