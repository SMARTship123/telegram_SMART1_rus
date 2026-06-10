#!/usr/bin/env python3
"""Брендированные графические карточки vibrotors.ru (1280x720 PNG).

Графики-диаграммы для постов Telegram. Каждый --kind рисует свою диаграмму,
чтобы канал не выглядел одним повторяющимся шаблоном:

  spectrum  спектр вибрации (столбцы), ключевые пики выделены янтарным
  trend     значение, растущее сквозь зоны тяжести ИСО A/B/C/D со временем
  timeline  стадийное развитие дефекта с выделенным «окном экономии»
  delta     баланс «с наблюдением / без» с итоговой цифрой риска
  gauge     полукруглый индикатор тяжести/оценки со стрелкой

Импортируемо: render(kind, out, title=..., **kw). Есть и небольшой CLI.
Чистый Pillow (без matplotlib). Требует: pip install pillow
"""
import argparse
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (11, 18, 32)
PANEL = (20, 30, 50)
ACCENT = (45, 156, 219)
AMBER = (240, 176, 64)
WHITE = (235, 240, 247)
MUTED = (150, 165, 185)
GREEN = (74, 198, 138)
RED = (224, 92, 92)
# ISO-zone palette, A(healthy) -> D(damage)
ZONE = [(74, 168, 120), (150, 190, 96), (240, 176, 64), (224, 92, 92)]
ZONE_LABEL = ["A", "B", "C", "D"]
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


def chrome(d, brand, subtitle, title):
    """Top accent bar, brand, subtitle, wrapped title + amber rule.
    Returns y just below the title block (top of the plot area)."""
    d.rectangle([0, 0, W, 8], fill=ACCENT)
    d.text((64, 40), brand, font=font(FB, 28), fill=ACCENT)
    d.text((64, 80), subtitle, font=font(FR, 23), fill=MUTED)
    tf = font(FB, 60)
    y = 140
    for line in wrap(d, title, tf, W - 128):
        d.text((64, y), line, font=tf, fill=WHITE)
        y += 68
    d.rectangle([64, y + 8, 300, y + 14], fill=AMBER)
    return y + 44


def footer(d, text, handle):
    d.rectangle([0, H - 64, W, H], fill=(8, 13, 24))
    d.text((64, H - 47), text, font=font(FR, 25), fill=WHITE)
    hw = d.textlength(handle, font=font(FR, 21))
    d.text((W - hw - 64, H - 45), handle, font=font(FR, 21), fill=MUTED)


# ---- kinds ---------------------------------------------------------------

def k_spectrum(d, area, *, bars, highlight, xlabel="частота  (× оборотная)"):
    """bars: list of (label, height 0..1). highlight: set of indices drawn amber."""
    x0, y0, x1, y1 = area
    base = y1 - 28
    d.line([(x0, base), (x1, base)], fill=MUTED, width=2)
    n = len(bars)
    slot = (x1 - x0) / n
    bw = slot * 0.5
    hi = set(highlight or [])
    for i, (lab, h) in enumerate(bars):
        cx = x0 + slot * (i + 0.5)
        bh = max(3, h * (base - y0 - 10))
        col = AMBER if i in hi else ACCENT
        d.rectangle([cx - bw / 2, base - bh, cx + bw / 2, base], fill=col)
        d.text((cx, base + 6), lab, font=font(FR, 19), fill=(WHITE if i in hi else MUTED), anchor="ma")
    d.text((x1, y0 - 2), xlabel, font=font(FR, 18), fill=MUTED, anchor="ra")


def k_trend(d, area, *, points, mark=None, ylabel="общий уровень вибрации"):
    """points: list of y in 0..1 (low=healthy). 4 zone bands behind."""
    x0, y0, x1, y1 = area
    bands = 4
    bh = (y1 - y0) / bands
    for i in range(bands):  # top band = D (worst)
        zi = bands - 1 - i
        top = y0 + i * bh
        c = tuple(int(v * 0.32 + BG[j] * 0.68) for j, v in enumerate(ZONE[zi]))
        d.rectangle([x0, top, x1, top + bh], fill=c)
        d.text((x1 - 10, top + bh / 2), "Зона " + ZONE_LABEL[zi],
               font=font(FB, 20), fill=ZONE[zi], anchor="rm")
    pts = [(x0 + (x1 - x0) * i / (len(points) - 1), y1 - (y1 - y0) * v)
           for i, v in enumerate(points)]
    d.line(pts, fill=WHITE, width=4, joint="curve")
    for p in pts:
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=WHITE)
    if mark is not None:
        mx = x0 + (x1 - x0) * mark / (len(points) - 1)
        d.line([(mx, y0), (mx, y1)], fill=AMBER, width=3)
        d.text((mx, y0 - 6), "плановое вмешательство", font=font(FB, 19), fill=AMBER, anchor="mb")
    d.text((x0, y1 + 8), "время  →  квартальные замеры", font=font(FR, 18), fill=MUTED)


