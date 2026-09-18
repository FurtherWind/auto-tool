import json
import os
import sys
import copy


def _base_dir() -> str:
    """Папка рядом с exe (или с корнем проекта при запуске из python)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SETTINGS_PATH = os.path.join(_base_dir(), "settings.json")

# ---------- настройки по умолчанию ----------
DEFAULTS = {
    "theme": "dark",                 # dark | light | system
    "start_minimized": False,        # запускать свёрнутым в трей
    "check_updates": True,           # проверять обновления при запуске
    "hotkeys": {
        "click":     "ctrl+alt+f9",
        "keys":      "ctrl+alt+f10",
        "points":    "ctrl+alt+f11",
        "pause":     "ctrl+alt+p",
        "stop_all":  "ctrl+alt+s",
        "exit":      "f12",
    },
}


_cache = None


def _deep_merge(base: dict, override: dict) -> dict:
    """Мержит override в base, не теряя вложенные ключи."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load() -> dict:
    """Загрузить настройки с диска. Если файла нет — создать с дефолтами."""
    global _cache
    if _cache is not None:
        return _cache

    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            _cache = _deep_merge(DEFAULTS, user)
        except Exception as e:
            print("settings load error:", e)
            _cache = copy.deepcopy(DEFAULTS)
    else:
        _cache = copy.deepcopy(DEFAULTS)
        save(_cache)
    return _cache


def save(settings: dict = None):
    """Сохранить настройки. Без аргумента — сохраняет текущий кэш."""
    global _cache
    if settings is not None:
        _cache = settings
    if _cache is None:
        return
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("settings save error:", e)


def get(key: str, default=None):
    """Получить значение по ключу. Поддерживает вложенность: 'hotkeys.click'."""
    s = load()
    parts = key.split(".")
    cur = s
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def set_value(key: str, value):
    """Установить значение по ключу с сохранением на диск."""
    s = load()
    parts = key.split(".")
    cur = s
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    save(s)


def reset():
    """Сбросить всё к дефолтам."""
    global _cache
    _cache = copy.deepcopy(DEFAULTS)
    save(_cache)