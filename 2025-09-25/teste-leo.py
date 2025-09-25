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
    r = requests.post(f"{SERVER}/start_election", timeout=3)
    print("Start election:", r.status_code, r.text)

if __name__ == "__main__":
    while True:
        print("\n1 Inserir  2 Listar  3 Ver coordenador  4 Iniciar eleição  0 Sair")
        op = input("> ").strip()
        if op == "1":
            remetente = int(input("remetente id: "))
            msg = input("mensagem: ")
            inserir_item(remetente, msg)
        elif op == "2":
            listar_itens()
        elif op == "3":
            ver_coordenador()
        elif op == "4":
            start_election()
        elif op == "0":
            break
        else:
            print("opção inválida")
