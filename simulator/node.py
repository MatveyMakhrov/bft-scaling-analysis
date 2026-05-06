import simpy

class Node:
    """
    Базовый узел BFT-протокола.
    """

    def __init__(self, env, node_id, network, metrics):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.metrics = metrics

        self.inbox = simpy.Store(env)

    # ===========================
    # Messaging
    # ===========================

    def send(self, dst, msg):
        """
        Отправка сообщения другому узлу
        """
        self.metrics.record_send(self.node_id)
        self.env.process(self.network.send(self.node_id, dst, msg))

    # ===========================
    # Process
    # ===========================

    def run(self):
        while True:
            src, msg = yield self.inbox.get()
            self.metrics.record_receive()
            self.handle(src, msg)

    def handle(self, src, msg):
        """
        Обрабатывается в дочерних классах (PBFT, HotStuff, ...)
        """
        raise NotImplementedError
