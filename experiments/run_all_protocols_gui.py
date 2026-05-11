import sys
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk

# Определяем корень проекта надёжно:
# этот файл лежит в experiments/, корень — на уровень выше
_this_file   = os.path.realpath(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(_this_file))

# insert(0, ...) — гарантирует что наш путь идёт первым
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import simpy
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from simulator.network import Network
from simulator.metrics import Metrics
from protocols.pbft import PBFTNode
from protocols.hotstuff import HotStuffNode
from protocols.honeybadger import HBBFTNode
from protocols.ibft import IBFTNode
from protocols.tendermint import TendermintNode
from protocols.rbft import RBFTNode

# -----------------------------
# Настройки эксперимента
# -----------------------------
NUM_NODES_LIST = [4, 8, 16, 32, 64, 128, 256]
BATCH_SIZE     = 2
ROUND_DELAY    = 10
SIMULATION_TIME = 1000

PROTOCOLS = {
    "PBFT":          PBFTNode,
    "HotStuff":      HotStuffNode,
    "HoneyBadgerBFT": HBBFTNode,
    "IBFT":          IBFTNode,
    "Tendermint":    TendermintNode,
    "RBFT":          RBFTNode,
}

TOTAL_RUNS = len(NUM_NODES_LIST) * len(PROTOCOLS)   # 7 × 6 = 42

# -----------------------------
# Логика симуляции
# -----------------------------
def run_simulation(protocol_cls, num_nodes):
    if num_nodes < 4:
        raise ValueError(f"num_nodes={num_nodes} < 4, BFT невозможен.")
    env = simpy.Environment()
    f   = num_nodes // 3
    metrics = Metrics()
    network = Network(env, metrics, delay_mean=ROUND_DELAY)
    nodes = []
    for i in range(num_nodes):
        if protocol_cls is HBBFTNode:
            node = protocol_cls(env, i, network, metrics, num_nodes, f, BATCH_SIZE)
        else:
            node = protocol_cls(env, i, network, metrics, num_nodes, f)
        network.register(node)
        nodes.append(node)
        env.process(node.run())
    for node in nodes:
        node.start_round()
    env.run(until=SIMULATION_TIME)
    summary = metrics.summary()
    round_times = summary.get("round_times", {})
    all_times   = [t for times in round_times.values() for t in times]
    avg_round_time = sum(all_times) / len(all_times) if all_times else 0
    return {
        "messages_sent":     summary["messages_sent"],
        "messages_received": summary["messages_received"],
        "rounds_finished":   summary["rounds_finished"],
        "avg_round_time":    avg_round_time,
        "simulation_time":   SIMULATION_TIME,
    }

def compute_throughput(r):
    total = sum(r["rounds_finished"].values())
    return total / r["simulation_time"] if r["simulation_time"] else 0

# -----------------------------
# Фоновый поток симуляции
# -----------------------------
def simulation_thread(log_q, progress_q, done_q):
    results = []
    completed = 0
    for num_nodes in NUM_NODES_LIST:
        for proto_name, proto_cls in PROTOCOLS.items():
            msg = f"Running {proto_name} with {num_nodes} nodes..."
            log_q.put(msg)
            try:
                r = run_simulation(proto_cls, num_nodes)
                throughput = compute_throughput(r)
                results.append({
                    "protocol":  proto_name,
                    "num_nodes": num_nodes,
                    "throughput": throughput,
                    **r,
                })
                log_q.put(f"  ✓ throughput={throughput:.4f}  "
                          f"msgs={r['messages_sent']}  "
                          f"avg_time={r['avg_round_time']:.2f}")
            except Exception as e:
                log_q.put(f"  ✗ Ошибка: {e}")
            completed += 1
            progress_q.put(completed)

    # сохраняем CSV
    df = pd.DataFrame(results)
    csv_path = os.path.join(project_root, "bft_results.csv")
    df.to_csv(csv_path, index=False)
    log_q.put(f"\nРезультаты сохранены → {csv_path}")
    done_q.put(df)

