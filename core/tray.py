import threading
import pystray
from PIL import Image


class TrayIcon:
    """Иконка в трее с меню. Поддерживает смену картинки (серая/зелёная)."""

    def __init__(self, icon_idle_path: str, icon_active_path: str = None,
                 on_show=None, on_stop=None, on_exit=None,
                 title: str = "Auto Tool"):
        self.icon_idle_path = icon_idle_path
        self.icon_active_path = icon_active_path or icon_idle_path
        self.on_show = on_show
        self.on_stop = on_stop
        self.on_exit = on_exit
        self.title = title
        self.icon = None
        self.thread = None
        self._running = False
        self._active = False   # сейчас активно?
        self._img_idle = None
        self._img_active = None

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Развернуть", self._handle_show, default=True),
            pystray.MenuItem("Стоп всё", self._handle_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._handle_exit),
        )

    def _handle_show(self, icon, item):
        if self.on_show:
            try:
                self.on_show()
            except Exception as e:
                print("tray show error:", e)

    def _handle_stop(self, icon, item):
        if self.on_stop:
            try:
                self.on_stop()
            except Exception as e:
                print("tray stop error:", e)

    def _handle_exit(self, icon, item):
        try:
            self.icon.stop()
        except Exception:
            pass
        self._running = False
        if self.on_exit:
            try:
                self.on_exit()
            except Exception as e:
                print("tray exit error:", e)

    def _load_images(self):
        try:
            self._img_idle = Image.open(self.icon_idle_path)
        except Exception as e:
            print("tray idle img error:", e)
            self._img_idle = Image.new("RGBA", (64, 64), (128, 128, 128, 255))
        try:
            self._img_active = Image.open(self.icon_active_path)
        except Exception as e:
            print("tray active img error:", e)
            self._img_active = self._img_idle

    def _run(self):
        try:
            self._load_images()
            self.icon = pystray.Icon(
                "auto_tool",
                icon=self._img_idle,
                title=self.title,
                menu=self._build_menu(),
            )
            self._running = True
            self.icon.run()
        except Exception as e:
            print("tray run error:", e)
            self._running = False

    def start(self):
        if self._running:
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        self._running = False

    def set_active(self, active: bool):
        """Сменить иконку: активна (зелёная) / неактивна (серая)."""
        if self.icon is None:
            return
        if active == self._active:
            return
        self._active = active
        try:
            self.icon.icon = self._img_active if active else self._img_idle
        except Exception as e:
            print("tray set_active error:", e)