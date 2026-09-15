from pynput import mouse


class PointRecorder:
    """Слушает клики мыши. Игнорирует клики в области GUI."""

    def __init__(self, on_point=None):
        self.points = []
        self.recording = False
        self.listener = None
        self.on_point = on_point
        self.ignore_rect = None

    def set_ignore_rect(self, x1, y1, x2, y2):
        self.ignore_rect = (x1, y1, x2, y2)

    def _in_ignore_rect(self, x, y):
        if self.ignore_rect is None:
            return False
        x1, y1, x2, y2 = self.ignore_rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def start(self):
        if self.recording:
            return
        self.recording = True

        def on_click(x, y, button, pressed):
            if not self.recording:
                return False
            if pressed and button == mouse.Button.left:
                ix, iy = int(x), int(y)
                if self._in_ignore_rect(ix, iy):
                    return
                pt = (ix, iy)
                self.points.append(pt)
                if self.on_point:
                    try:
                        self.on_point(pt)
                    except Exception as e:
                        print("on_point error:", e)

        self.listener = mouse.Listener(on_click=on_click)
        self.listener.start()

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    def clear(self):
        self.points = []

    def get_points(self):
        return list(self.points)