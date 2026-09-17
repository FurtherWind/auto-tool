import os
import sys
from ui.app import AutoToolApp
from core import presets
from core.tray import TrayIcon


def resource_path(relative: str) -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


if __name__ == "__main__":
    presets.ensure_dir()
    app = AutoToolApp()

    # иконка окна
    try:
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            app.iconbitmap(icon_path)
    except Exception as e:
        print("icon error:", e)

    # трей
    icon_tray_path = resource_path("icon.png")
    if not os.path.exists(icon_tray_path):
        icon_tray_path = resource_path("icon.ico")

    tray = TrayIcon(
        icon_path=icon_tray_path,
        on_show=app._show_from_tray,
        on_stop=app._stop_from_tray,
        on_exit=app._exit_from_tray,
        title="Auto Tool",
    )
    app.tray = tray
    tray.start()

    app.mainloop()