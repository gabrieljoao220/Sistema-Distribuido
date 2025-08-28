import requests

BASE_URL = "http://:8000/dados"


def enviar_mensagem(nome, texto):
    msg = {"nome": nome, "mensagem": texto}
    resp = requests.post(BASE_URL, json=msg)
    if resp.status_code == 202:
        print("Mensagem enviada com sucesso!")
    else:
        print("Erro ao enviar mensagem:", resp.status_code, resp.text)


def buscar_mensagens():
    resp = requests.get(BASE_URL)
    if resp.status_code == 200:
        msgs = resp.json()
        print("\n--- Chat ---")
        for m in msgs:
            print(f"{m['nome']}: {m['mensagem']}")
        print("------------\n")
    else:
        print("Erro ao buscar mensagens:", resp.status_code, resp.text)


if __name__ == "__main__":
    nome = input("Digite seu nome: ")
    while True:
        texto = input("Digite sua mensagem (ou 'sair' para encerrar): ")
        if texto.lower() == "sair":
            break
        enviar_mensagem(nome, texto)
        buscar_mensagens()
