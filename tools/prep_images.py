"""Готовит фото со старого сайта: WebP в двух ширинах + OG-картинку 1200×630.
Запуск: python tools/prep_images.py (из корня проекта)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_old_site" / "gallery_gen"
OUT = ROOT / "src" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# имя файла → (исходник, кадрирование или None)
PHOTOS = {
    "evakuator-legkovoy": ("1f6048ad29ccd61b2c92dce92405fb69_1180x884.jpg", None),
    "evakuaciya-traktorov": ("6e3897a68ac23d05b90c74efaabc4dca_1180x884.jpg", None),
    "evakuaciya-traktora": ("cea39c185c9c451aba2acd981f9304cf_1180x888.jpg", None),
    # коллаж 800×800: сверху ГАЗель на 5 мест, снизу Hyundai HD78 на 5 тонн
    "evakuator-5-mest": ("9828cfe78c01755a9b2f2bf2f8c85d98_800x802.72108843536.jpg", (20, 20, 780, 390)),
    "evakuator-5-tonn": ("9828cfe78c01755a9b2f2bf2f8c85d98_800x802.72108843536.jpg", (20, 410, 780, 780)),
}
WIDTHS = (1180, 640)


def save_webp(img, name):
    sizes = {}
    for w in WIDTHS:
        if img.width < w and w != WIDTHS[-1]:
            w = img.width
        h = round(img.height * w / img.width)
        im = img.resize((w, h), Image.LANCZOS) if w != img.width else img
        path = OUT / f"{name}-{w}.webp"
        im.save(path, "WEBP", quality=80, method=6)
        sizes[w] = (w, h)
    return sizes


manifest = {}
for name, (src, crop) in PHOTOS.items():
    img = Image.open(SRC / src).convert("RGB")
    if crop:
        img = img.crop(crop)
    manifest[name] = save_webp(img, name)

# OG-картинка: фото легкового эвакуатора + тёмная плашка с телефоном
og = Image.open(SRC / PHOTOS["evakuator-legkovoy"][0]).convert("RGB")
scale = 1200 / og.width
og = og.resize((1200, round(og.height * scale)), Image.LANCZOS)
top = (og.height - 630) // 2
og = og.crop((0, top, 1200, top + 630))
draw = ImageDraw.Draw(og, "RGBA")
draw.rectangle((0, 400, 1200, 630), fill=(20, 22, 26, 225))
draw.rectangle((0, 400, 14, 630), fill=(255, 190, 0, 255))
font_b = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 54)
font_r = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34)
draw.text((50, 425), "Эвакуатор-34 · круглосуточно", font=font_b, fill=(255, 255, 255))
draw.text((50, 500), "Волжский и область · до 5 тонн · 5 мест", font=font_r, fill=(220, 220, 220))
draw.text((50, 550), "8 (927) 067-70-70", font=font_b, fill=(255, 190, 0))
og.save(OUT / "og.jpg", "JPEG", quality=85, optimize=True)

# иконки сайта
icon = Image.new("RGB", (512, 512), (255, 190, 0))
d = ImageDraw.Draw(icon)
f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 230)
d.text((256, 270), "34", font=f, fill=(20, 22, 26), anchor="mm")
icon.resize((180, 180), Image.LANCZOS).save(OUT / "apple-touch-icon.png")
icon.resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png")
icon.save(OUT / "icon-512.png")

for k, v in manifest.items():
    print(k, v)
