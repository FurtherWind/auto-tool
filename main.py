import threading
import time
import keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyController

mouse = MouseController()
kb = KeyController()

# --- состояние ---
running = False
worker_thread = None
stop_event = threading.Event()

# --- настройки (потом вынесем в GUI/пресеты) ---
CONFIG = {
    "mode": "keys",          # "click" или "keys"
    "mouse_button": "left",   # left / right / middle
    "click_type": "single",   # single / double
    "keys": ["space"],        # список клавиш для режима keys
    "interval_ms": 50,        # пауза между действиями
    "toggle_hotkey": "f8",    # старт/стоп
    "exit_hotkey": "f12",     # выход
}

BUTTON_MAP = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


def do_action():
    """Одно действие согласно конфигу."""
    if CONFIG["mode"] == "click":
        btn = BUTTON_MAP[CONFIG["mouse_button"]]
        mouse.click(btn)
        if CONFIG["click_type"] == "double":
            time.sleep(0.05)
            mouse.click(btn)
    elif CONFIG["mode"] == "keys":
        for k in CONFIG["keys"]:
            keyboard.press(k)
        for k in reversed(CONFIG["keys"]):
            keyboard.release(k)


def worker():
    """Цикл выполнения действий, пока не попросят стоп."""
    interval = CONFIG["interval_ms"] / 1000.0
    while not stop_event.is_set():
        do_action()
        # дробим сон, чтобы стоп срабатывал быстро
        slept = 0.0
        while slept < interval and not stop_event.is_set():
            time.sleep(0.01)
            slept += 0.01


def start():
    global running, worker_thread
    if running:
        return
    stop_event.clear()
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    running = True
    print(f"[+] Started ({CONFIG['mode']})")


def stop():
    global running
    if not running:
        return
    stop_event.set()
    running = False
    print("[-] Stopped")


def toggle():
    if running:
        stop()
    else:
        start()


def main():
    keyboard.add_hotkey(CONFIG["toggle_hotkey"], toggle)
    keyboard.add_hotkey(CONFIG["exit_hotkey"], lambda: (stop(), exit(0)))

    print("=== Auto Tool ===")
    print(f"Toggle: {CONFIG['toggle_hotkey'].upper()}")
    print(f"Exit:   {CONFIG['exit_hotkey'].upper()}")
    print(f"Mode:   {CONFIG['mode']}")

    keyboard.wait()  # блокируем главный поток


from ui.app import AutoToolApp

if __name__ == "__main__":
    app = AutoToolApp()
    app.mainloop()