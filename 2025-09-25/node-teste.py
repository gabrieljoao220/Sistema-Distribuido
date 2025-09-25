import socket
import threading
import json
import time
import sys

class Node:
    def __init__(self, node_id, host, port, peers):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = peers
        self.lamport_clock = 0
        self.leader_id = None

        # Flag para controlar o estado da eleição. 'volatile' em Java.
        self.is_election_active = False
        # Lock para garantir operações atômicas no relógio e no estado da eleição
        self.lock = threading.Lock()

        self.server_thread = threading.Thread(target=self._listen)
        self.server_thread.daemon = True
        self.server_thread.start()

    def _increment_clock(self):
        self.lamport_clock += 1

    def _update_clock(self, received_time):
        self.lamport_clock = max(self.lamport_clock, received_time) + 1

    def _listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)
        print(f"[Nó {self.node_id}] Escutando em {self.host}:{self.port}")

        while True:
            conn, _ = server_socket.accept()
            handler_thread = threading.Thread(target=self._handle_connection, args=(conn,))
            handler_thread.daemon = True
            handler_thread.start()

    def _handle_connection(self, conn):
        try:
            data = conn.recv(1024).decode('utf-8')
            if data:
                message = json.loads(data)

                with self.lock:
                    original_clock = self.lamport_clock
                    self._update_clock(message['tempo_lamport'])
                    print(f"[Nó {self.node_id}] Mensagem '{message['tipo']}' de {message['remetente_id']}. Relógio: {original_clock} -> {self.lamport_clock}")

                self._process_message(message)
        except Exception as e:
            print(f"[Nó {self.node_id}] Erro ao receber mensagem: {e}")
        finally:
            conn.close()

    def _send_message(self, target_node_id, message_type, data={}):
        if target_node_id not in self.peers:
            return

        with self.lock:
            self._increment_clock()
            message = {
                'tipo': message_type,
                'remetente_id': self.node_id,
                'tempo_lamport': self.lamport_clock,
                'dados': data
            }
            current_clock = self.lamport_clock

        client_socket = None
        try:
            target_host, target_port = self.peers[target_node_id]
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2) # Timeout para evitar bloqueio indefinido
            client_socket.connect((target_host, target_port))
            client_socket.sendall(json.dumps(message).encode('utf-8'))
            print(f"[Nó {self.node_id}] Mensagem '{message_type}' enviada para {target_node_id}. Meu relógio: {current_clock}")
        except Exception as e:
            print(f"[Nó {self.node_id}] Falha ao enviar para {target_node_id}: {e}")
        finally:
            if client_socket:
                client_socket.close()

    def _broadcast(self, message_type, data={}):
        for peer_id in self.peers:
            if peer_id != self.node_id:
                self._send_message(peer_id, message_type, data)

    def _process_message(self, message):
        msg_type = message['tipo']
        remetente_id = message['remetente_id']

        if msg_type == 'ELEICAO':
            # Se meu ID é maior, eu respondo e começo minha própria eleição
            if self.node_id > remetente_id:
                self._send_message(remetente_id, 'RESPOSTA_ELEICAO')
                # Inicia uma nova eleição imediatamente se não houver uma ativa
                self.start_election()

        elif msg_type == 'RESPOSTA_ELEICAO':
            # Recebi uma resposta de um nó com ID maior.
            # Isso significa que não posso ser o líder. Cancelo minha candidatura.
            with self.lock:
                self.is_election_active = False
            print(f"[Nó {self.node_id}] Recebi resposta de um nó maior ({remetente_id}). Não sou o líder.")

        elif msg_type == 'LIDER':
            # Um novo líder foi anunciado. Atualizo meu estado.
            novo_lider_id = message['dados']['lider_id']
            with self.lock:
                self.leader_id = novo_lider_id
                self.is_election_active = False # Encerra qualquer processo de eleição
            print(f"\n====================\n[Nó {self.node_id}] NOVO LÍDER ELEITO: Nó {self.leader_id}\n====================\n")

    def start_election(self):
        with self.lock:
            # Verifica se uma eleição já está em andamento para evitar iniciar outra
            if self.is_election_active:
                print(f"[Nó {self.node_id}] Tentou iniciar eleição, mas uma já está ativa.")
                return
            print(f"[Nó {self.node_id}] INICIANDO ELEIÇÃO...")
            self.is_election_active = True

        # Envia mensagem de eleição para todos os nós com ID maior
        maiores_ids = [pid for pid in self.peers if pid > self.node_id]

        if not maiores_ids:
            # Se não há nós com ID maior, eu sou o líder por padrão
            print(f"[Nó {self.node_id}] Nenhum nó com ID maior detectado.")
            self._declare_leader()
            return

        # Transmite a mensagem de eleição
        for peer_id in maiores_ids:
            self._send_message(peer_id, 'ELEICAO')

        # Agenda uma verificação para daqui a 5 segundos.
        # Se até lá 'is_election_active' ainda for True, ninguém maior respondeu.
        threading.Timer(5.0, self._check_election_result).start()

    def _check_election_result(self):
        with self.lock:
            # Se a flag ainda estiver ativa, significa que ninguém maior respondeu.
            if self.is_election_active:
                print(f"[Nó {self.node_id}] Timeout da eleição. Nenhuma resposta de nós maiores.")
                self._declare_leader()
            else:
                print(f"[Nó {self.node_id}] Timeout da eleição, mas já recebi resposta de um nó maior. Eleição cancelada.")

    def _declare_leader(self):
        with self.lock:
            self.leader_id = self.node_id
            self.is_election_active = False
        print(f"\n====================\n[Nó {self.node_id}] EU SOU O NOVO LÍDER!\n====================\n")
        self._broadcast('LIDER', {'lider_id': self.node_id})

    def simulate_event(self):
        with self.lock:
            self._increment_clock()
            print(f"[Nó {self.node_id}] Evento local simulado. Meu relógio: {self.lamport_clock}")


def main():
    if len(sys.argv) != 3:
        print(f"Uso: python {sys.argv[0]} <node_id> <config_file>")
        sys.exit(1)

    node_id = int(sys.argv[1])
    config_file = sys.argv[2]

    with open(config_file, 'r') as f:
        config = json.load(f)

    if str(node_id) not in config:
        print(f"Erro: ID de nó {node_id} não encontrado no arquivo de configuração.")
        sys.exit(1)

    host = config[str(node_id)]['host']
    port = int(config[str(node_id)]['port'])

    peers = {int(nid): (cfg['host'], int(cfg['port'])) for nid, cfg in config.items()}

    node = Node(node_id, host, port, peers)

    print("Aguardando 10 segundos para a rede estabilizar...")
    time.sleep(10)

    while True:
        print("\nEscolha uma ação:")
        print("1. Iniciar Eleição de Líder")
        print("2. Simular Evento Local")
        print("3. Ver Estado Atual")
        print("4. Sair")

        choice = input(f"[Nó {node_id}] > ")
        if choice == '1':
            node.start_election()
        elif choice == '2':
            node.simulate_event()
        elif choice == '3':
            print(f"  - Meu ID: {node.node_id}")
            print(f"  - Relógio de Lamport: {node.lamport_clock}")
            print(f"  - Líder Atual: {node.leader_id if node.leader_id else 'Nenhum'}")
        elif choice == '4':
            print("Saindo...")
            break
        else:
            print("Opção inválida.")
        time.sleep(1)


if __name__ == "__main__":
    main()