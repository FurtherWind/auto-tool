import customtkinter as ctk
import keyboard

from core.clicker import Clicker
from core import presets


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AutoToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Auto Tool")
        self.geometry("660x640")
        self.resizable(False, False)

        self.clicker = Clicker()
        self.active_hotkeys: dict[str, str] = {}
        self.exit_hotkey = "f12"

        self.pressed_keys = []
        self.capturing_keys = False
        self.capture_hook = None

        self.capturing_hotkey = None
        self.capture_hotkey_hook = None
        self.capture_hotkey_pressed = []
        self.capture_hotkey_released = set()

        self.current_preset = None

        self._build_ui()
        self._reload_hotkeys()

    # ---------- UI ----------
    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self, width=620, height=520)
        self.tabview.pack(padx=20, pady=15)

        self.tab_click = self.tabview.add("Кликер")
        self.tab_keys = self.tabview.add("Клавиши")
        self.tab_presets = self.tabview.add("Пресеты")

        self._build_click_tab()
        self._build_keys_tab()
        self._build_presets_tab()

        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=20, pady=(0, 15))

        self.status_label = ctk.CTkLabel(bottom, text="Остановлено", text_color="#ff6b6b")
        self.status_label.pack(side="left", padx=10)

        ctk.CTkButton(bottom, text="СТОП ВСЁ", command=self._stop_all,
                      fg_color="#c0392b", hover_color="#e74c3c").pack(side="right", padx=10)

    def _make_hotkey_row(self, parent, default: str):
        row = ctk.CTkFrame(parent)
        row.pack(anchor="w", fill="x", pady=(0, 5))
        entry = ctk.CTkEntry(row, placeholder_text="напр. ctrl+alt+f9")
        entry.insert(0, default)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry.bind("<Key>", lambda e: "break")
        btn = ctk.CTkButton(row, text="● Записать", width=110,
                            command=lambda: self._start_hotkey_capture(entry, btn))
        btn.pack(side="right")
        return entry, btn

    def _build_click_tab(self):
        f = self.tab_click

        ctk.CTkLabel(f, text="Кнопка мыши:").pack(anchor="w", pady=(10, 0))
        self.mouse_btn_var = ctk.StringVar(value="left")
        ctk.CTkOptionMenu(f, values=["left", "right", "middle"],
                          variable=self.mouse_btn_var).pack(anchor="w")

        ctk.CTkLabel(f, text="Тип клика:").pack(anchor="w", pady=(10, 0))
        self.click_type_var = ctk.StringVar(value="single")
        ctk.CTkOptionMenu(f, values=["single", "double"],
                          variable=self.click_type_var).pack(anchor="w")

        ctk.CTkLabel(f, text="Интервал (мс):").pack(anchor="w", pady=(10, 0))
        self.click_interval = ctk.CTkEntry(f)
        self.click_interval.insert(0, "50")
        self.click_interval.pack(anchor="w")

        ctk.CTkLabel(f, text="Хоткей запуска:").pack(anchor="w", pady=(10, 0))
        self.click_hotkey, _ = self._make_hotkey_row(f, "ctrl+alt+f9")

        ctk.CTkLabel(f, text="Имя пресета:").pack(anchor="w", pady=(10, 0))
        self.click_preset_name = ctk.CTkEntry(f)
        self.click_preset_name.pack(anchor="w", fill="x")

        ctk.CTkButton(f, text="💾 Сохранить пресет (Кликер)",
                      command=self._save_click_preset).pack(anchor="w", pady=10)

    def _build_keys_tab(self):
        f = self.tab_keys

        ctk.CTkLabel(f, text="Клавиши (запись):").pack(anchor="w", pady=(10, 0))
        self.keys_display = ctk.CTkTextbox(f, height=60)
        self.keys_display.pack(fill="x", pady=5)
        self.keys_display.configure(state="disabled")

        row = ctk.CTkFrame(f)
        row.pack(anchor="w", pady=5)
        self.rec_btn = ctk.CTkButton(row, text="● Начать запись", command=self._start_key_capture,
                                     fg_color="#27ae60", hover_color="#2ecc71")
        self.rec_btn.pack(side="left", padx=5)
        ctk.CTkButton(row, text="Очистить", command=self._clear_keys).pack(side="left", padx=5)

        ctk.CTkLabel(f, text="Интервал (мс):").pack(anchor="w", pady=(10, 0))
        self.keys_interval = ctk.CTkEntry(f)
        self.keys_interval.insert(0, "50")
        self.keys_interval.pack(anchor="w")

        ctk.CTkLabel(f, text="Хоткей запуска:").pack(anchor="w", pady=(10, 0))
        self.keys_hotkey, _ = self._make_hotkey_row(f, "ctrl+alt+f10")

        ctk.CTkLabel(f, text="Имя пресета:").pack(anchor="w", pady=(10, 0))
        self.keys_preset_name = ctk.CTkEntry(f)
        self.keys_preset_name.pack(anchor="w", fill="x")

        ctk.CTkButton(f, text="💾 Сохранить пресет (Клавиши)",
                      command=self._save_keys_preset).pack(anchor="w", pady=10)

    def _build_presets_tab(self):
        f = self.tab_presets

        ctk.CTkLabel(f, text="Сохранённые пресеты:").pack(anchor="w", pady=(10, 0))

        self.presets_frame = ctk.CTkScrollableFrame(f, height=300)
        self.presets_frame.pack(fill="both", expand=True, pady=5)

        ctk.CTkButton(f, text="🔄 Обновить список",
                      command=self._reload_presets_ui).pack(anchor="w", pady=5)

        ctk.CTkLabel(f, text="F12 — стоп всё и выход",
                     text_color="#888").pack(anchor="w", pady=(5, 0))

    # ---------- пресеты UI ----------
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

        info = f"[{mode}]  {name}  •  хоткей: {hk.upper()}"
        ctk.CTkLabel(row, text=info, anchor="w").pack(side="left", padx=10, pady=5)

        ctk.CTkButton(row, text="▶", width=40,
                      command=lambda: self._start_preset(name)).pack(side="right", padx=3, pady=3)
        ctk.CTkButton(row, text="✎", width=40,
                      command=lambda: self._load_to_editor(name, cfg)).pack(side="right", padx=3, pady=3)
        ctk.CTkButton(row, text="🗑", width=40, fg_color="#c0392b", hover_color="#e74c3c",
                      command=lambda: self._delete_preset(name)).pack(side="right", padx=3, pady=3)

    def _load_to_editor(self, name: str, cfg: dict):
        mode = cfg.get("mode", "click")
        if mode == "click":
            self.tabview.set("Кликер")
            self.mouse_btn_var.set(cfg.get("mouse_button", "left"))
            self.click_type_var.set(cfg.get("click_type", "single"))
            self.click_interval.delete(0, "end")
            self.click_interval.insert(0, str(cfg.get("interval_ms", 50)))
            self.click_hotkey.delete(0, "end")
            self.click_hotkey.insert(0, cfg.get("hotkey", ""))
            self.click_preset_name.delete(0, "end")
            self.click_preset_name.insert(0, name)
        else:
            self.tabview.set("Клавиши")
            self.pressed_keys = list(cfg.get("keys", []))
            self._refresh_keys_display()
            self.keys_interval.delete(0, "end")
            self.keys_interval.insert(0, str(cfg.get("interval_ms", 50)))
            self.keys_hotkey.delete(0, "end")
            self.keys_hotkey.insert(0, cfg.get("hotkey", ""))
            self.keys_preset_name.delete(0, "end")
            self.keys_preset_name.insert(0, name)

    def _delete_preset(self, name: str):
        presets.delete_preset(name)
        # если удалили запущенный — стоп
        if self.current_preset == name:
            self._stop_all()
        self._reload_hotkeys()
        self._reload_presets_ui()

    # ---------- сохранение ----------
    def _save_click_preset(self):
        name = self.click_preset_name.get().strip()
        if not name:
            self._status("Впиши имя пресета!", error=True)
            return
        hk = self.click_hotkey.get().strip().lower()
        if not hk:
            self._status("Запиши хоткей!", error=True)
            return
        cfg = {
            "mode": "click",
            "mouse_button": self.mouse_btn_var.get(),
            "click_type": self.click_type_var.get(),
            "interval_ms": int(self.click_interval.get() or "50"),
            "hotkey": hk,
        }
        presets.save_preset(name, cfg)
        self._reload_hotkeys()
        self._reload_presets_ui()
        self._status(f"Сохранён: {name}")

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
        cfg = {
            "mode": "keys",
            "keys": list(self.pressed_keys),
            "interval_ms": int(self.keys_interval.get() or "50"),
            "hotkey": hk,
        }
        presets.save_preset(name, cfg)
        self._reload_hotkeys()
        self._reload_presets_ui()
        self._status(f"Сохранён: {name}")

    # ---------- хоткеи ----------
    def _reload_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.active_hotkeys.clear()

        try:
            keyboard.add_hotkey(self.exit_hotkey, lambda: self.after(0, self._exit_app))
        except Exception as e:
            print("exit hotkey error:", e)

        for name in presets.list_presets():
            try:
                cfg = presets.load_preset(name)
            except Exception:
                continue
            hk = cfg.get("hotkey", "").strip().lower()
            if not hk or hk == self.exit_hotkey:
                continue
            if hk in self.active_hotkeys:
                print(f"конфликт хоткеев: {hk} — {name} пропущен")
                continue
            try:
                keyboard.add_hotkey(hk, lambda n=name: self.after(0, lambda: self._toggle_preset(n)))
                self.active_hotkeys[hk] = name
            except Exception as e:
                print(f"не смог повесить {hk}: {e}")

    def _toggle_preset(self, name: str):
        if self.clicker.running and self.current_preset == name:
            self._stop_all()
            return
        self._start_preset(name)

    def _start_preset(self, name: str):
        try:
            cfg = presets.load_preset(name)
        except Exception as e:
            self._status(f"Ошибка: {e}", error=True)
            return
        self.clicker.stop()
        self.clicker.update_config(cfg)
        self.clicker.start()
        self.current_preset = name
        hk = cfg.get("hotkey", "").upper()
        self._status(f"Работает: {name}  [{hk}]")

    def _stop_all(self):
        self.clicker.stop()
        self.current_preset = None
        self._status("Остановлено")

    def _exit_app(self):
        self._stop_all()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()

    def _status(self, text: str, error: bool = False):
        color = "#ff6b6b" if error else "#6bff8f"
        self.status_label.configure(text=text, text_color=color)

    # ---------- запись клавиш (для спама) ----------
    def _start_key_capture(self):
        if self.capturing_keys:
            return
        self.capturing_keys = True
        self.pressed_keys = []
        self._refresh_keys_display()
        self.rec_btn.configure(text="■ Стоп записи", fg_color="#c0392b", hover_color="#e74c3c",
                               command=self._stop_key_capture)
        self._status("Запись... жми клавиши, потом Стоп или Esc")

        def on_event(e):
            if e.event_type == "down":
                name = e.name
                if name == "esc":
                    self.after(0, self._stop_key_capture)
                    return
                if name not in self.pressed_keys:
                    self.pressed_keys.append(name)
                    self.after(0, self._refresh_keys_display)

        self.capture_hook = keyboard.hook(on_event)

    def _stop_key_capture(self):
        if not self.capturing_keys:
            return
        self.capturing_keys = False
        try:
            keyboard.unhook(self.capture_hook)
        except Exception:
            pass
        self.capture_hook = None
        self.rec_btn.configure(text="● Начать запись", fg_color="#27ae60", hover_color="#2ecc71",
                               command=self._start_key_capture)
        self._status("Запись остановлена")

    def _refresh_keys_display(self):
        self.keys_display.configure(state="normal")
        self.keys_display.delete("1.0", "end")
        self.keys_display.insert("1.0", " + ".join(self.pressed_keys) if self.pressed_keys else "")
        self.keys_display.configure(state="disabled")

    def _clear_keys(self):
        self.pressed_keys = []
        self._refresh_keys_display()

    # ---------- запись хоткея (комбо) ----------
    def _start_hotkey_capture(self, entry: ctk.CTkEntry, btn: ctk.CTkButton):
        if self.capturing_hotkey is not None:
            return
        self.capturing_hotkey = entry
        self.capture_hotkey_pressed = []
        self.capture_hotkey_released = set()
        btn.configure(text="● Жми комбо...", fg_color="#c0392b", hover_color="#e74c3c")
        self._status("Жми комбо (напр. ctrl+alt+f9) и отпусти — запишется")

        def on_event(e):
            name = self._normalize_key(e.name) if e.name else ""
            if not name:
                return

            if e.event_type == "down":
                if name == "esc":
                    self.after(0, self._cancel_hotkey_capture)
                    return
                if name not in self.capture_hotkey_pressed:
                    self.capture_hotkey_pressed.append(name)
                self.capture_hotkey_released.discard(name)

            elif e.event_type == "up":
                self.capture_hotkey_released.add(name)
                if self.capture_hotkey_pressed and all(
                    k in self.capture_hotkey_released for k in self.capture_hotkey_pressed
                ):
                    combo = "+".join(self.capture_hotkey_pressed)
                    self.after(0, lambda: self._finish_hotkey_capture(combo))

        self.capture_hotkey_hook = keyboard.hook(on_event)

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

    def _finish_hotkey_capture(self, combo: str):
        try:
            keyboard.unhook(self.capture_hotkey_hook)
        except Exception:
            pass
        self.capture_hotkey_hook = None

        if self.capturing_hotkey is not None:
            self.capturing_hotkey.delete(0, "end")
            self.capturing_hotkey.insert(0, combo)
            self.capturing_hotkey = None

        self._reset_hotkey_buttons()
        self._status(f"Хоткей: {combo}")

    def _cancel_hotkey_capture(self):
        try:
            keyboard.unhook(self.capture_hotkey_hook)
        except Exception:
            pass
        self.capture_hotkey_hook = None
        self.capturing_hotkey = None
        self._reset_hotkey_buttons()
        self._status("Запись хоткея отменена", error=True)

    def _reset_hotkey_buttons(self):
        for tab in (self.tab_click, self.tab_keys):
            for widget in tab.winfo_children():
                if isinstance(widget, ctk.CTkFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkButton) and "Жми комбо" in child.cget("text"):
                            child.configure(text="● Записать", fg_color=("#3B8ED0", "#1F6AA5"))