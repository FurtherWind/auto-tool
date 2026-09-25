import os
import sys
import customtkinter as ctk
import keyboard

from CTkToolTip import CTkToolTip
from core.clicker import Clicker
from core.points import PointsClicker
from core.recorder import PointRecorder
from core.overlay import Overlay
from core import presets
from core import settings
from core.settings_window import SettingsWindow


def _resource_path(relative: str) -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


ctk.set_default_color_theme("blue")


def ms_to_display(ms: int):
    if ms % 60000 == 0 and ms >= 60000:
        return (ms // 60000, "мин")
    if ms % 1000 == 0 and ms >= 1000:
        return (ms // 1000, "сек")
    return (ms, "мс")


def display_to_ms(value: float, unit: str) -> int:
    if unit == "сек":
        return int(value * 1000)
    if unit == "мин":
        return int(value * 60000)
    return int(value)


class AutoToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Auto Tool")
        self.geometry("720x760")
        self.resizable(False, False)
        self._center_window()

        self.clicker = Clicker(on_finish=self._on_clicker_finished)
        self.points_clicker = PointsClicker(on_finish=self._on_points_finished)
        self.recorder = PointRecorder(on_point=self._on_point_recorded)
        self.overlay = Overlay(parent=self, on_close=self._on_overlay_closed)

        self.active_hotkeys: dict[str, str] = {}
        self.exit_hotkey = "f12"

        self.pressed_keys = []
        self.capturing_keys = False
        self.capture_hook = None

        self.capturing_hotkey = None
        self.capture_hotkey_hook = None

        self.current_preset = None
        self.recording_points = False

        ctk.set_appearance_mode("dark")

        self._build_ui()
        self._reload_hotkeys()
        self._reload_presets_ui()
        self.tray = None

        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._update_status_loop()

    def _center_window(self):
        self.update_idletasks()
        w, h = 720, 760
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ====================== UI ======================
    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(top_bar, text="Auto Tool", font=("Arial", 16, "bold")).pack(side="left")

        self.settings_btn = ctk.CTkButton(
            top_bar, text="⚙", width=40, height=32,
            command=self._open_settings,
            fg_color="#3B8ED0", hover_color="#1F6AA5",
            font=("Arial", 18),
        )
        self.settings_btn.pack(side="right")
        CTkToolTip(self.settings_btn, message="Настройки")

        self.tabview = ctk.CTkTabview(self, width=680, height=520)
        self.tabview.pack(padx=20, pady=15)

        self.tab_click = self.tabview.add("Клик")
        self.tab_keys = self.tabview.add("Клавиши")
        self.tab_points = self.tabview.add("Точки")
        self.tab_presets = self.tabview.add("Пресеты")

        self._build_click_tab()
        self._build_keys_tab()
        self._build_points_tab()
        self._build_presets_tab()

        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=20, pady=(0, 15))

        self.status_label = ctk.CTkLabel(bottom, text="Готово", text_color="#6bff8f")
        self.status_label.pack(side="left", padx=10)

        self.pause_btn = ctk.CTkButton(bottom, text="⏸ Пауза", width=110,
                                       command=self._toggle_pause,
                                       fg_color="#e67e22", hover_color="#d35400")
        self.pause_btn.pack(side="right", padx=5)

        stop_btn = ctk.CTkButton(bottom, text="СТОП ВСЁ", command=self._stop_all,
                                 fg_color="#c0392b", hover_color="#e74c3c")
        stop_btn.pack(side="right", padx=5)

    def _make_interval_row(self, parent, default_ms: int = 500):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=(0, 5))

        val, unit = ms_to_display(default_ms)

        e_val = ctk.CTkEntry(row, width=60)
        e_val.insert(0, str(val))
        e_val.pack(side="left", padx=(0, 3))

        u_val = ctk.CTkOptionMenu(row, values=["мс", "сек", "мин"], width=70)
        u_val.set(unit)
        u_val.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row, text="±").pack(side="left", padx=(0, 3))

        e_dev = ctk.CTkEntry(row, width=60)
        e_dev.insert(0, "0")
        e_dev.pack(side="left", padx=(0, 3))

        u_dev = ctk.CTkOptionMenu(row, values=["мс", "сек"], width=70)
        u_dev.set("мс")
        u_dev.pack(side="left")

        return e_val, u_val, e_dev, u_dev

    def _get_interval_ms(self, e_val, u_val, e_dev, u_dev):
        try:
            v = float(e_val.get() or "500")
        except ValueError:
            v = 500
        try:
            d = float(e_dev.get() or "0")
        except ValueError:
            d = 0

        base_ms = display_to_ms(v, u_val.get())
        dev_ms = display_to_ms(d, u_dev.get())

        if dev_ms < 0:
            dev_ms = 0

        min_ms = max(1, base_ms - dev_ms)
        max_ms = base_ms + dev_ms
        return min_ms, max_ms

    def _make_hotkey_row(self, parent, default: str = ""):
        row = ctk.CTkFrame(parent)
        row.pack(anchor="w", fill="x", pady=(0, 5))
        entry = ctk.CTkEntry(row, placeholder_text="напр. f6")
        if default:
            entry.insert(0, default)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry.bind("<Key>", lambda e: "break")
        btn = ctk.CTkButton(row, text="● Записать", width=110,
                            command=lambda: self._start_hotkey_capture(entry, btn))
        btn.pack(side="right")
        return entry, btn

    # ---------- вкладка КЛИК ----------
    def _build_click_tab(self):
        f = self.tab_click

        row1 = ctk.CTkFrame(f)
        row1.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row1, text="Кнопка:").pack(side="left")
        self.mouse_btn_var = ctk.StringVar(value="left")
        ctk.CTkOptionMenu(row1, values=["left", "right", "middle"],
                          variable=self.mouse_btn_var, width=100).pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Тип:").pack(side="left", padx=(15, 0))
        self.click_type_var = ctk.StringVar(value="single")
        ctk.CTkOptionMenu(row1, values=["single", "double"],
                          variable=self.click_type_var, width=100).pack(side="left", padx=5)

        ctk.CTkLabel(f, text="Интервал:").pack(anchor="w", pady=(10, 0))
        self.click_iv = self._make_interval_row(f, 500)
        ctk.CTkLabel(f, text="⚠ меньше 40 мс — возможны баги",
                     text_color="#c08400").pack(anchor="w")

        ctk.CTkLabel(f, text="Количество кликов (0 = ∞):").pack(anchor="w", pady=(10, 0))
        self.click_max = ctk.CTkEntry(f)
        self.click_max.insert(0, "0")
        self.click_max.pack(anchor="w", fill="x")

        ctk.CTkLabel(f, text="Хоткей запуска:").pack(anchor="w", pady=(10, 0))
        self.click_hotkey, _ = self._make_hotkey_row(f, "f6")

        ctk.CTkLabel(f, text="Жми хоткей — запуск, ещё раз — стоп",
                     text_color="#888").pack(anchor="w", pady=(10, 0))

    # ---------- вкладка КЛАВИШИ ----------
    def _build_keys_tab(self):
        f = self.tab_keys

        row = ctk.CTkFrame(f)
        row.pack(anchor="w", fill="x", pady=(10, 5))
        self.rec_btn = ctk.CTkButton(row, text="● Запись", command=self._start_key_capture,
                                     fg_color="#27ae60", hover_color="#2ecc71", width=110)
        self.rec_btn.pack(side="left", padx=5)
        ctk.CTkButton(row, text="🗑 Очистить", command=self._clear_keys,
                      fg_color="#c0392b", hover_color="#e74c3c", width=110).pack(side="left", padx=5)
        ctk.CTkButton(row, text="▶ Тест", command=self._toggle_keys,
                      fg_color="#3498db", hover_color="#2980b9", width=100).pack(side="left", padx=5)

        self.keys_display = ctk.CTkTextbox(f, height=40)
        self.keys_display.pack(fill="x", pady=5)
        self.keys_display.configure(state="disabled")

        ctk.CTkLabel(f, text="Esc — стоп. Повторы разрешены",
                     text_color="#888").pack(anchor="w")

        ctk.CTkLabel(f, text="Интервал:").pack(anchor="w", pady=(10, 0))
        self.keys_iv = self._make_interval_row(f, 500)
        ctk.CTkLabel(f, text="⚠ меньше 40 мс — возможны баги",
                     text_color="#c08400").pack(anchor="w")

        ctk.CTkLabel(f, text="Количество повторов (0 = ∞):").pack(anchor="w", pady=(10, 0))
        self.keys_max = ctk.CTkEntry(f)
        self.keys_max.insert(0, "0")
        self.keys_max.pack(anchor="w", fill="x")

        ctk.CTkLabel(f, text="Хоткей запуска:").pack(anchor="w", pady=(10, 0))
        self.keys_hotkey, _ = self._make_hotkey_row(f, "f7")

        ctk.CTkLabel(f, text="Имя пресета:").pack(anchor="w", pady=(10, 0))
        row_save = ctk.CTkFrame(f)
        row_save.pack(anchor="w", fill="x", pady=(0, 5))
        self.keys_preset_name = ctk.CTkEntry(row_save, height=36, placeholder_text="имя пресета")
        self.keys_preset_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row_save, text="💾 Сохранить", command=self._save_keys_preset,
                      height=36, width=140).pack(side="right")

    # ---------- вкладка ТОЧКИ ----------
    def _build_points_tab(self):
        f = self.tab_points

        row = ctk.CTkFrame(f)
        row.pack(anchor="w", fill="x", pady=(10, 5))
        self.points_rec_btn = ctk.CTkButton(
            row, text="● Запись", command=self._toggle_point_record,
            fg_color="#27ae60", hover_color="#2ecc71", width=110)
        self.points_rec_btn.pack(side="left", padx=5)
        ctk.CTkButton(row, text="▶ Тест", command=self._toggle_points,
                      fg_color="#3498db", hover_color="#2980b9", width=110).pack(side="left", padx=5)
        ctk.CTkButton(row, text="🗑 Очистить", command=self._clear_points,
                      fg_color="#c0392b", hover_color="#e74c3c", width=110).pack(side="left", padx=5)

        ctk.CTkLabel(f, text="Esc — стоп", text_color="#888").pack(anchor="w", pady=(0, 5))

        self.points_count_label = ctk.CTkLabel(f, text="Записано: 0 точек")
        self.points_count_label.pack(anchor="w", pady=(5, 5))

        self.points_list_frame = ctk.CTkScrollableFrame(f, height=40, label_text="Список точек")
        self.points_list_frame.pack(fill="x", pady=5)

        row1 = ctk.CTkFrame(f)
        row1.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row1, text="Интервал:").pack(side="left")
        self.points_iv = self._make_interval_row(row1, 500)

        row2 = ctk.CTkFrame(f)
        row2.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(row2, text="Прогонов:").pack(side="left")
        self.points_loops = ctk.CTkEntry(row2, width=70)
        self.points_loops.insert(0, "1")
        self.points_loops.pack(side="left", padx=(5, 15))
        ctk.CTkLabel(row2, text="Кнопка:").pack(side="left")
        self.points_mouse_var = ctk.StringVar(value="left")
        ctk.CTkOptionMenu(row2, values=["left", "right", "middle"],
                          variable=self.points_mouse_var, width=90).pack(side="left", padx=5)

        self.smooth_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Плавное перемещение курсора",
                        variable=self.smooth_var).pack(anchor="w", pady=(5, 0))

        self.show_overlay_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Показывать оверлей",
                        variable=self.show_overlay_var).pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(f, text="⚠ <40 мс — баги; >10 прогонов — баги",
                     text_color="#c08400").pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(f, text="Хоткей запуска:").pack(anchor="w", pady=(10, 0))
        self.points_hotkey, _ = self._make_hotkey_row(f, "f8")

        ctk.CTkLabel(f, text="Имя пресета:").pack(anchor="w", pady=(10, 0))
        row_save = ctk.CTkFrame(f)
        row_save.pack(anchor="w", fill="x", pady=(0, 5))
        self.points_preset_name = ctk.CTkEntry(row_save, height=36, placeholder_text="имя пресета")
        self.points_preset_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row_save, text="💾 Сохранить", command=self._save_points_preset,
                      height=36, width=140).pack(side="right")

    # ---------- вкладка ПРЕСЕТЫ ----------
    def _build_presets_tab(self):
        f = self.tab_presets

        self.presets_frame = ctk.CTkScrollableFrame(f, height=400)
        self.presets_frame.pack(fill="both", expand=True, pady=5)

        ctk.CTkButton(f, text="🔄 Обновить", command=self._reload_presets_ui,
                      height=32).pack(anchor="w", fill="x", pady=5)

        ctk.CTkLabel(f, text="F12 — выход", text_color="#888").pack(anchor="w")

    # ====================== статус ======================
    def _update_status_loop(self):
        try:
            if self.clicker.running:
                c = self.clicker.counter
                max_c = self.clicker.config.get("max_count", 0)
                suffix = f" ({c}/{max_c})" if max_c > 0 else f" ({c})"
                if self.clicker.paused:
                    self.status_label.configure(text=f"⏸ Пауза{suffix}",
                                                text_color="#e67e22")
                else:
                    self.status_label.configure(text=f"▶ Работает{suffix}",
                                                text_color="#6bff8f")
            elif self.points_clicker.running:
                c = self.points_clicker.counter
                loops = self.points_clicker.loops
                suffix = f" ({c}/{loops})" if loops > 0 else f" ({c}/∞)"
                if self.points_clicker.paused:
                    self.status_label.configure(text=f"⏸ Пауза{suffix}",
                                                text_color="#e67e22")
                else:
                    self.status_label.configure(text=f"▶ Точки{suffix}",
                                                text_color="#6bff8f")
        except Exception:
            pass
        self.after(500, self._update_status_loop)

    def _on_clicker_finished(self):
        self.after(0, lambda: self._status("✓ Пресет завершён"))

    def _on_points_finished(self):
        self.after(0, self._hide_overlay_safe)
        self.after(0, lambda: self._status("✓ Прогоны завершены"))
        if self.tray:
            try:
                self.tray.set_active(False)
            except Exception:
                pass

    # ====================== список точек ======================
    def _refresh_points_list(self):
        for w in self.points_list_frame.winfo_children():
            w.destroy()

        pts = self.recorder.get_points()
        self.points_count_label.configure(text=f"Записано: {len(pts)} точек")

        if not pts:
            ctk.CTkLabel(self.points_list_frame, text="(пусто)").pack(anchor="w", padx=5)
            return

        for i, (x, y) in enumerate(pts, start=1):
            row = ctk.CTkFrame(self.points_list_frame)
            row.pack(fill="x", pady=1, padx=2)
            ctk.CTkLabel(row, text=f"{i}. ({x}, {y})", anchor="w").pack(side="left", padx=8)
            ctk.CTkButton(row, text="✕", width=30, height=24,
                          fg_color="#c0392b", hover_color="#e74c3c",
                          command=lambda idx=i-1: self._remove_point(idx)).pack(side="right", padx=3)

    def _remove_point(self, index: int):
        pts = self.recorder.get_points()
        if 0 <= index < len(pts):
            pts.pop(index)
            self.recorder.points = pts
            self._refresh_points_list()
            self.overlay.update(pts)

    def _clear_points(self):
        self.recorder.clear()
        self._refresh_points_list()
        self.overlay.update([])

    def _on_point_recorded(self, pt):
        self.after(0, self._refresh_points_list)
        self.after(0, lambda: self.overlay.update(self.recorder.get_points()))

    # ====================== запись точек ======================
    def _toggle_point_record(self):
        if self.recording_points:
            self._stop_point_record()
        else:
            self._start_point_record()

    def _start_point_record(self):
        if self.recording_points:
            return
        self.recording_points = True
        self.points_rec_btn.configure(text="■ Стоп", fg_color="#c0392b", hover_color="#e74c3c")
        self._status("Запись... кликай, Esc — стоп")

        self.update_idletasks()
        x1 = self.winfo_rootx()
        y1 = self.winfo_rooty()
        x2 = x1 + self.winfo_width()
        y2 = y1 + self.winfo_height()
        self.recorder.set_ignore_rect(x1, y1, x2, y2)

        self.overlay.show(self.recorder.get_points())
        self.recorder.start()

    def _stop_point_record(self):
        if not self.recording_points:
            return
        self.recording_points = False
        self.recorder.stop()
        self.points_rec_btn.configure(text="● Запись", fg_color="#27ae60", hover_color="#2ecc71")
        self._refresh_points_list()
        self.overlay.hide()
        self._status(f"Записано: {len(self.recorder.get_points())}")

    # ====================== запуск ======================
    def _toggle_click(self):
        if self.clicker.running and self.current_preset == "__click__":
            self._stop_all()
            return
        min_ms, max_ms = self._get_interval_ms(*self.click_iv)
        try:
            max_c = int(self.click_max.get() or "0")
        except ValueError:
            max_c = 0

        self.clicker.stop()
        self.points_clicker.stop()
        self.clicker.update_config({
            "mode": "click",
            "mouse_button": self.mouse_btn_var.get(),
            "click_type": self.click_type_var.get(),
            "interval_min": min_ms,
            "interval_max": max_ms,
            "max_count": max_c,
        })
        self.clicker.start()
        self.current_preset = "__click__"
        self._update_pause_button()
        if self.tray:
            try:
                self.tray.set_active(True)
            except Exception:
                pass

    def _toggle_keys(self):
        if self.clicker.running and self.current_preset == "__keys__":
            self._stop_all()
            return
        if not self.pressed_keys:
            self._status("Сначала запиши клавиши!", error=True)
            return
        min_ms, max_ms = self._get_interval_ms(*self.keys_iv)
        try:
            max_c = int(self.keys_max.get() or "0")
        except ValueError:
            max_c = 0

        self.clicker.stop()
        self.points_clicker.stop()
        self.clicker.update_config({
            "mode": "keys",
            "keys": list(self.pressed_keys),
            "interval_min": min_ms,
            "interval_max": max_ms,
            "max_count": max_c,
        })
        self.clicker.start()
        self.current_preset = "__keys__"
        self._update_pause_button()
        if self.tray:
            try:
                self.tray.set_active(True)
            except Exception:
                pass

    def _toggle_points(self):
        if self.points_clicker.running and self.current_preset == "__points__":
            self._stop_all()
            return
        pts = self.recorder.get_points()
        if not pts:
            self._status("Сначала запиши точки!", error=True)
            return
        min_ms, max_ms = self._get_interval_ms(*self.points_iv)
        try:
            loops = int(self.points_loops.get() or "1")
        except ValueError:
            loops = 1

        self.clicker.stop()
        self.points_clicker.stop()
        self.points_clicker.update(
            points=pts,
            interval_min=min_ms,
            interval_max=max_ms,
            mouse_button=self.points_mouse_var.get(),
            loops=loops,
            smooth=self.smooth_var.get(),
        )
        self.points_clicker.start()
        if self.show_overlay_var.get():
            self.overlay.show(pts)
        self.current_preset = "__points__"
        self._update_pause_button()
        if self.tray:
            try:
                self.tray.set_active(True)
            except Exception:
                pass

    def _toggle_pause(self):
        if self.clicker.running:
            self.clicker.toggle_pause()
            self._update_pause_button()
        elif self.points_clicker.running:
            self.points_clicker.toggle_pause()
            self._update_pause_button()
        else:
            self._status("Ничего не запущено", error=True)

    def _update_pause_button(self):
        paused = False
        if self.clicker.running:
            paused = self.clicker.paused
        elif self.points_clicker.running:
            paused = self.points_clicker.paused

        if paused:
            self.pause_btn.configure(text="▶ Продолжить",
                                     fg_color="#27ae60", hover_color="#2ecc71")
        else:
            self.pause_btn.configure(text="⏸ Пауза",
                                     fg_color="#e67e22", hover_color="#d35400")

    # ====================== хоткеи ======================
    def _reload_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.active_hotkeys.clear()

        s = settings.load()
        hk = s.get("hotkeys", {})

        exit_hk = hk.get("exit", "f12").strip().lower()
        pause_hk = hk.get("pause", "").strip().lower()
        stop_all_hk = hk.get("stop_all", "").strip().lower()

        # обновляем поля на вкладках
        try:
            self.click_hotkey.delete(0, "end")
            self.click_hotkey.insert(0, hk.get("click", ""))
            self.keys_hotkey.delete(0, "end")
            self.keys_hotkey.insert(0, hk.get("keys", ""))
            self.points_hotkey.delete(0, "end")
            self.points_hotkey.insert(0, hk.get("points", ""))
        except Exception:
            pass

        if exit_hk:
            try:
                keyboard.add_hotkey(exit_hk, lambda: self.after(0, self._exit_app))
            except Exception as e:
                print("exit hotkey error:", e)

        if stop_all_hk:
            try:
                keyboard.add_hotkey(stop_all_hk, lambda: self.after(0, self._stop_all))
            except Exception as e:
                print("stop_all hotkey error:", e)

        if pause_hk:
            try:
                keyboard.add_hotkey(pause_hk, lambda: self.after(0, self._toggle_pause))
            except Exception as e:
                print("pause hotkey error:", e)

        try:
            keyboard.add_hotkey("esc", lambda: self.after(0, self._on_escape_pressed))
        except Exception:
            pass

        click_hk = hk.get("click", "").strip().lower()
        if click_hk:
            try:
                keyboard.add_hotkey(click_hk, lambda: self.after(0, self._toggle_click))
                self.active_hotkeys[click_hk] = "__click__"
            except Exception as e:
                print(f"click hotkey error: {e}")

        keys_hk = hk.get("keys", "").strip().lower()
        if keys_hk:
            try:
                keyboard.add_hotkey(keys_hk, lambda: self.after(0, self._toggle_keys))
                self.active_hotkeys[keys_hk] = "__keys__"
            except Exception as e:
                print(f"keys hotkey error: {e}")

        points_hk = hk.get("points", "").strip().lower()
        if points_hk:
            try:
                keyboard.add_hotkey(points_hk, lambda: self.after(0, self._toggle_points))
                self.active_hotkeys[points_hk] = "__points__"
            except Exception as e:
                print(f"points hotkey error: {e}")

        for name in presets.list_presets():
            try:
                cfg = presets.load_preset(name)
            except Exception:
                continue
            phk = cfg.get("hotkey", "").strip().lower()
            if not phk or phk in (exit_hk, "esc", pause_hk, stop_all_hk):
                continue
            if phk in self.active_hotkeys:
                continue
            try:
                keyboard.add_hotkey(phk, lambda n=name: self.after(0, lambda: self._toggle_preset(n)))
                self.active_hotkeys[phk] = name
            except Exception as e:
                print(f"preset hotkey error: {e}")

    def _toggle_preset(self, name: str):
        if self.clicker.running or self.points_clicker.running:
            if self.current_preset == name:
                self._stop_all()
                return
        self._start_preset(name)
        if self.tray:
            try:
                self.tray.set_active(True)
            except Exception:
                pass

    def _start_preset(self, name: str):
        try:
            cfg = presets.load_preset(name)
        except Exception as e:
            self._status(f"Ошибка: {e}", error=True)
            return

        self.clicker.stop()
        self.points_clicker.stop()

        mode = cfg.get("mode", "click")

        if mode == "points":
            self.points_clicker.update(
                points=cfg.get("points", []),
                interval_min=cfg.get("interval_min", 500),
                interval_max=cfg.get("interval_max", 500),
                mouse_button=cfg.get("mouse_button", "left"),
                loops=cfg.get("loops", 1),
                smooth=cfg.get("smooth", True),
            )
            self.points_clicker.start()
            if cfg.get("show_overlay", True):
                self.overlay.show(cfg.get("points", []))
        else:
            self.clicker.update_config(cfg)
            self.clicker.start()

        self.current_preset = name
        hk = cfg.get("hotkey", "").upper()
        self._status(f"▶ {name}  [{hk}]")

    def _stop_all(self):
        self.clicker.stop()
        self.points_clicker.stop()
        self.current_preset = None
        self._update_pause_button()
        try:
            self.overlay.hide()
        except Exception:
            pass
        self._status("Остановлено")
        if self.tray:
            try:
                self.tray.set_active(False)
            except Exception:
                pass

    def _open_settings(self):
        icon_path = _resource_path("icon.ico")
        if hasattr(self, "_settings_window"):
            try:
                if self._settings_window.winfo_exists():
                    self._settings_window.focus()
                    self._settings_window.lift()
                    return
            except Exception:
                pass

        self._settings_window = SettingsWindow(
            parent=self,
            on_hotkeys_change=self._reload_hotkeys,
            icon_path=icon_path,
        )

    def _on_escape_pressed(self):
        if self.recording_points:
            self._stop_point_record()
            return
        if self.capturing_keys:
            self._stop_key_capture()
            return
        if self.capturing_hotkey is not None:
            self._cancel_hotkey_capture()
            return
        self.clicker.stop()
        self.points_clicker.stop()
        self.current_preset = None
        self.after(30, self._hide_overlay_safe)
        self._status("Остановлено (Esc)")
        if self.tray:
            try:
                self.tray.set_active(False)
            except Exception:
                pass

    def _hide_overlay_safe(self):
        try:
            self.overlay.hide()
        except Exception:
            pass

    def _hide_to_tray(self):
        self.withdraw()

    def _show_from_tray(self):
        self.after(0, self._do_show_from_tray)

    def _do_show_from_tray(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception as e:
            print("show from tray error:", e)

    def _stop_from_tray(self):
        self.after(0, self._stop_all)

    def _exit_from_tray(self):
        self.after(0, self._exit_app)

    def _exit_app(self):
        try:
            if hasattr(self, "_settings_window") and self._settings_window.winfo_exists():
                self._settings_window.destroy()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass

        try:
            self.clicker.stop()
        except Exception:
            pass
        try:
            self.points_clicker.stop()
        except Exception:
            pass
        if self.recording_points:
            try:
                self.recorder.stop()
            except Exception:
                pass
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.overlay.close()
        except Exception:
            pass
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        import os
        os._exit(0)

    def _status(self, text: str, error: bool = False):
        color = "#ff6b6b" if error else "#6bff8f"
        self.status_label.configure(text=text, text_color=color)

    def _on_overlay_closed(self):
        pass

    # ====================== запись клавиш ======================
    def _start_key_capture(self):
        if self.capturing_keys:
            return
        self.capturing_keys = True
        self.pressed_keys = []
        self._refresh_keys_display()
        self.rec_btn.configure(text="■ Стоп", fg_color="#c0392b", hover_color="#e74c3c",
                               command=self._stop_key_capture)
        self._status("Запись клавиш... Esc — стоп, клик в другое окно — стоп")

        def on_event(e):
            if not self.capturing_keys:
                return False
            if e.event_type == "down":
                name = e.name
                if name == "esc":
                    self.after(0, self._stop_key_capture)
                    return
                self.pressed_keys.append(name)
                self.after(0, self._refresh_keys_display)

        self.capture_hook = keyboard.hook(on_event)

        # следим за кликами вне окна — останавливаем запись
        from pynput import mouse as _mouse

        def on_click(x, y, button, pressed_state):
            if not pressed_state or not self.capturing_keys:
                return
            try:
                rx1 = self.winfo_rootx()
                ry1 = self.winfo_rooty()
                rx2 = rx1 + self.winfo_width()
                ry2 = ry1 + self.winfo_height()
                if not (rx1 <= x <= rx2 and ry1 <= y <= ry2):
                    self.after(0, self._stop_key_capture)
            except Exception:
                pass

        self._key_capture_mouse = _mouse.Listener(on_click=on_click)
        self._key_capture_mouse.start()

    def _stop_key_capture(self):
        if not self.capturing_keys:
            return
        self.capturing_keys = False
        try:
            keyboard.unhook(self.capture_hook)
        except Exception:
            pass
        self.capture_hook = None

        # останавливаем mouse listener
        try:
            if hasattr(self, "_key_capture_mouse") and self._key_capture_mouse:
                self._key_capture_mouse.stop()
                self._key_capture_mouse = None
        except Exception:
            pass

        self.rec_btn.configure(text="● Запись", fg_color="#27ae60", hover_color="#2ecc71",
                               command=self._start_key_capture)
        self._status(f"Записано клавиш: {len(self.pressed_keys)}")

    def _refresh_keys_display(self):
        self.keys_display.configure(state="normal")
        self.keys_display.delete("1.0", "end")
        self.keys_display.insert("1.0", " + ".join(self.pressed_keys) if self.pressed_keys else "")
        self.keys_display.configure(state="disabled")

    def _clear_keys(self):
        self.pressed_keys = []
        self._refresh_keys_display()

    # ====================== запись хоткея ======================
    def _start_hotkey_capture(self, entry: ctk.CTkEntry, btn: ctk.CTkButton):
        if self.capturing_hotkey is not None:
            return
        self.capturing_hotkey = entry
        btn.configure(text="● Жми...", fg_color="#c0392b", hover_color="#e74c3c")
        self._status("Жми комбо и отпусти (Esc или клик мимо — отмена)")

        from core import hotkey_capture

        def on_done(combo):
            self.capturing_hotkey = None
            if entry is not None:
                entry.delete(0, "end")
                entry.insert(0, combo)
                key = None
                if entry is self.click_hotkey:
                    key = "click"
                elif entry is self.keys_hotkey:
                    key = "keys"
                elif entry is self.points_hotkey:
                    key = "points"
                if key:
                    settings.set_value(f"hotkeys.{key}", combo.lower())
            self._reset_hotkey_buttons()
            self._reload_hotkeys()
            self._status(f"Хоткей: {combo}")

        def on_cancel():
            self.capturing_hotkey = None
            self._reset_hotkey_buttons()
            self._status("Отменено", error=True)

        hotkey_capture.capture(on_done, on_cancel=on_cancel, entry_widget=entry)

    def _cancel_hotkey_capture(self):
        try:
            from core import hotkey_capture
            hotkey_capture.cancel()
        except Exception:
            pass
        self.capturing_hotkey = None
        self._reset_hotkey_buttons()
        self._status("Отменено", error=True)

    def _normalize_key(self, name: str) -> str:
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

    def _reset_hotkey_buttons(self):
        for tab in (self.tab_click, self.tab_keys, self.tab_points):
            for widget in tab.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkButton) and "Жми" in child.cget("text"):
                            child.configure(text="● Записать", fg_color=("#3B8ED0", "#1F6AA5"))

    # ====================== пресеты ======================
    def _reload_presets_ui(self):
        for w in self.presets_frame.winfo_children():
            w.destroy()

        names = presets.list_presets()
        if not names:
            ctk.CTkLabel(self.presets_frame, text="Пока нет пресетов").pack(anchor="w", pady=5)
            return

        for name in names:
            try:
                cfg = presets.load_preset(name)
            except Exception:
                continue
            self._make_preset_row(name, cfg)

    def _make_preset_row(self, name: str, cfg: dict):
        row = ctk.CTkFrame(self.presets_frame)
        row.pack(fill="x", pady=3, padx=3)

        mode = cfg.get("mode", "click")
        hk = cfg.get("hotkey", "—")
        mode_label = {"click": "клик", "keys": "клавиши", "points": "точки"}.get(mode, mode)

        if mode == "points":
            extra = f" • {len(cfg.get('points', []))} точек"
        else:
            extra = ""

        info = f"[{mode_label}]  {name}  •  {hk.upper()}{extra}"
        ctk.CTkLabel(row, text=info, anchor="w").pack(side="left", padx=10, pady=5)

        ctk.CTkButton(row, text="▶", width=40,
                      command=lambda: self._start_preset(name)).pack(side="right", padx=3, pady=3)
        ctk.CTkButton(row, text="✎", width=40,
                      command=lambda: self._load_to_editor(name, cfg)).pack(side="right", padx=3, pady=3)
        ctk.CTkButton(row, text="✏", width=40, fg_color="#8e44ad", hover_color="#9b59b6",
                      command=lambda: self._rename_preset(name)).pack(side="right", padx=3, pady=3)
        ctk.CTkButton(row, text="🗑", width=40, fg_color="#c0392b", hover_color="#e74c3c",
                      command=lambda: self._delete_preset(name)).pack(side="right", padx=3, pady=3)

    def _load_to_editor(self, name: str, cfg: dict):
        mode = cfg.get("mode", "click")
        if mode == "click":
            self.tabview.set("Клик")
            self.mouse_btn_var.set(cfg.get("mouse_button", "left"))
            self.click_type_var.set(cfg.get("click_type", "single"))
            self._set_interval(self.click_iv, cfg.get("interval_min", 500), cfg.get("interval_max", 500))
            self.click_max.delete(0, "end")
            self.click_max.insert(0, str(cfg.get("max_count", 0)))
            self.click_hotkey.delete(0, "end")
            self.click_hotkey.insert(0, cfg.get("hotkey", ""))
        elif mode == "keys":
            self.tabview.set("Клавиши")
            self.pressed_keys = list(cfg.get("keys", []))
            self._refresh_keys_display()
            self._set_interval(self.keys_iv, cfg.get("interval_min", 500), cfg.get("interval_max", 500))
            self.keys_max.delete(0, "end")
            self.keys_max.insert(0, str(cfg.get("max_count", 0)))
            self.keys_hotkey.delete(0, "end")
            self.keys_hotkey.insert(0, cfg.get("hotkey", ""))
            self.keys_preset_name.delete(0, "end")
            self.keys_preset_name.insert(0, name)
        elif mode == "points":
            self.tabview.set("Точки")
            self.recorder.points = list(cfg.get("points", []))
            self._refresh_points_list()
            self._set_interval(self.points_iv, cfg.get("interval_min", 500), cfg.get("interval_max", 500))
            self.points_loops.delete(0, "end")
            self.points_loops.insert(0, str(cfg.get("loops", 1)))
            self.points_mouse_var.set(cfg.get("mouse_button", "left"))
            self.smooth_var.set(cfg.get("smooth", True))
            self.show_overlay_var.set(cfg.get("show_overlay", True))
            self.points_hotkey.delete(0, "end")
            self.points_hotkey.insert(0, cfg.get("hotkey", ""))
            self.points_preset_name.delete(0, "end")
            self.points_preset_name.insert(0, name)

    def _set_interval(self, iv, min_ms, max_ms):
        e_val, u_val, e_dev, u_dev = iv
        base_ms = (min_ms + max_ms) // 2
        dev_ms = max_ms - base_ms

        v, u = ms_to_display(base_ms)
        e_val.delete(0, "end"); e_val.insert(0, str(v)); u_val.set(u)

        if dev_ms >= 1000 and dev_ms % 1000 == 0:
            e_dev.delete(0, "end"); e_dev.insert(0, str(dev_ms // 1000)); u_dev.set("сек")
        else:
            e_dev.delete(0, "end"); e_dev.insert(0, str(dev_ms)); u_dev.set("мс")

    def _delete_preset(self, name: str):
        presets.delete_preset(name)
        if self.current_preset == name:
            self._stop_all()
        self._reload_hotkeys()
        self._reload_presets_ui()

    def _rename_preset(self, name: str):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Переименовать пресет")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.after(50, lambda: dialog.lift())
        dialog.after(100, lambda: dialog.focus_force())

        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 150) // 2
        dialog.geometry(f"400x150+{x}+{y}")

        ctk.CTkLabel(dialog, text="Новое имя пресета:").pack(anchor="w", padx=15, pady=(15, 5))

        entry = ctk.CTkEntry(dialog, width=360)
        entry.insert(0, name)
        entry.pack(padx=15, pady=5)
        entry.focus_set()
        entry.select_range(0, "end")

        def do_rename():
            new_name = entry.get().strip()
            if not new_name or new_name == name:
                dialog.destroy()
                return
            if new_name in presets.list_presets():
                self._status(f"Пресет '{new_name}' уже существует!", error=True)
                return
            try:
                cfg = presets.load_preset(name)
                presets.save_preset(new_name, cfg)
                presets.delete_preset(name)
                if self.current_preset == name:
                    self.current_preset = new_name
                self._reload_hotkeys()
                self._reload_presets_ui()
                self._status(f"Переименован: {name} → {new_name}")
            except Exception as e:
                self._status(f"Ошибка: {e}", error=True)
            dialog.destroy()

        def on_enter(event):
            do_rename()

        entry.bind("<Return>", on_enter)

        row = ctk.CTkFrame(dialog)
        row.pack(pady=10)
        ctk.CTkButton(row, text="Переименовать", command=do_rename,
                      fg_color="#27ae60", hover_color="#2ecc71").pack(side="left", padx=5)
        ctk.CTkButton(row, text="Отмена", command=dialog.destroy,
                      fg_color="#7f8c8d", hover_color="#95a5a6").pack(side="left", padx=5)

    def _save_keys_preset(self):
        name = self.keys_preset_name.get().strip()
        if not name:
            self._status("Впиши имя пресета!", error=True)
            return
        if not self.pressed_keys:
            self._status("Сначала запиши клавиши!", error=True)
            return
        hk = self.keys_hotkey.get().strip().lower()
        if not hk:
            self._status("Запиши хоткей!", error=True)
            return
        min_ms, max_ms = self._get_interval_ms(*self.keys_iv)
        try:
            max_c = int(self.keys_max.get() or "0")
        except ValueError:
            max_c = 0
        cfg = {
            "mode": "keys",
            "keys": list(self.pressed_keys),
            "interval_min": min_ms,
            "interval_max": max_ms,
            "max_count": max_c,
            "hotkey": hk,
        }
        presets.save_preset(name, cfg)
        self._reload_hotkeys()
        self._reload_presets_ui()
        self._status(f"Сохранён: {name}")

    def _save_points_preset(self):
        name = self.points_preset_name.get().strip()
        if not name:
            self._status("Впиши имя пресета!", error=True)
            return
        pts = self.recorder.get_points()
        if not pts:
            self._status("Сначала запиши точки!", error=True)
            return
        hk = self.points_hotkey.get().strip().lower()
        if not hk:
            self._status("Запиши хоткей!", error=True)
            return
        min_ms, max_ms = self._get_interval_ms(*self.points_iv)
        try:
            loops = int(self.points_loops.get() or "1")
        except ValueError:
            loops = 1
        cfg = {
            "mode": "points",
            "points": pts,
            "interval_min": min_ms,
            "interval_max": max_ms,
            "mouse_button": self.points_mouse_var.get(),
            "show_overlay": self.show_overlay_var.get(),
            "smooth": self.smooth_var.get(),
            "loops": loops,
            "hotkey": hk,
        }
        presets.save_preset(name, cfg)
        self._reload_hotkeys()
        self._reload_presets_ui()
        self._status(f"Сохранён: {name} ({len(pts)} точек)")