import tkinter as tk


class Overlay:
    """Оверлей поверх всех окон с маркерами точек."""

    COLOR_BG = "#101010"
    COLOR_POINT = "#00ff88"
    COLOR_POINT_BORDER = "#00aa55"
    COLOR_LINE = "#00ff88"
    COLOR_TEXT = "#ffffff"
    ALPHA = 0.35

    def __init__(self, parent: tk.Tk, on_close=None):
        self.parent = parent
        self.on_close = on_close
        self.win = None
        self.canvas = None
        self.visible = False
        self._alpha_job = None

    def _build(self):
        if self.win is not None:
            return
        self.win = tk.Toplevel(self.parent)
        self.win.title("Points Overlay")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", self.ALPHA)
        self.win.configure(bg=self.COLOR_BG)

        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        self.win.geometry(f"{screen_w}x{screen_h}+0+0")

        self.canvas = tk.Canvas(
            self.win, width=screen_w, height=screen_h,
            bg=self.COLOR_BG, highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.win.update_idletasks()
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            styles |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)
        except Exception as e:
            print("click-through failed:", e)

        self._keep_alpha()

    def _keep_alpha(self):
        if self.win is None:
            return
        if not self.visible:
            self._alpha_job = None
            return
        try:
            self.win.attributes("-alpha", self.ALPHA)
            self.win.attributes("-topmost", True)
        except Exception:
            pass
        self._alpha_job = self.win.after(200, self._keep_alpha)

    def show(self, points):
        self._build()
        self._redraw(points)
        if not self.visible:
            self.win.deiconify()
            self.win.lift()
            self.visible = True
        if self._alpha_job is None:
            self._keep_alpha()

    def update(self, points):
        if self.win is None:
            return
        self._redraw(points)

    def hide(self):
        if self.win is None:
            return
        if self._alpha_job:
            try:
                self.win.after_cancel(self._alpha_job)
            except Exception:
                pass
            self._alpha_job = None
        try:
            self.win.withdraw()
            self.win.attributes("-topmost", False)
        except Exception:
            pass
        self.visible = False

    def close(self):
        if self.win is None:
            return
        if self._alpha_job:
            try:
                self.win.after_cancel(self._alpha_job)
            except Exception:
                pass
            self._alpha_job = None
        try:
            self.win.destroy()
        except Exception:
            pass
        self.win = None
        self.canvas = None
        self.visible = False
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                pass

    def _redraw(self, points):
        if self.canvas is None:
            return
        self.canvas.delete("all")
        if not points:
            return

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill=self.COLOR_LINE, width=2, dash=(6, 4))
        if len(points) > 2:
            x1, y1 = points[-1]
            x2, y2 = points[0]
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill=self.COLOR_LINE, width=1, dash=(4, 4))

        radius = 16
        for i, (x, y) in enumerate(points, start=1):
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline=self.COLOR_POINT_BORDER, width=3, fill="")
            self.canvas.create_oval(
                x - radius + 3, y - radius + 3, x + radius - 3, y + radius - 3,
                outline=self.COLOR_POINT, width=2, fill="")
            self.canvas.create_text(
                x, y, text=str(i),
                fill=self.COLOR_TEXT, font=("Arial", 12, "bold"))