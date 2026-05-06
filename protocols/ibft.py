from simulator.node import Node

class IBFTNode(Node):
    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n
        self.f = f
        self.prepares = set()
        self.commits = set()
        self.round_number = 0
        self.round_started = False
        self.round_start_time = None  # для замера времени раунда

    # ===========================
    # Запуск нового раунда
    # ===========================
    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_number += 1
        self.round_start_time = self.env.now  # фиксируем время начала раунда

        leader = self.round_number % self.n
        if self.node_id == leader:
            for i in range(self.n):
                self.send(i, "PRE-PREPARE")

    # ===========================
    # Обработка сообщений
    # ===========================
    def handle(self, src, msg):
        if msg == "PRE-PREPARE":
            for i in range(self.n):
                self.send(i, "PREPARE")

        elif msg == "PREPARE":
            self.prepares.add(src)
            if len(self.prepares) >= 2 * self.f + 1 and "COMMIT_SENT" not in self.__dict__:
                self.__dict__["COMMIT_SENT"] = True
                for i in range(self.n):
                    self.send(i, "COMMIT")

        elif msg == "COMMIT":
            self.commits.add(src)
            if len(self.commits) >= 2 * self.f + 1:
                self.round_finished()

    # ===========================
    # Завершение раунда
    # ===========================
    def round_finished(self):
        round_time = None
        if self.round_start_time is not None:
            round_time = self.env.now - self.round_start_time

        if self.node_id == 0:
            self.metrics.record_round_finished("global", round_time)
        self.round_started = False
        self.prepares.clear()
        self.commits.clear()
        self.round_start_time = None

        self.env.process(self._start_next_round())


    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()
