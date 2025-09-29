import http.server
import socketserver
import json
import requests
import sys
import threading
from typing import Dict, Tuple

# =================== CONFIGURAÇÕES ===================
# ID e porta devem ser passados via linha de comando:
# Exemplo: python server_ring_json.py 1 8000
ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

# Dicionário com todos os nós do anel (ID -> URL base)
# Dicionário com todos os nós do anel (ID -> URL base)
nos_conectados: Dict[str, str] = {
    "1": "http://127.0.0.1:8000",
    "2": "http://127.0.0.1:8001",
    "3": "http://127.0.0.1:8002",
}

coordenador_id = None  # ID do coordenador atual
# =====================================================


# -------- Função auxiliar: próximo no do anel --------
def proximo_no() -> Tuple[int, str]:
    ids = sorted([int(x) for x in nos_conectados.keys()])
    pos = ids.index(ID)
    prox_id = ids[(pos + 1) % len(ids)]
    return prox_id, nos_conectados[str(prox_id)]


def send_to_next(path: str, payload: dict):
    """Envia mensagem ao próximo nó no anel"""
    prox_id, prox_url = proximo_no()
    try:
        requests.post(f"{prox_url}{path}", json=payload, timeout=5)
        print(f"[enviado] -> Nó {prox_id} {path}: {payload}")
    except Exception as e:
        print(f"[erro] Falha ao enviar para Nó {prox_id}: {e}")


# -------- Handlers HTTP --------
class NossoHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    def do_GET(self):
        if self.path == "/coordenador":
            self._send_json(200, {"coordenador": coordenador_id})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global coordenador_id

        if self.path == "/eleicao":
            dado = self._read_json()
            iniciador = int(dado["iniciador"])
            ids = [int(x) for x in dado.get("ids", [])]
            participando = dado.get("participando", {})

            # Marca que este nó está participando
            if str(ID) not in participando:
                participando[str(ID)] = True
            if ID not in ids:
                ids.append(ID)

            print(f"[eleicao] Nó {ID} participando da eleição. Estado: {participando}")

            # Salva em arquivo local
            with open(f"eleicao_node{ID}.json", "w", encoding="utf-8") as f:
                json.dump({
                    "iniciador": iniciador,
                    "ids": ids,
                    "participando": participando
                }, f, ensure_ascii=False, indent=2)

            # Responde IMEDIATAMENTE para o nó anterior
            self._send_json(200, {"status": "ok"})

            # E SÓ DEPOIS, repassa a mensagem em uma thread
            if iniciador == ID:
                print(f"[resultado] Coordenador eleito: Nó {max(ids)}")
                # Usar thread aqui também é uma boa prática
                threading.Thread(target=anunciar_coordenador, args=(max(ids),)).start()
            else:
                payload = {"iniciador": iniciador, "ids": ids, "participando": participando}
                # Repassa para o próximo em uma tarefa de fundo
                threading.Thread(target=send_to_next, args=("/eleicao", payload)).start()
            return

        elif self.path == "/coordenador":
            dado = self._read_json()
            coordenador_id = dado["coordenador"]
            origem = int(dado["origem"])
            print(f"[coordenador] Anúncio recebido: coordenador é Nó {coordenador_id}")

            # Responde IMEDIATAMENTE
            self._send_json(200, {"status": "ok"})

            # E repassa a notícia em uma thread
            prox_id, _ = proximo_no()
            if prox_id != origem:
                payload = {"coordenador": coordenador_id, "origem": origem}
                threading.Thread(target=send_to_next, args=("/coordenador", payload)).start()

            return

        self.send_response(404)
        self.end_headers()


# -------- Lógica da eleição --------
def iniciar_eleicao():
    """Inicia uma eleição no anel"""
    print(f"[iniciar] Nó {ID} iniciou eleição")
    payload = {"iniciador": ID, "ids": [ID], "participando": {str(ID): True}}
    send_to_next("/eleicao", payload)


def anunciar_coordenador(vencedor: int):
    """Anuncia o vencedor a todos no anel"""
    payload = {"coordenador": vencedor, "origem": ID}
    send_to_next("/coordenador", payload)


# -------- Servidor --------
class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with ThreadingTCPServer(("", PORT), NossoHandler) as httpd:
        print(f"Nó {ID} servindo em porta {PORT}")
        if ID == 1:
            # Apenas nó 1 inicia eleição no começo
            iniciar_eleicao()
        httpd.serve_forever()
