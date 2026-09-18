import keyboard


_capture_hook = None


def capture(on_done, on_cancel=None):
    """Слушает следующее комбинацию клавиш и вызывает on_done(combo).
    Esc — отмена."""
    global _capture_hook

    if _capture_hook is not None:
        try:
            keyboard.unhook(_capture_hook)
        except Exception:
            pass

    pressed = []
    released = set()

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
        global _capture_hook
        name = _normalize(e.name) if e.name else ""
        if not name:
            return
        if e.event_type == "down":
            if name == "esc":
                try:
                    keyboard.unhook(_capture_hook)
                except Exception:
                    pass
                _capture_hook = None
                if on_cancel:
                    on_cancel()
                return
            if name not in pressed:
                pressed.append(name)
            released.discard(name)
        elif e.event_type == "up":
            released.add(name)
            if pressed and all(k in released for k in pressed):
                combo = "+".join(pressed)
                try:
                    keyboard.unhook(_capture_hook)
                except Exception:
                    pass
                _capture_hook = None
                on_done(combo)

    _capture_hook = keyboard.hook(on_event)