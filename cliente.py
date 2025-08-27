import requests


def main():

    try:
        resp = requests.get("http://10.80.30.82:8000", timeout=10)
        print("Resp: serv", resp.text)
    except requests.RequestException as e:
        print("Erro ao conectar", e)


if __name__ == "__main__":
    main()
