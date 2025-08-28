import requests

BASE_URL = "http://localhost:8000/dados"


def adicionar_item(nome: str, idade: int):
    """Envia um item (nome e idade) para o servidor via POST."""
    dado = {"nome": nome, "idade": idade}
    resp = requests.post(BASE_URL, json=dado)
    if resp.status_code == 202:
        print("Item adicionado:", dado)
        print("Resposta do servidor:", resp.json())
    else:
        print("Erro ao adicionar item:", resp.status_code, resp.text)


def listar_itens():
    resp = requests.get(BASE_URL)
    if resp.status_code == 200:
        itens = resp.json()
        print("\nItens na lista do servidor:")
        for i, item in enumerate(itens, 1):
            if isinstance(item, dict):
                nome = item.get("nome", "N/A")
                idade = item.get("idade", "N/A")
                print(f"{i}. Nome: {nome}, Idade: {idade}")
            else:
                # item é string ou outro tipo
                print(f"{i}. {item}")
    else:
        print("❌ Erro ao buscar itens:", resp.status_code, resp.text)


if __name__ == "__main__":
    while True:
        print("\n1 - Adicionar item")
        print("2 - Listar itens")
        print("3 - Sair")
        escolha = input("Escolha: ")

        if escolha == "1":
            nome = input("Digite o nome: ")
            while True:
                try:
                    idade = int(input("Digite a idade: "))
                    break
                except ValueError:
                    print("Por favor, digite um número válido para a idade.")
            adicionar_item(nome, idade)
        elif escolha == "2":
            listar_itens()
        elif escolha == "3":
            break
        else:
            print("Opção inválida, tente novamente.")
