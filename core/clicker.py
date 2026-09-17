import threading
import time
import random
import keyboard
from pynput.mouse import Button, Controller as MouseController

mouse = MouseController()

BUTTON_MAP = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


class Clicker:
    """Движок автоклика/автонажатия. Поддерживает:
    - рандомизацию интервала (min-max)
    - счётчик выполнений с лимитом
    - пауза/продолжить
    """

    def __init__(self, on_finish=None):
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()   # установлен = на паузе
        self.thread = None
        self.counter = 0                       # сколько раз выполнено
        self.on_finish = on_finish             # колбэк при завершении (лимит)

        self.config = {
            "mode": "click",         # click | keys
            "mouse_button": "left",
            "click_type": "single",
            "keys": ["space"],
            "interval_min": 500,     # мс
            "interval_max": 500,     # мс (== min → без рандома)
            "max_count": 0,          # 0 = бесконечно
        }

    def update_config(self, new_config: dict):
        self.config.update(new_config)

    # ---------- действия ----------
    def _do_action(self):
        if self.config["mode"] == "click":
            btn = BUTTON_MAP[self.config["mouse_button"]]
            mouse.click(btn)
            if self.config["click_type"] == "double":
                time.sleep(0.05)
                mouse.click(btn)
        else:
            for k in self.config["keys"]:
                keyboard.press(k)
            for k in reversed(self.config["keys"]):
                keyboard.release(k)

    def _sleep_interval(self):
        """Спит случайный интервал между min и max."""
        lo = self.config["interval_min"]
        hi = self.config["interval_max"]
        if hi < lo:
            hi = lo
        interval_ms = random.randint(lo, hi) if hi > lo else lo
        interval = interval_ms / 1000.0

        slept = 0.0
        while slept < interval and not self.stop_event.is_set():
            if self.pause_event.is_set():
                # на паузе — ждём снятия
                time.sleep(0.05)
                continue
            time.sleep(0.01)
            slept += 0.01

    def _worker(self):
        while not self.stop_event.is_set():
            # пауза перед действием
            if self.pause_event.is_set():
                time.sleep(0.05)
                continue

            self._do_action()
            self.counter += 1

            # проверка лимита
            max_c = self.config.get("max_count", 0)
            if max_c > 0 and self.counter >= max_c:
                break

            self._sleep_interval()

        self.running = False
        # колбэк только если не стопнули руками
        if not self.stop_event.is_set() and self.on_finish:
            try:
                self.on_finish()
            except Exception as e:
                print("on_finish error:", e)

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.pause_event.clear()
        self.paused = False
        self.counter = 0
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.stop_event.set()
        self.pause_event.clear()
        self.paused = False
        self.running = False

    def pause(self):
        if not self.running:
            return
        self.pause_event.set()
        self.paused = True

    def resume(self):
        if not self.running:
            return
        self.pause_event.clear()
        self.paused = False

    def toggle_pause(self):
        if not self.running:
            return
        if self.paused:
            self.resume()
        else:
            self.pause()