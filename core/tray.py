import threading
import pystray
from PIL import Image


class TrayIcon:
    """Иконка в системном трее с меню:
    Развернуть / Стоп всё / Выход."""

    def __init__(self, icon_path: str, on_show=None, on_stop=None, on_exit=None,
                 title: str = "Auto Tool"):
        """
        icon_path — путь к .ico или .png
        on_show   — показать главное окно
        on_stop   — стоп всё
        on_exit   — выход из программы
        """
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_stop = on_stop
        self.on_exit = on_exit
        self.title = title
        self.icon = None
        self.thread = None
        self._running = False

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

    def _run(self):
        try:
            img = Image.open(self.icon_path)
            self.icon = pystray.Icon(
                "auto_tool",
                icon=img,
                title=self.title,
                menu=self._build_menu(),
            )
            self._running = True
            self.icon.run()
        except Exception as e:
            print("tray run error:", e)
            self._running = False

    def start(self):
        """Запустить трей в отдельном потоке."""
        if self._running:
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Остановить трей."""
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        self._running = False

    def notify(self, message: str, title: str = "Auto Tool"):
        """Показать уведомление из трея (Windows 10+)."""
        if self.icon is None:
            return
        try:
            self.icon.notify(message, title)
        except Exception:
            pass