from simulator.node import Node

class PBFTNode(Node):
    """
    Простая модель PBFT для симуляции масштабируемости с учётом времени раунда.
    """

    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n          # общее число узлов
        self.f = f          # допустимое число Byzantine узлов
        self.prepares = set()
        self.commits = set()
        self.round_started = False
        self.round_start_time = None
        self.commit_sent = False  # флаг отправки COMMIT в текущем раунде

    # ===========================
    # Запуск раунда
    # ===========================
    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_start_time = self.env.now  # фиксируем время старта раунда

        if self.node_id == 0:  # primary
            # Primary рассылает PRE-PREPARE всем
            for i in range(self.n):
                self.send(i, "PRE-PREPARE")

    # ===========================
    # Обработка сообщений
    # ===========================
    def handle(self, src, msg):
        if msg == "PRE-PREPARE":
            # Респондер рассылает PREPARE
            for i in range(self.n):
                self.send(i, "PREPARE")

        elif msg == "PREPARE":
            self.prepares.add(src)
            # Если получено 2f+1 PREPARE, рассылаем COMMIT
            if len(self.prepares) >= 2 * self.f + 1 and not self.commit_sent:
                self.commit_sent = True
                for i in range(self.n):
                    self.send(i, "COMMIT")

        elif msg == "COMMIT":
            self.commits.add(src)
            # Если получено 2f+1 COMMIT, раунд завершён
            if len(self.commits) >= 2 * self.f + 1:
                self.round_finished()

    # ===========================
    # Завершение раунда
    # ===========================
    def round_finished(self):
        if self.round_start_time is None:
            round_time = None
        else:
            round_time = self.env.now - self.round_start_time  # считаем длительность раунда

        # Каждый узел фиксирует своё время раунда для честной статистики
        self.metrics.record_round_finished(self.node_id, round_time)
        # Сбрасываем счётчики для возможного следующего раунда
        self.prepares.clear()
        self.commits.clear()
        self.round_started = False
        self.round_start_time = None
        self.commit_sent = False  # сбрасываем для следующего раунда

        self.env.process(self._start_next_round())


    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()