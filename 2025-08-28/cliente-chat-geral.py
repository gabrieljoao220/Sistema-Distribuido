import requests


def enviar_mensagem(base_url, nome, texto):
    msg = {"nome": nome, "mensagem": texto}
    try:
        resp = requests.post(base_url, json=msg, timeout=5)
        if resp.status_code == 202:
            print("Mensagem enviada com sucesso!")
        else:
            print("Erro ao enviar mensagem:", resp.status_code, resp.text)
    except requests.exceptions.RequestException as e:
        print("Erro de conexão:", e)


def buscar_mensagens(base_url):
    try:
        resp = requests.get(base_url, timeout=5)
        if resp.status_code == 200:
            msgs = resp.json()
            print("\n--- Chat ---")
            for m in msgs:
                print(f"{m['nome']}: {m['mensagem']}")
            print("------------\n")
        else:
            print("Erro ao buscar mensagens:", resp.status_code, resp.text)
    except requests.exceptions.RequestException as e:
        print("Erro de conexão:", e)


if __name__ == "__main__":
    ip = input("Digite o IP do servidor (ex: 192.168.1.100): ").strip()
    base_url = f"http://{ip}:8000/dados"
    nome = input("Digite seu nome: ")

    while True:
        texto = input("Digite sua mensagem (ou 'sair' para encerrar): ")
        if texto.lower() == "sair":
            break
        enviar_mensagem(base_url, nome, texto)
        buscar_mensagens(base_url)
