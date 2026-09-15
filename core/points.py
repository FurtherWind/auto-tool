import threading
import time
from pynput.mouse import Button, Controller as MouseController

mouse = MouseController()


class PointsClicker:
    """Кликает по точкам. Поддерживает прогоны и колбэк завершения."""

    def __init__(self, on_finish=None):
        self.running = False
        self.stop_event = threading.Event()
        self.thread = None
        self.points = []
        self.interval_ms = 500
        self.mouse_button = "left"
        self.loops = 1
        self.on_finish = on_finish   # колбэк когда прогоны закончились

    def update(self, points=None, interval_ms=None, mouse_button=None, loops=None):
        if points is not None:
            self.points = list(points)
        if interval_ms is not None:
            self.interval_ms = interval_ms
        if mouse_button is not None:
            self.mouse_button = mouse_button
        if loops is not None:
            self.loops = loops

    def _worker(self):
        interval = self.interval_ms / 1000.0
        btn = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }.get(self.mouse_button, Button.left)

        loops_done = 0
        while not self.stop_event.is_set():
            for (x, y) in self.points:
                if self.stop_event.is_set():
                    break
                mouse.position = (x, y)
                time.sleep(0.02)
                mouse.click(btn)

                slept = 0.0
                while slept < interval and not self.stop_event.is_set():
                    time.sleep(0.01)
                    slept += 0.01

            if self.stop_event.is_set():
                break

            loops_done += 1
            if self.loops > 0 and loops_done >= self.loops:
                break

        self.running = False
        # сообщаем наверх что закончили (для скрытия оверлея)
        if self.on_finish and not self.stop_event.is_set():
            try:
                self.on_finish()
            except Exception as e:
                print("on_finish error:", e)

    def start(self):
        if self.running or not self.points:
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