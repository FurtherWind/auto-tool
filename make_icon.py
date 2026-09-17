from PIL import Image
import os

src = "icon.png"
if not os.path.exists(src):
    print(f"❌ Файл {src} не найден")
    exit(1)

img = Image.open(src).convert("RGBA")
w, h = img.size
print(f"Исходный размер: {w}x{h}")

# Оставляем центральные 70% (обрезаем внешний фон вокруг скруглённого квадрата)
# Если иконка занимает больше/меньше — поменяй 0.7 на 0.75 или 0.65
crop_ratio = 0.72
side = int(min(w, h) * crop_ratio)
left = (w - side) // 2
top = (h - side) // 2
img = img.crop((left, top, left + side, top + side))
print(f"Обрезано до: {side}x{side}")

# Базовый размер 256x256
img_256 = img.resize((256, 256), Image.LANCZOS)

# Множественные размеры в .ico
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img_256.save("icon.ico", format="ICO", sizes=sizes)

# Также сохраняем PNG-версии для README/релиза
img.resize((512, 512), Image.LANCZOS).save("icon_512.png", "PNG")
img.resize((128, 128), Image.LANCZOS).save("icon_128.png", "PNG")

print(f"✅ icon.ico ({os.path.getsize('icon.ico')} байт)")
print(f"✅ icon_512.png (для README)")
print(f"✅ icon_128.png")