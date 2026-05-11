from simulator.node import Node

class HBBFTNode(Node):
    def __init__(self, env, node_id, network, metrics, n, f, batch_size=2):
        super().__init__(env, node_id, network, metrics)
        self.n = n
        self.f = f
        self.batch_size = batch_size
        self.batch = []
        self.round_started = False
        self.round_number = 0
        self.acks = {}
        self.round_start_time = None
        self.committed = set()

    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_number += 1
        self.batch = []
        self.acks = {}
        self.committed = set()
        self.round_start_time = self.env.now
        # Каждый узел предлагает столько транзакций, чтобы гарантировать batch_size
        for i in range(self.batch_size):
            self.propose_tx(f"tx_from_{self.node_id}_r{self.round_number}_#{i+1}")

    def propose_tx(self, tx):
        self.batch.append(tx)
        for i in range(self.n):
            self.send(i, ("PROPOSE", tx))

    def handle(self, src, msg):
        msg_type = msg[0]

        if msg_type == "PROPOSE":
            tx = msg[1]
            if tx not in self.batch:
                self.batch.append(tx)
                self.send(src, ("ACK", tx))

        elif msg_type == "ACK":
            tx = msg[1]
            if tx not in self.acks:
                self.acks[tx] = set()
            self.acks[tx].add(src)

            if len(self.acks[tx]) >= self.n - self.f and tx not in self.committed:
                self.committed.add(tx)
                # Если набралось batch_size транзакций, раунд завершён
                if len(self.committed) >= self.batch_size:
                    self.round_finished()

    def round_finished(self):
        if hasattr(self, "round_start_time"):
            round_time = self.env.now - self.round_start_time
        else:
            round_time = None
        # Каждый узел фиксирует своё время раунда для честной статистики
        self.metrics.record_round_finished(self.node_id, round_time)
        self.round_started = False

        self.env.process(self._start_next_round())


    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()