def k_timeline(d, area, *, stages, money):
    """stages: list of (label, sub). money: (start_idx,end_idx) window to highlight."""
    x0, y0, x1, y1 = area
    n = len(stages)
    seg = (x1 - x0) / n
    ty = y0 + 70
    th = 64
    pal = [ZONE[0], ZONE[1], ZONE[2], ZONE[3]]
    for i, (lab, sub) in enumerate(stages):
        sx = x0 + i * seg
        c = pal[min(i, 3)]
        d.rectangle([sx + 4, ty, sx + seg - 4, ty + th], fill=c)
        d.text((sx + seg / 2, ty + th / 2), lab, font=font(FB, 24), fill=(10, 16, 28), anchor="mm")
        d.text((sx + seg / 2, ty + th + 12), sub, font=font(FR, 19), fill=MUTED, anchor="ma")
    if money:
        a, b = money
        mx0 = x0 + a * seg + 4
        mx1 = x0 + (b + 1) * seg - 4
        by = ty - 30
        d.line([(mx0, by), (mx1, by)], fill=AMBER, width=4)
        d.line([(mx0, by), (mx0, ty)], fill=AMBER, width=4)
        d.line([(mx1, by), (mx1, ty)], fill=AMBER, width=4)
        d.text(((mx0 + mx1) / 2, by - 8), "окно экономии", font=font(FB, 22), fill=AMBER, anchor="mb")


def k_delta(d, area, *, without_val, without_lab, with_val, with_lab, net_val, net_lab):
    x0, y0, x1, y1 = area
    gap = 28
    cw = (x1 - x0 - gap) / 2
    # left (without) red, right (with) green
    for (bx, col, val, lab, tag) in [
        (x0, RED, without_val, without_lab, "БЕЗ НАБЛЮДЕНИЯ"),
        (x0 + cw + gap, GREEN, with_val, with_lab, "С НАБЛЮДЕНИЕМ"),
    ]:
        d.rectangle([bx, y0, bx + cw, y1 - 70], fill=PANEL)
        d.rectangle([bx, y0, bx + 8, y1 - 70], fill=col)
        d.text((bx + 28, y0 + 18), tag, font=font(FB, 20), fill=col)
        d.text((bx + 28, y0 + 56), val, font=font(FB, 62), fill=WHITE)
        d.text((bx + 28, y0 + 130), lab, font=font(FR, 22), fill=MUTED)
    # net bar
    ny = y1 - 52
    d.text((x0, ny), net_lab, font=font(FR, 24), fill=MUTED)
    nw = d.textlength(net_val, font=font(FB, 52))
    d.text((x1 - nw, ny - 14), net_val, font=font(FB, 52), fill=AMBER)


def k_gauge(d, area, *, value, label, ticks=("low", "high"), good_high=False):
    """value 0..1 along a 180° arc; colored A->D segments.
    good_high=True flips the palette (red left, green right) for 'higher is better'."""
    x0, y0, x1, y1 = area
    cx = (x0 + x1) / 2
    cy = y1 - 30
    r = min((x1 - x0) / 2 - 20, (y1 - y0) - 40)
    segs = 4
    pal = list(reversed(ZONE)) if good_high else ZONE
    for i in range(segs):
        a0 = 180 + i * (180 / segs)
        a1 = 180 + (i + 1) * (180 / segs)
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=pal[i], width=46)
    ang = math.radians(180 + value * 180)
    nx = cx + (r - 30) * math.cos(ang)
    ny = cy + (r - 30) * math.sin(ang)
    d.line([(cx, cy), (nx, ny)], fill=WHITE, width=8)
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=WHITE)
    d.text((cx - r, cy + 14), ticks[0], font=font(FR, 20), fill=MUTED, anchor="ma")
    d.text((cx + r, cy + 14), ticks[1], font=font(FR, 20), fill=MUTED, anchor="ma")
    d.text((cx, cy - r - 8), label, font=font(FB, 26), fill=AMBER, anchor="mb")


KINDS = {
    "spectrum": k_spectrum,
    "trend": k_trend,
    "timeline": k_timeline,
    "delta": k_delta,
    "gauge": k_gauge,
}


def render(kind, out, *, title, subtitle="Бриф по надёжности флота",
           brand="ВИБРОДИАГНОСТИКА СУДОВ", footer_text="vibrotors.ru",
           handle="vibrotors.ru", **kw):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    top = chrome(d, brand, subtitle, title)
    area = (64, top + 10, W - 64, H - 96)
    KINDS[kind](d, area, **kw)
    footer(d, footer_text, handle)
    img.save(out, "PNG")
    print(f"saved {out} [{kind}]")
    return out


def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=list(KINDS))
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="Fleet Reliability Brief")
    ap.add_argument("--footer", default="vibrotors.ru")
    ap.add_argument("--out", required=True)
    a, extra = ap.parse_known_args()
    print("CLI renders need params via the Python API; see module docstring.")


if __name__ == "__main__":
    _cli()
