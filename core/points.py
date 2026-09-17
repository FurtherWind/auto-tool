import threading
import time
import random
from pynput.mouse import Button, Controller as MouseController

mouse = MouseController()


class PointsClicker:
    """Кликает по точкам. Поддерживает:
    - рандомизацию интервала
    - лимит прогонов
    - пауза/продолжить
    - плавное перемещение курсора
    """

    def __init__(self, on_finish=None):
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.thread = None
        self.counter = 0                       # сколько прогонов сделано
        self.on_finish = on_finish

        self.points = []
        self.interval_min = 500
        self.interval_max = 500
        self.mouse_button = "left"
        self.loops = 1                         # 0 = ∞
        self.smooth = True                     # плавное перемещение
        self.smooth_steps = 15                 # шагов за клик
        self.smooth_delay = 0.005              # пауза между шагами (сек)

    def update(self, points=None, interval_min=None, interval_max=None,
               mouse_button=None, loops=None, smooth=None):
        if points is not None:
            self.points = list(points)
        if interval_min is not None:
            self.interval_min = interval_min
        if interval_max is not None:
            self.interval_max = interval_max
        if mouse_button is not None:
            self.mouse_button = mouse_button
        if loops is not None:
            self.loops = loops
        if smooth is not None:
            self.smooth = smooth

    def _move_to(self, x, y):
        """Перемещение курсора — плавно или телепортом."""
        if not self.smooth:
            mouse.position = (x, y)
            return

        try:
            cur_x, cur_y = mouse.position
        except Exception:
            mouse.position = (x, y)
            return

        # уже там — не дёргаемся
        if abs(cur_x - x) < 2 and abs(cur_y - y) < 2:
            mouse.position = (x, y)
            return

        steps = self.smooth_steps
        for i in range(1, steps + 1):
            if self.stop_event.is_set():
                return
            t = i / steps
            nx = cur_x + (x - cur_x) * t
            ny = cur_y + (y - cur_y) * t
            mouse.position = (int(nx), int(ny))
            time.sleep(self.smooth_delay)

    def _sleep_interval(self):
        lo = self.interval_min
        hi = self.interval_max
        if hi < lo:
            hi = lo
        interval_ms = random.randint(lo, hi) if hi > lo else lo
        interval = interval_ms / 1000.0

        slept = 0.0
        while slept < interval and not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.05)
                continue
            time.sleep(0.01)
            slept += 0.01

    def _worker(self):
        btn = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }.get(self.mouse_button, Button.left)

        loops_done = 0
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.05)
                continue

            for (x, y) in self.points:
                if self.stop_event.is_set():
                    break

                # пауза перед кликом
                while self.pause_event.is_set() and not self.stop_event.is_set():
                    time.sleep(0.05)

                self._move_to(x, y)
                time.sleep(0.02)
                mouse.click(btn)
                self._sleep_interval()

            if self.stop_event.is_set():
                break

            loops_done += 1
            self.counter = loops_done
            if self.loops > 0 and loops_done >= self.loops:
                break

        self.running = False
        if not self.stop_event.is_set() and self.on_finish:
            try:
                self.on_finish()
            except Exception as e:
                print("on_finish error:", e)

    def start(self):
        if self.running or not self.points:
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