class Metrics:
    def __init__(self):
        # Количество отправленных сообщений
        self.messages_sent = 0

        # Количество полученных сообщений
        self.messages_received = 0

        # Сколько раундов завершил каждый узел
        self.rounds_finished = {}

        # Дополнительно: время на каждый раунд (для анализа производительности)
        self.round_times = {}

    # ===========================
    # Методы для Node
    # ===========================
    def record_send(self, node_id):
        self.messages_sent += 1

    def record_receive(self):
        self.messages_received += 1

    def record_round_finished(self, node_id, round_time=None):
        self.rounds_finished[node_id] = self.rounds_finished.get(node_id, 0) + 1
        if round_time is not None:
            if node_id not in self.round_times:
                self.round_times[node_id] = []
            self.round_times[node_id].append(round_time)

    # ===========================
    # Вывод результатов
    # ===========================
    def summary(self):
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "rounds_finished": self.rounds_finished,
            "round_times": self.round_times
        }
