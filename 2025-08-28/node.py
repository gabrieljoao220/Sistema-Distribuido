import http.server
import socketserver
import json

PORT = 8000
lista = []

# Criem um cliente em python usando a biblioteca requests
# para inserir itens na lista do servidor e ler itens e
# exibir para o usuário.


class NossoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/dados":
            dado = json.dumps(lista, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dado)))
            self.end_headers()
            self.wfile.write(dado)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/dados":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                dado = json.loads(body)
                lista.append(dado)  # adiciona o conteúdo do JSON na lista
                resp = {"status": "ok", "tamanho": len(lista)}
                resp_bytes = json.dumps(resp, ensure_ascii=False).encode("utf-8")
                self.send_response(202)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(resp_bytes)))
                self.end_headers()
                self.wfile.write(resp_bytes)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


with socketserver.TCPServer(("", PORT), NossoHandler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
