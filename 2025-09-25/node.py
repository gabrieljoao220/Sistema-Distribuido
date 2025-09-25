import random
import time

class Node:
    def __init__(self, node_id, total_nodes):
        self.node_id = node_id
        self.clock = 0
        self.total_nodes = total_nodes

    def internal_event(self):
        self.clock += 1
        print(f"Nó {self.node_id}: Evento interno | Relógio = {self.clock}")

    def send_event(self, target_node):
        self.clock += 1
        print(f"Nó {self.node_id}: Enviando mensagem para Nó {target_node.node_id} | Relógio = {self.clock}")
        target_node.receive_event(self.clock, self.node_id)

    def receive_event(self, received_clock, sender_id):
        self.clock = max(self.clock, received_clock) + 1
        print(f"Nó {self.node_id}: Recebeu mensagem de Nó {sender_id} | Relógio = {self.clock}")

def main():
    num_nodes = 3
    nodes = [Node(i, num_nodes) for i in range(num_nodes)]

    eventos = [
        lambda: nodes[0].internal_event(),
        lambda: nodes[1].internal_event(),
        lambda: nodes[2].internal_event(),
        lambda: nodes[0].send_event(nodes[1]),
        lambda: nodes[1].send_event(nodes[2]),
        lambda: nodes[2].send_event(nodes[0]),
    ]

    for i in range(10):
        print(f"\n--- Interação {i+1} ---")
        evento = random.choice(eventos)
        evento()
        time.sleep(1)

if __name__ == "__main__":
    main()