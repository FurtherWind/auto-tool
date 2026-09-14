import threading
import time
import keyboard
from pynput.mouse import Button, Controller as MouseController

mouse = MouseController()

BUTTON_MAP = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


class Clicker:
    """Движок автоклика/автонажатия. Потокобезопасный старт/стоп."""

    def __init__(self):
        self.running = False
        self.stop_event = threading.Event()
        self.thread = None
        self.config = {
            "mode": "click",         # click | keys
            "mouse_button": "left",  # left | right | middle
            "click_type": "single",  # single | double
            "keys": ["space"],
            "interval_ms": 50,
        }

    def update_config(self, new_config: dict):
        self.config.update(new_config)

    def _do_action(self):
        if self.config["mode"] == "click":
            btn = BUTTON_MAP[self.config["mouse_button"]]
            mouse.click(btn)
            if self.config["click_type"] == "double":
                time.sleep(0.05)
                mouse.click(btn)
        else:  # keys
            for k in self.config["keys"]:
                keyboard.press(k)
            for k in reversed(self.config["keys"]):
                keyboard.release(k)

    def _worker(self):
        interval = self.config["interval_ms"] / 1000.0
        while not self.stop_event.is_set():
            self._do_action()
            slept = 0.0
            while slept < interval and not self.stop_event.is_set():
                time.sleep(0.01)
                slept += 0.01

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.stop_event.set()
        self.running = False

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()