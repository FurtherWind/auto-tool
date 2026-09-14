# 🤖 Auto Tool

Автоматизатор задач для Windows: автокликер, спам клавишами, пресеты с хоткеями. Проект создан для портфолио.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat)

---

## 📸 Демонстрация

![Auto Tool Screenshot](docs/screenshot.png)

> Интерфейс: 3 вкладки — Кликер, Клавиши, Пресеты.

---

## ⚙️ Стек технологий

- **Python 3.10+**
- **customtkinter** (GUI)
- **pynput** (эмуляция мыши)
- **keyboard** (глобальные хоткеи + эмуляция клавиш)
- **PyInstaller** (сборка в .exe)

---

## ✨ Возможности

- 🖱 **Автокликер** — ЛКМ / ПКМ / СКМ, одиночный / двойной, свой интервал
- ⌨️ **Спам клавишами** — запись любой комбинации (ctrl+c, space, shift+w...)
- 🔥 **Хоткеи из нескольких клавиш** — например `ctrl+alt+f9`, защита от ложных срабатываний
- 💾 **Пресеты** — сохранение настроек + своего хоткея в JSON
- 🎨 **Тёмный GUI** на customtkinter
- 📦 **Сборка в .exe** — один файл, без Python на целевой машине

---

## 📋 Управление

| Клавиша | Действие |
|---------|----------|
| `ctrl+alt+f9` | Запуск пресета (кликер) — по умолчанию |
| `ctrl+alt+f10` | Запуск пресета (клавиши) — по умолчанию |
| `F12` | Стоп всё и выход |
| `Esc` | Отмена записи клавиш / хоткея |

Хоткеи настраиваются на каждой вкладке через кнопку **● Записать** — жмёшь комбо, отпускаешь, готово.

---

## 🚀 Как запустить локально

### Из исходников

```bash
# 1. Клонировать репозиторий
git clone https://github.com/DeliverMyCargo/auto-tool.git

# 2. Перейти в папку проекта
cd auto-tool

# 3. Создать виртуальное окружение
python -m venv venv

# 4. Активировать (Windows)
venv\Scripts\activate

# 5. Установить зависимости
pip install -r requirements.txt

# 6. Запустить
python main.py