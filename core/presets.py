import json
import os
import sys


def _base_dir() -> str:
    """Папка рядом с exe (или с корнем проекта при запуске из python)."""
    if getattr(sys, "frozen", False):
        # запущено как PyInstaller exe
        return os.path.dirname(sys.executable)
    # запущено из python
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PRESETS_DIR = os.path.join(_base_dir(), "presets")


def ensure_dir():
    os.makedirs(PRESETS_DIR, exist_ok=True)


def list_presets() -> list[str]:
    ensure_dir()
    return [f[:-5] for f in os.listdir(PRESETS_DIR) if f.endswith(".json")]


def save_preset(name: str, config: dict):
    ensure_dir()
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_preset(name: str) -> dict:
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_preset(name: str):
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)