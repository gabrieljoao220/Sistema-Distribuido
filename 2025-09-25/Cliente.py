#!/usr/bin/env python3
import requests
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--server", type=str, required=True, help="URL do nó: ex http://127.0.0.1:8001")
args = parser.parse_args()

SERVER = args.server.rstrip("/")

def inserir_item(remetente:int, conteudo: str):
    dado = {"remetente": remetente, "conteudo": conteudo}
    r = requests.post(f"{SERVER}/dados", json=dado, timeout=3)
    print("Resposta:", r.status_code, r.text)

def listar_itens():
    r = requests.get(f"{SERVER}/dados", timeout=3)
    print("Itens:", json.dumps(r.json(), ensure_ascii=False, indent=2))

def ver_coordenador():
    r = requests.get(f"{SERVER}/coordenador", timeout=3)
    print("Coordenador:", r.json())

def start_election():
    """Inicia uma eleição a partir do nó conectado"""
    print(f"Pedindo para o Nó em {SERVER} iniciar uma eleição...")
    try:
        iniciador_id = int(input("Qual nó deve iniciar a eleição? (ex: 1): "))
        payload = {"iniciador": iniciador_id, "ids": [iniciador_id], "participando": {str(iniciador_id): True}}
        r = requests.post(f"{SERVER}/eleicao", json=payload, timeout=3)
        print("Resposta do início da eleição:", r.status_code, r.text)
    except Exception as e:
        print(f"Erro ao iniciar eleição: {e}")

if __name__ == "__main__":
    while True:
        print("\nOpções:")
        print("  3: Ver coordenador atual")
        print("  4: Iniciar uma nova eleição")
        print("  0: Sair")
        op = input("> ").strip()
        if op == "3":
            ver_coordenador()
        elif op == "4":
            start_election()
        elif op == "0":
            break
        else:
            print("opção inválida")
