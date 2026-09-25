import keyboard
from pynput import mouse as _mouse


_capture_hook = None
_mouse_listener = None
_on_cancel_cb = None


def capture(on_done, on_cancel=None, entry_widget=None):
    """Слушает следующее комбо клавиш и вызывает on_done(combo).
    Esc — отмена. Клик ВНЕ окна (не entry) — отмена."""
    global _capture_hook, _mouse_listener, _on_cancel_cb

    _cleanup()

    pressed = []
    released = set()
    _on_cancel_cb = on_cancel

    def _normalize(name: str) -> str:
        if not name:
            return ""
        for prefix in ("left ", "right "):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        mapping = {
            "ctrl_l": "ctrl", "ctrl_r": "ctrl",
            "alt_l": "alt", "alt_r": "alt",
            "shift_l": "shift", "shift_r": "shift",
            "alt_gr": "alt",
        }
        return mapping.get(name, name)

    def on_event(e):
        name = _normalize(e.name) if e.name else ""
        if not name:
            return
        if e.event_type == "down":
            if name == "esc":
                cb = _on_cancel_cb
                _cleanup()
                if cb:
                    cb()
                return
            if name not in pressed:
                pressed.append(name)
            released.discard(name)
        elif e.event_type == "up":
            released.add(name)
            if pressed and all(k in released for k in pressed):
                combo = "+".join(pressed)
                _cleanup()
                on_done(combo)

    _capture_hook = keyboard.hook(on_event)

    if entry_widget is not None:
        # получаем корневое окно (Tk / Toplevel), к которому привязан entry
        try:
            root_win = entry_widget.winfo_toplevel()
        except Exception:
            root_win = entry_widget

        def on_click(x, y, button, pressed_state):
            if not pressed_state:
                return
            try:
                # проверяем ВСЁ окно, а не отдельный entry
                rx1 = root_win.winfo_rootx()
                ry1 = root_win.winfo_rooty()
                rx2 = rx1 + root_win.winfo_width()
                ry2 = ry1 + root_win.winfo_height()

                # клик вне окна — отменяем
                if not (rx1 <= x <= rx2 and ry1 <= y <= ry2):
                    cb = _on_cancel_cb
                    _cleanup()
                    if cb:
                        cb()
            except Exception:
                pass

        _mouse_listener = _mouse.Listener(on_click=on_click)
        _mouse_listener.start()


def cancel():
    """Принудительная отмена с вызовом on_cancel."""
    global _on_cancel_cb
    cb = _on_cancel_cb
    _cleanup()
    if cb:
        try:
            cb()
        except Exception:
            pass


def _cleanup():
    global _capture_hook, _mouse_listener, _on_cancel_cb
    if _capture_hook is not None:
        try:
            keyboard.unhook(_capture_hook)
        except Exception:
            pass
        _capture_hook = None
    if _mouse_listener is not None:
        try:
            _mouse_listener.stop()
        except Exception:
            pass
        _mouse_listener = None
    _on_cancel_cb = None