from simulator.node import Node

class TendermintNode(Node):
    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n
        self.f = f
        self.prevotes = set()
        self.precommits = set()
        self.round_number = 0
        self.round_started = False
        self.round_start_time = None  # для замера времени раунда
        self.precommit_sent = False   # флаг отправки PRECOMMIT в текущем раунде

    # ===========================
    # Запуск нового раунда
    # ===========================
    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_number += 1
        self.round_start_time = self.env.now  # фиксируем начало раунда

        leader = self.round_number % self.n
        if self.node_id == leader:
            for i in range(self.n):
                self.send(i, "PROPOSAL")

    # ===========================
    # Обработка сообщений
    # ===========================
    def handle(self, src, msg):
        if msg == "PROPOSAL":
            for i in range(self.n):
                self.send(i, "PREVOTE")

        elif msg == "PREVOTE":
            self.prevotes.add(src)
            if len(self.prevotes) >= 2 * self.f + 1 and not self.precommit_sent:
                self.precommit_sent = True
                for i in range(self.n):
                    self.send(i, "PRECOMMIT")

        elif msg == "PRECOMMIT":
            # В Tendermint 2f+1 PRECOMMIT = решение принято, этап COMMIT отсутствует
            self.precommits.add(src)
            if len(self.precommits) >= 2 * self.f + 1:
                self.round_finished()

    # ===========================
    # Завершение раунда
    # ===========================
    def round_finished(self):
        round_time = None
        if self.round_start_time is not None:
            round_time = self.env.now - self.round_start_time

        # фиксируем метрики
        # Каждый узел фиксирует своё время раунда для честной статистики
        self.metrics.record_round_finished(self.node_id, round_time)

        # сбрасываем состояние раунда
        self.round_started = False
        self.prevotes.clear()
        self.precommits.clear()
        self.round_start_time = None
        self.precommit_sent = False   # сбрасываем для следующего раунда

        # запускаем следующий раунд с небольшой паузой
        self.env.process(self._start_next_round())

    def _start_next_round(self):
        yield self.env.timeout(1)
        self.start_round()