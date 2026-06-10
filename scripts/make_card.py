#!/usr/bin/env python3
"""Генерация брендированной инфо-карточки vibrotors.ru (1280x720 PNG).

Использование:
    python3 scripts/make_card.py \
        --title "Вибромониторинг судовых механизмов" \
        --subtitle "Бриф по надёжности флота" \
        --stat "6 нед=раннее обнаружение дефекта" \
        --stat "СНО=без разборки исправного" \
        --stat "15+ лет=опыт лаборатории" \
        --footer "Предиктивная диагностика, а не ремонт по поломке." \
        --out images/sample-vcm.png

Требует Pillow:  pip install pillow
Каждый --stat — это "БОЛЬШОЕ=мелкое" (до 3). Затем закоммить PNG и опубликуй
его воркфлоу «Post Photo to Telegram».
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (11, 18, 32)
ACCENT = (45, 156, 219)
AMBER = (240, 176, 64)
WHITE = (235, 240, 247)
MUTED = (150, 165, 185)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="Бриф по надёжности флота")
    ap.add_argument("--brand", default="ВИБРОДИАГНОСТИКА СУДОВ")
    ap.add_argument("--stat", action="append", default=[], help='"BIG=small", up to 3')
    ap.add_argument("--footer", default="Предиктивная диагностика, а не ремонт по поломке.")
    ap.add_argument("--handle", default="vibrotors.ru")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=ACCENT)
    d.text((64, 54), a.brand, font=font(FB, 30), fill=ACCENT)
    d.text((64, 96), a.subtitle, font=font(FR, 24), fill=MUTED)

    title_f = font(FB, 76)
    y = 180
    for line in wrap(d, a.title, title_f, W - 200):
        d.text((64, y), line, font=title_f, fill=WHITE)
        y += 82
    d.rectangle([64, y + 16, 360, y + 22], fill=AMBER)

    sy = y + 64
    for i, s in enumerate(a.stat[:3]):
        big, _, small = s.partition("=")
        x = 64 + i * 348
        d.text((x, sy), big, font=font(FB, 64), fill=AMBER)
        d.text((x, sy + 80), small, font=font(FR, 24), fill=MUTED)

    d.rectangle([0, H - 70, W, H], fill=(8, 13, 24))
    d.text((64, H - 52), a.footer, font=font(FR, 26), fill=WHITE)
    hw = d.textlength(a.handle, font=font(FR, 22))
    d.text((W - hw - 64, H - 50), a.handle, font=font(FR, 22), fill=MUTED)

    img.save(a.out, "PNG")
    print(f"saved {a.out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
