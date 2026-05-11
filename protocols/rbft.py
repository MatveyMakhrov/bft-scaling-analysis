from simulator.node import Node

class RBFTNode(Node):
    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n
        self.f = f
        self.prepares = set()
        self.commits = set()
        self.round_number = 0
        self.round_started = False
        self.round_start_time = None  # для измерения времени раунда
        self.commit_sent = False      # флаг отправки COMMIT в текущем раунде
        self.pre_prepare_received = False  # получен ли PRE-PREPARE в этом раунде

    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_number += 1
        self.round_start_time = self.env.now
        self.pre_prepare_received = False

        # Ротация лидера с имитацией отказа
        leader = self.round_number % self.n
        if self.node_id == leader and self.round_number % 3 != 0:  # иногда лидер "падает"
            for i in range(self.n):
                self.send(i, "PRE-PREPARE")

        # Все узлы запускают таймер view-change:
        # если PRE-PREPARE не придёт за отведённое время — переходим к следующему раунду
        self.env.process(self._view_change_timeout())

    def _view_change_timeout(self):
        """
        Имитация view-change: если лидер упал и не прислал PRE-PREPARE,
        узлы через таймаут самостоятельно переходят к следующему раунду.
        """
        # Таймаут = 3 средних сетевых задержки — достаточно, чтобы честный лидер успел
        yield self.env.timeout(self.network.delay_mean * 3)
        if self.round_started and not self.pre_prepare_received:
            # PRE-PREPARE так и не пришёл — лидер упал, форсируем переход
            self.round_started = False
            self.prepares.clear()
            self.commits.clear()
            self.round_start_time = None
            self.commit_sent = False
            self.pre_prepare_received = False
            self.env.process(self._start_next_round())

    def handle(self, src, msg):
        if msg == "PRE-PREPARE":
            self.pre_prepare_received = True  # отмечаем — лидер живой, таймер не сработает
            for i in range(self.n):
                self.send(i, "PREPARE")

        elif msg == "PREPARE":
            self.prepares.add(src)
            if len(self.prepares) >= 2 * self.f + 1 and not self.commit_sent:
                self.commit_sent = True
                for i in range(self.n):
                    self.send(i, "COMMIT")

        elif msg == "COMMIT":
            self.commits.add(src)
            if len(self.commits) >= 2 * self.f + 1:
                self.round_finished()

    def round_finished(self):
        # вычисляем длительность раунда
        round_time = None
        if self.round_start_time is not None:
            round_time = self.env.now - self.round_start_time

        # записываем в метрики
        # Каждый узел фиксирует своё время раунда для честной статистики
        self.metrics.record_round_finished(self.node_id, round_time)
        self.round_started = False
        self.prepares.clear()
        self.commits.clear()
        self.round_start_time = None
        self.commit_sent = False
        self.pre_prepare_received = False

        self.env.process(self._start_next_round())

    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()