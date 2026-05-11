from simulator.node import Node

class HotStuffNode(Node):
    """
    Модель HotStuff для симуляции масштабируемости.
    Ключевое отличие от PBFT: O(n) сообщений за раунд вместо O(n²).

    Схема раунда:
      1. Лидер рассылает PROPOSE всем                — O(n)
      2. Каждый узел отправляет VOTE только лидеру   — O(n) суммарно
      3. Лидер собирает 2f+1 VOTE → рассылает DECIDE — O(n)
      4. Каждый узел получает DECIDE → отправляет
         NEW-VIEW новому лидеру                      — O(n) суммарно
      5. Новый лидер собирает 2f+1 NEW-VIEW →
         рассылает PROPOSE (следующий раунд)          — O(n)

    NEW-VIEW обеспечивает синхронизацию: все узлы переходят
    к новому раунду одновременно, после явного подтверждения лидера.
    """

    def __init__(self, env, node_id, network, metrics, n, f):
        super().__init__(env, node_id, network, metrics)
        self.n = n
        self.f = f
        self.votes = set()      # VOTE, собранные лидером текущего раунда
        self.new_views = set()  # NEW-VIEW, собранные лидером следующего раунда
        self.round_number = 0
        self.round_started = False
        self.round_start_time = None
        self.voted = False      # узел уже проголосовал в этом раунде

    # ===========================
    # Запуск первого раунда
    # (последующие запускаются через NEW-VIEW)
    # ===========================
    def start_round(self):
        if self.round_started:
            return
        self.round_started = True
        self.round_number += 1
        self.round_start_time = self.env.now
        self.voted = False
        self.votes.clear()
        self.new_views.clear()

        leader = self.round_number % self.n
        if self.node_id == leader:
            # Лидер рассылает PROPOSE всем — O(n)
            for i in range(self.n):
                self.send(i, ("PROPOSE", self.round_number))

    # ===========================
    # Обработка сообщений
    # ===========================
    def handle(self, src, msg):
        msg_type = msg[0]
        msg_round = msg[1]

        # Игнорируем сообщения из устаревших раундов
        if msg_round < self.round_number:
            return

        leader_current = self.round_number % self.n
        leader_next = (self.round_number + 1) % self.n

        if msg_type == "PROPOSE":
            # Синхронизируемся с раундом из сообщения
            if msg_round > self.round_number:
                self.round_number = msg_round
                self.round_started = True
                self.round_start_time = self.env.now
                self.voted = False
                self.votes.clear()

            # Отправляем VOTE только текущему лидеру — O(1) на узел
            if not self.voted:
                self.voted = True
                self.send(leader_current, ("VOTE", self.round_number))

        elif msg_type == "VOTE":
            # Только текущий лидер собирает голоса
            if self.node_id == leader_current and msg_round == self.round_number:
                self.votes.add(src)
                if len(self.votes) >= 2 * self.f + 1:
                    # Собрано достаточно — рассылаем DECIDE всем — O(n)
                    for i in range(self.n):
                        self.send(i, ("DECIDE", self.round_number))

        elif msg_type == "DECIDE":
            if msg_round == self.round_number:
                # Фиксируем метрики
                round_time = None
                if self.round_start_time is not None:
                    round_time = self.env.now - self.round_start_time
                self.metrics.record_round_finished(self.node_id, round_time)

                # Отправляем NEW-VIEW следующему лидеру — O(1) на узел
                self.send(leader_next, ("NEW-VIEW", self.round_number + 1))

        elif msg_type == "NEW-VIEW":
            # Только следующий лидер собирает NEW-VIEW
            if self.node_id == leader_next and msg_round == self.round_number + 1:
                self.new_views.add(src)
                if len(self.new_views) >= 2 * self.f + 1:
                    # Достаточно подтверждений — запускаем следующий раунд
                    self._advance_round()

    # ===========================
    # Переход к следующему раунду
    # ===========================
    def _advance_round(self):
        self.round_number += 1
        self.round_started = True
        self.round_start_time = self.env.now
        self.voted = False
        self.votes.clear()
        self.new_views.clear()

        # Новый лидер рассылает PROPOSE — O(n)
        for i in range(self.n):
            self.send(i, ("PROPOSE", self.round_number))