# -----------------------------
# GUI
# -----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BFT Scaling Simulator")
        self.configure(bg="#0f1117")
        self.resizable(True, True)
        self.minsize(720, 520)

        self._build_ui()
        self._log_q      = queue.Queue()
        self._progress_q = queue.Queue()
        self._done_q     = queue.Queue()
        self._running    = False
        self.after(100, self._poll_queues)

    # ---------- UI ----------
    def _build_ui(self):
        # ── заголовок ──
        header = tk.Frame(self, bg="#0f1117")
        header.pack(fill="x", padx=32, pady=(28, 0))

        tk.Label(
            header,
            text="BFT Scaling Analysis",
            font=("Courier New", 13, "bold"),
            fg="#4ade80", bg="#0f1117",
        ).pack()

        # ── кнопка ──
        btn_frame = tk.Frame(self, bg="#0f1117")
        btn_frame.pack(pady=(18, 0))

        self._btn = tk.Button(
            btn_frame,
            text="▶  Начать симуляцию",
            font=("Courier New", 12, "bold"),
            fg="#0f1117", bg="#4ade80",
            activebackground="#22c55e", activeforeground="#0f1117",
            relief="flat", padx=28, pady=10,
            cursor="hand2",
            command=self._start,
        )
        self._btn.pack()

        # ── прогресс-бар ──
        prog_frame = tk.Frame(self, bg="#0f1117")
        prog_frame.pack(fill="x", padx=32, pady=(20, 0))

        self._pct_label = tk.Label(
            prog_frame,
            text="0 %",
            font=("Courier New", 10),
            fg="#94a3b8", bg="#0f1117",
            anchor="e",
        )
        self._pct_label.pack(side="right")

        self._status_label = tk.Label(
            prog_frame,
            text="Готов к запуску",
            font=("Courier New", 10),
            fg="#94a3b8", bg="#0f1117",
            anchor="w",
        )
        self._status_label.pack(side="left")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "green.Horizontal.TProgressbar",
            troughcolor="#1e293b",
            background="#4ade80",
            bordercolor="#0f1117",
            lightcolor="#4ade80",
            darkcolor="#4ade80",
        )
        self._progress = ttk.Progressbar(
            self,
            orient="horizontal",
            length=400,
            mode="determinate",
            maximum=TOTAL_RUNS,
            style="green.Horizontal.TProgressbar",
        )
        self._progress.pack(fill="x", padx=32, pady=(6, 0))

        # ── окно вывода ──
        term_frame = tk.Frame(self, bg="#1e293b", relief="flat")
        term_frame.pack(fill="both", expand=True, padx=32, pady=(18, 28))

        scrollbar = tk.Scrollbar(term_frame, bg="#334155", troughcolor="#1e293b")
        scrollbar.pack(side="right", fill="y")

        self._terminal = tk.Text(
            term_frame,
            bg="#1e293b", fg="#e2e8f0",
            font=("Courier New", 10),
            relief="flat",
            insertbackground="#4ade80",
            selectbackground="#334155",
            wrap="word",
            state="disabled",
            yscrollcommand=scrollbar.set,
            padx=12, pady=10,
        )
        self._terminal.pack(fill="both", expand=True)
        scrollbar.config(command=self._terminal.yview)

        # теги цвета
        self._terminal.tag_config("ok",    foreground="#4ade80")
        self._terminal.tag_config("err",   foreground="#f87171")
        self._terminal.tag_config("info",  foreground="#94a3b8")
        self._terminal.tag_config("run",   foreground="#fbbf24")
        self._terminal.tag_config("done",  foreground="#38bdf8")

    # ---------- запуск ----------
    def _start(self):
        if self._running:
            return
        self._running = True
        self._btn.config(state="disabled", text="⏳  Симуляция запущена...")
        self._progress["value"] = 0
        self._pct_label.config(text="0 %")
        self._status_label.config(text="Выполняется...")
        self._log("\n▶  Запуск симуляции\n", "done")
        self._log(f"   Протоколы : {', '.join(PROTOCOLS.keys())}\n", "info")
        self._log(f"   Узлы      : {NUM_NODES_LIST}\n", "info")
        self._log(f"   Всего запусков: {TOTAL_RUNS}\n\n", "info")

        t = threading.Thread(
            target=simulation_thread,
            args=(self._log_q, self._progress_q, self._done_q),
            daemon=True,
        )
        t.start()

    # ---------- polling ----------
    def _poll_queues(self):
        # логи
        while not self._log_q.empty():
            line = self._log_q.get_nowait()
            if line.startswith("  ✓"):
                self._log(line + "\n", "ok")
            elif line.startswith("  ✗"):
                self._log(line + "\n", "err")
            elif line.startswith("Running"):
                self._log(line + "\n", "run")
            else:
                self._log(line + "\n", "info")

        # прогресс
        while not self._progress_q.empty():
            completed = self._progress_q.get_nowait()
            self._progress["value"] = completed
            pct = int(completed / TOTAL_RUNS * 100)
            self._pct_label.config(text=f"{pct} %")

        # завершение
        while not self._done_q.empty():
            df = self._done_q.get_nowait()
            self._on_done(df)

        self.after(80, self._poll_queues)

    # ---------- завершение ----------
    def _on_done(self, df):
        self._running = False
        self._btn.config(state="normal", text="▶  Начать симуляцию")
        self._pct_label.config(text="100 %")
        self._progress["value"] = TOTAL_RUNS
        self._status_label.config(text="Готово ✓")
        self._log("\nСимуляция завершена. Строю графики...\n", "done")
        self.after(300, lambda: self._show_plots(df))

    def _show_plots(self, df):
        sns.set(style="whitegrid")
        plt.figure(figsize=(18, 5))

        plt.subplot(1, 3, 1)
        sns.lineplot(data=df, x="num_nodes", y="avg_round_time",
                     hue="protocol", marker="o")
        plt.title("Среднее время раунда для разных протоколов")
        plt.xlabel("Количество узлов (шт.)")
        plt.ylabel("Среднее время раунда (симуляционных единиц)")

        plt.subplot(1, 3, 2)
        sns.lineplot(data=df, x="num_nodes", y="messages_sent",
                     hue="protocol", marker="o")
        plt.yscale("log")
        plt.title("Количество отправленных сообщений (log scale)")
        plt.xlabel("Количество узлов (шт.)")
        plt.ylabel("Число отправленных сообщений (шт., лог. шкала)")

        plt.subplot(1, 3, 3)
        sns.lineplot(data=df, x="num_nodes", y="throughput",
                     hue="protocol", marker="o")
        plt.title("Пропускная способность протоколов")
        plt.xlabel("Количество узлов (шт.)")
        plt.ylabel("Пропускная способность (раундов / сим. единицу времени)")

        plt.tight_layout()
        plt.show()

    # ---------- helper ----------
    def _log(self, text, tag="info"):
        self._terminal.config(state="normal")
        self._terminal.insert("end", text, tag)
        self._terminal.see("end")
        self._terminal.config(state="disabled")


# -----------------------------
# Точка входа
# -----------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()