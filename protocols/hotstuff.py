from simulator.node import Node

class HotStuffNode(Node):
    """
    Упрощённая модель HotStuff для симуляции масштабируемости.
    """

    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n          # общее число узлов
        self.f = f          # допустимое число Byzantine узлов
        self.prepares = set()
        self.commits = set()
        self.round_started = False
        self.decided = False
        self.round_start_time = None

    # ===========================
    # Запуск раунда
    # ===========================
    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_start_time = self.env.now

        if self.node_id == 0:  # лидер (primary)
            for i in range(self.n):
                self.send(i, "PROPOSE")

    # ===========================
    # Обработка сообщений
    # ===========================
    def handle(self, src, msg):
        if self.decided:
            return  # Игнорируем после решения

        if msg == "PROPOSE":
            # Респондер рассылает PREPARE
            for i in range(self.n):
                self.send(i, "PREPARE")

        elif msg == "PREPARE":
            self.prepares.add(src)
            # Если собрано 2f+1 PREPARE, рассылаем COMMIT
            if len(self.prepares) >= 2 * self.f + 1 and "COMMIT_SENT" not in self.__dict__:
                self.__dict__["COMMIT_SENT"] = True
                for i in range(self.n):
                    self.send(i, "COMMIT")

        elif msg == "COMMIT":
            self.commits.add(src)
            # Если собрано 2f+1 COMMIT, принимаем решение (DECIDE)
            if len(self.commits) >= 2 * self.f + 1:
                self.decide()

    # ===========================
    # Завершение раунда
    # ===========================
    def decide(self):
        round_time = self.env.now - self.round_start_time
        if self.node_id == 0:
            self.metrics.record_round_finished("global", round_time)

        # Сбрасываем для нового раунда
        self.prepares.clear()
        self.commits.clear()
        self.round_started = False
        self.decided = False
        self.round_start_time = None

        self.env.process(self._start_next_round())


    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()

