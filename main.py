import os
import sys
from ui.app import AutoToolApp
from core import presets
from core import settings
from core.tray import TrayIcon


def resource_path(relative: str) -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


if __name__ == "__main__":
    presets.ensure_dir()
    settings.load()
    app = AutoToolApp()

    # иконка окна
    try:
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            app.iconbitmap(icon_path)
    except Exception as e:
        print("icon error:", e)

    # трей с двумя иконками (серая / зелёная)
    gray = resource_path("icons/tray_gray.png")
    green = resource_path("icons/tray_green.png")
    if not os.path.exists(gray):
        gray = resource_path("icon.png")
    if not os.path.exists(green):
        green = resource_path("icon.png")

    tray = TrayIcon(
        icon_idle_path=gray,
        icon_active_path=green,
        on_show=app._show_from_tray,
        on_stop=app._stop_from_tray,
        on_exit=app._exit_from_tray,
        title="Auto Tool",
    )
    app.tray = tray
    tray.start()

    # запуск свёрнутым
    if settings.get("start_minimized", False):
        app.withdraw()

    # проверка обновлений при старте
    if settings.get("check_updates", True):
        # запрос в фоне, чтобы не блокировать старт
        import threading
        def _check():
            try:
                import urllib.request, json
                url = "https://api.github.com/repos/FurtherWind/auto-tool/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": "AutoTool"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode())
                tag = data.get("tag_name", "").lstrip("v")
                if tag and tag != "1.4.0":
                    print(f"[update] доступна новая версия: v{tag}")
            except Exception:
                pass
        threading.Thread(target=_check, daemon=True).start()

    app.mainloop()