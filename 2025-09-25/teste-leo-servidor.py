#!/usr/bin/env python3
"""
server_ring_step_by_step.py
Servidor HTTP simples que mantém um "mural" e implementa
o algoritmo de eleição em anel para escolher um coordenador.
Uso (exemplo local com 3 nós):
python3 server_ring_step_by_step.py --id 1 --port 8001 --peers "1=http://127.0.0.1:8001,2=http://127.0.0.1:8002,3=http://127.0.0.1:8003"
"""
import argparse
import http.server
import socketserver
import json
import requests
import threading
import time
from typing import Dict

# --- parâmetros padrão ---
TIMEOUT = 2  # timeout para requests (s)

# --- parse args (ID, PORT, PEERS) ---
parser = argparse.ArgumentParser(description="Servidor em anel com eleição")
parser.add_argument("--id", type=int, required=True, help="ID numérico do nó")
parser.add_argument("--port", type=int, required=True, help="Porta HTTP do nó")
parser.add_argument(
    "--peers",
    type=str,
    required=True,
    help='Lista de pares id=url separados por vírgula. Ex: "1=http://127.0.0.1:8001,2=http://127.0.0.1:8002"',
)
parser.add_argument("--no-auto", action="store_true", help="Não iniciar eleição automaticamente")
args = parser.parse_args()

ID = args.id
PORT = args.port

def parse_peers(s: str) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError("Formato de --peers inválido")
        k, v = part.split("=", 1)
        d[k.strip()] = v.strip().rstrip("/")  # remove / final
    return d

peers: Dict[str, str] = parse_peers(args.peers)

# se o usuário não incluiu o próprio nó na lista, adicionamos com localhost:PORT
if str(ID) not in peers:
    peers[str(ID)] = f"http://127.0.0.1:{PORT}"

# estado do nó
lista = []  # mural local (lista de mensagens)
coordenador_id = None  # id do coordenador conhecido
lock = threading.Lock()

def sorted_ids():
    """Retorna IDs ordenados (lista de ints)."""
    ids = sorted({int(x) for x in peers.keys()})
    return ids

def send_to_next(path: str, payload: dict) -> bool:
    """
    Tenta enviar `payload` para o próximo nó no anel,
    pulando nós não responsivos (tenta todos os nós uma vez).
    Retorna True se algum nó respondeu com status < 400.
    """
    ids = sorted_ids()
    if ID not in ids:
        ids = sorted(ids + [ID])
    idx = ids.index(ID)
    n = len(ids)
    for offset in range(1, n):
        nid = ids[(idx + offset) % n]
        url = peers.get(str(nid))
        if not url:
            continue
        try:
            full = f"{url}{path}"
            print(f"[send_to_next] tentando {nid} -> {full}")
            r = requests.post(full, json=payload, timeout=TIMEOUT)
            if r.status_code < 400:
                return True
        except Exception as e:
            print(f"[WARN] falha ao enviar para {nid} ({url}{path}): {e}")
            continue
    print("[WARN] nenhum vizinho respondeu ao tentar enviar para", path)
    return False

def iniciar_eleicao():
    """Inicia eleição: envia mensagem para o próximo com ids=[ID]."""
    global coordenador_id
    print("⚡ Iniciando eleição no anel (iniciador =", ID, ")")
    payload = {"iniciador": ID, "ids": [ID]}
    ok = send_to_next("/eleicao", payload)
    if not ok:
        # se não conseguiu contatar ninguém, eu me torno coordenador (nó isolado)
        coordenador_id = ID
        print(f"✅ Nenhum vizinho disponível: eu ({ID}) virei coordenador.")

def anunciar_coordenador(vencedor: int):
    """Circula anúncio do coordenador no anel (origem = initiador)."""
    global coordenador_id
    coordenador_id = vencedor
    payload = {"coordenador": vencedor, "origem": ID}
    print(f"📢 Anunciando coordenador {vencedor} a partir de {ID}")
    send_to_next("/coordenador", payload)

class Handler(http.server.BaseHTTPRequestHandler):
    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def _send_json(self, code: int, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # GET endpoints: /dados, /coordenador, /ping
    def do_GET(self):
        if self.path == "/dados":
            with lock:
                self._send_json(200, lista)
        elif self.path == "/coordenador":
            with lock:
                self._send_json(200, {"coordenador": coordenador_id})
        elif self.path == "/ping":
            with lock:
                self._send_json(200, {"id": ID, "coordenador": coordenador_id})
        else:
            self.send_response(404)
            self.end_headers()

    # POST endpoints: /dados, /eleicao, /coordenador, /start_election
    def do_POST(self):
        global coordenador_id
        try:
            if self.path == "/dados":
                dado = self._read_json()
                with lock:
                    lista.append(dado)
                    tamanho = len(lista)
                resp = {"status": "ok", "tamanho": tamanho}
                self._send_json(202, resp)
                return

            elif self.path == "/eleicao":
                dado = self._read_json()
                iniciador = int(dado["iniciador"])
                ids = [int(x) for x in dado.get("ids", [])]
                # se meu ID ainda não estiver na lista, adiciono
                if ID not in ids:
                    ids.append(ID)
                print(f"[eleicao] recebi eleicao de {iniciador}, ids={ids}")
                # se sou o iniciador (a mensagem voltou), finaliza-se a eleição
                if iniciador == ID:
                    vencedor = max(ids)
                    print(f"[eleicao] circuicao completa; vencedor = {vencedor}")
                    coordenador_id = vencedor
                    # iniciar anúncio do coordenador
                    anunciar_coordenador(vencedor)
                else:
                    # encaminhar adiante a lista atualizada
                    payload = {"iniciador": iniciador, "ids": ids}
                    send_to_next("/eleicao", payload)
                self._send_json(200, {"status": "ok"})
                return

            elif self.path == "/coordenador":
                dado = self._read_json()
                vencedor = int(dado["coordenador"])
                origem = int(dado.get("origem", -1))
                with lock:
                    coordenador_id = vencedor
                print(f"[coordenador] recebi anuncio: coordenador = {vencedor} (origem {origem})")
                # se a mensagem já deu a volta e chegou no origem, paramos
                if origem == ID:
                    print("[coordenador] anuncio retornou ao originador; fim da circulação.")
                else:
                    # encaminha adiante mantendo o campo "origem" (quem iniciou o anuncio)
                    payload = {"coordenador": vencedor, "origem": origem}
                    send_to_next("/coordenador", payload)
                self._send_json(200, {"status": "ok"})
                return

            elif self.path == "/start_election":
                # trigger manual para iniciar eleição neste nó
                threading.Thread(target=iniciar_eleicao, daemon=True).start()
                self._send_json(200, {"status": "election_started", "node": ID})
                return

            else:
                self.send_response(404)
                self.end_headers()
                return

        except Exception as e:
            print("[ERROR] exceção no handler:", e)
            self.send_response(500)
            self.end_headers()

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"Nó {ID} servindo em 0.0.0.0:{PORT}  — peers:", peers)
    # auto-start election (a menos que --no-auto)
    if not args.no_auto:
        # delay curto para dar tempo aos outros nós ligarem, se estiver testando localmente
        time.sleep(0.8)
        threading.Thread(target=iniciar_eleicao, daemon=True).start()

    with ThreadingTCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
