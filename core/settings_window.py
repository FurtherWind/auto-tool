import os
import subprocess
import sys
import threading
import customtkinter as ctk

from core import settings
from core import presets


CURRENT_VERSION = "1.4.1"
GITHUB_REPO = "FurtherWind/auto-tool"


class SettingsWindow(ctk.CTkToplevel):
    """Окно настроек. Открывается по кнопке ⚙️."""

    def __init__(self, parent, on_hotkeys_change=None, icon_path: str = None):
        super().__init__(parent)
        self.parent = parent
        self.on_hotkeys_change = on_hotkeys_change

        self.title("Настройки — Auto Tool")
        self.geometry("600x700")
        self.resizable(False, False)

        # поднять поверх главного окна
        self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, self._drop_topmost)
        self.focus_force()

        if icon_path and os.path.exists(icon_path):
            try:
                self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception as e:
                print("settings icon error:", e)

        self._center()
        self._hotkey_widgets = {}

        self._build()
        self._load_from_settings()

        self.bind("<FocusOut>", self._on_focus_out)

    def _drop_topmost(self):
        try:
            self.attributes("-topmost", False)
            self.lift()
            self.focus_force()
        except Exception as e:
            print("drop topmost error:", e)
            
    def _center(self):
        self.update_idletasks()
        w, h = 600, 700
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- сборка UI ----------
    def _build(self):
        scroll = ctk.CTkScrollableFrame(self, width=560, height=620)
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # ===== Поведение =====
        self._section(scroll, "🖥 Поведение")

        self.start_min_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(scroll, text="Запускать свёрнутым в трей",
                        variable=self.start_min_var).pack(anchor="w", pady=3)

        self.check_upd_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Проверять обновления при запуске",
                        variable=self.check_upd_var).pack(anchor="w", pady=3)

        # ===== Глобальные хоткеи =====
        self._section(scroll, "🔥 Глобальные хоткеи")

        hotkey_labels = [
            ("click",    "Клик"),
            ("keys",     "Клавиши"),
            ("points",   "Точки"),
            ("pause",    "Пауза"),
            ("stop_all", "СТОП ВСЁ"),
            ("exit",     "Выход"),
        ]
        for key, label in hotkey_labels:
            self._hotkey_row(scroll, key, label)

        # ===== Пресеты =====
        self._section(scroll, "💾 Пресеты")

        row2 = ctk.CTkFrame(scroll)
        row2.pack(fill="x", pady=5)
        ctk.CTkButton(row2, text="📂 Открыть папку",
                      command=self._open_presets_folder, width=160).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📤 Экспорт",
                      command=self._export_presets, width=140).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="📥 Импорт",
                      command=self._import_presets, width=140).pack(side="left", padx=3)

        # ===== Обновления =====
        self._section(scroll, "🔄 Обновления")

        self.update_info = ctk.CTkLabel(scroll, text=f"Текущая версия: v{CURRENT_VERSION}")
        self.update_info.pack(anchor="w", pady=3)

        ctk.CTkButton(scroll, text="Проверить обновления",
                      command=self._check_updates, width=200).pack(anchor="w", pady=5)

        # ===== Кнопки внизу =====
        self._section(scroll, "")

        row3 = ctk.CTkFrame(scroll)
        row3.pack(fill="x", pady=10)
        ctk.CTkButton(row3, text="🗑 Сбросить настройки",
                      command=self._reset_settings,
                      fg_color="#c0392b", hover_color="#e74c3c",
                      width=180).pack(side="left", padx=3)
        ctk.CTkButton(row3, text="💾 Сохранить",
                      command=self._save_all,
                      fg_color="#27ae60", hover_color="#2ecc71",
                      width=140).pack(side="right", padx=3)

    def _section(self, parent, title: str):
        if title:
            lbl = ctk.CTkLabel(parent, text=title, font=("Arial", 14, "bold"))
            lbl.pack(anchor="w", pady=(15, 5))
        else:
            ctk.CTkFrame(parent, height=2, fg_color="#444").pack(fill="x", pady=10)

    def _hotkey_row(self, parent, key: str, label: str):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=3)

        ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left", padx=5)

        entry = ctk.CTkEntry(row, width=200)
        entry.pack(side="left", padx=5)
        entry.bind("<Key>", lambda e: "break")
        self._hotkey_widgets[key] = entry

        btn = ctk.CTkButton(row, text="✎", width=40,
                            command=lambda: self._start_hotkey_capture(key, entry, btn))
        btn.pack(side="right", padx=5)

    # ---------- хоткей-капчер ----------
    def _start_hotkey_capture(self, key: str, entry: ctk.CTkEntry, btn: ctk.CTkButton):
        from core import hotkey_capture
        btn.configure(text="●", fg_color="#c0392b", hover_color="#e74c3c")

        def on_done(combo):
            if combo:
                entry.delete(0, "end")
                entry.insert(0, combo)
            btn.configure(text="✎", fg_color=("#3B8ED0", "#1F6AA5"))

        def on_cancel():
            btn.configure(text="✎", fg_color=("#3B8ED0", "#1F6AA5"))

        hotkey_capture.capture(on_done, on_cancel=on_cancel, entry_widget=entry)

    # ---------- загрузка / сохранение ----------
    def _load_from_settings(self):
        s = settings.load()
        self.start_min_var.set(s.get("start_minimized", False))
        self.check_upd_var.set(s.get("check_updates", True))
        hk = s.get("hotkeys", {})
        for key, entry in self._hotkey_widgets.items():
            entry.delete(0, "end")
            entry.insert(0, hk.get(key, ""))

    def _save_all(self):
        s = settings.load()
        s["start_minimized"] = self.start_min_var.get()
        s["check_updates"] = self.check_upd_var.get()
        s["hotkeys"] = {k: e.get().strip().lower() for k, e in self._hotkey_widgets.items()}
        settings.save(s)

        if self.on_hotkeys_change:
            try:
                self.on_hotkeys_change()
            except Exception as e:
                print("hotkeys change error:", e)

        self.destroy()

    def _reset_settings(self):
        settings.reset()
        self._load_from_settings()
        if self.on_hotkeys_change:
            self.on_hotkeys_change()

    # ---------- пресеты ----------
    def _open_presets_folder(self):
        folder = presets.PRESETS_DIR
        presets.ensure_dir()
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            print("open folder error:", e)

    def _export_presets(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="auto-tool-presets.json",
        )
        if not path:
            return
        import json
        data = {}
        for name in presets.list_presets():
            try:
                data[name] = presets.load_preset(name)
            except Exception:
                pass
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.update_info.configure(text=f"✅ Экспортировано {len(data)} пресетов")

    def _import_presets(self):
        from tkinter import filedialog, messagebox
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for name, cfg in data.items():
                presets.save_preset(name, cfg)
                count += 1
            if hasattr(self.parent, "_reload_presets_ui"):
                self.parent._reload_presets_ui()
            if hasattr(self.parent, "_reload_hotkeys"):
                self.parent._reload_hotkeys()
            self.update_info.configure(text=f"✅ Импортировано {count} пресетов")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось импортировать: {e}")

    # ---------- обновления ----------
    def _check_updates(self):
        self.update_info.configure(text="Проверка...")

        def worker():
            import urllib.request
            import json
            try:
                url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": "AutoTool"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode())
                tag = data.get("tag_name", "").lstrip("v")
                if not tag:
                    self.after(0, lambda: self.update_info.configure(text="❌ Не удалось узнать версию"))
                    return
                if tag == CURRENT_VERSION:
                    self.after(0, lambda: self.update_info.configure(
                        text=f"✅ У вас последняя версия (v{CURRENT_VERSION})"))
                else:
                    assets = data.get("assets", [])
                    exe_url = None
                    for a in assets:
                        if a.get("name", "").endswith(".exe"):
                            exe_url = a.get("browser_download_url")
                            break
                    if exe_url:
                        self.after(0, lambda: self.update_info.configure(
                            text=f"⬇ Скачиваю v{tag}..."))
                        self._download_exe(exe_url, tag)
                    else:
                        self.after(0, lambda: self.update_info.configure(
                            text=f"⬆ Доступна v{tag}, но exe не найден"))
            except Exception as e:
                print("update check error:", e)
                self.after(0, lambda: self.update_info.configure(
                    text="❌ Ошибка проверки (нет интернета?)"))

        threading.Thread(target=worker, daemon=True).start()

    def _download_exe(self, url, version):
        def worker():
            import urllib.request
            try:
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                os.makedirs(downloads, exist_ok=True)
                path = os.path.join(downloads, f"AutoTool-v{version}.exe")
                urllib.request.urlretrieve(url, path)
                self.after(0, lambda: self.update_info.configure(
                    text=f"✅ Скачано: {os.path.basename(path)}"))
                try:
                    if sys.platform == "win32":
                        subprocess.Popen(["explorer", "/select,", path])
                except Exception:
                    pass
            except Exception as e:
                print("download error:", e)
                self.after(0, lambda: self.update_info.configure(
                    text="❌ Ошибка скачивания"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Фокус ----------

    def _on_focus_out(self, event=None):
        """Если окно теряет фокус — отменяем биндинг."""
        try:
            focused = self.focus_get()
            if focused is not None and str(focused).startswith(str(self)):
                return
        except Exception:
            pass

        from core import hotkey_capture
        hotkey_capture._cleanup()
        # сбрасываем все кнопки ✎
        for key, entry in self._hotkey_widgets.items():
            pass  # кнопка сбросится сама при следующем вызове