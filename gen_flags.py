"""
gen_flags.py — Generate 40x28 px flag PNGs for every site language.
Run once from the repo root:  python gen_flags.py
Output: static/img/flags/<code>.png
"""
from PIL import Image, ImageDraw
import math, os

OUT = "static/img/flags"
os.makedirs(OUT, exist_ok=True)

W, H = 40, 28   # 40×28 px (2× for retina; displayed at 20×14 in CSS)


def save(img: Image.Image, code: str):
    img.save(f"{OUT}/{code}.png")


def hbands(colors, widths=None):
    """Horizontal bands. widths is relative list summing to 1."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    n = len(colors)
    if widths is None:
        widths = [1 / n] * n
    y = 0
    for c, w in zip(colors, widths):
        y2 = round(y + H * w)
        d.rectangle([0, y, W - 1, y2 - 1], fill=c)
        y = y2
    return img


def vbands(colors, widths=None):
    """Vertical bands."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    n = len(colors)
    if widths is None:
        widths = [1 / n] * n
    x = 0
    for c, w in zip(colors, widths):
        x2 = round(x + W * w)
        d.rectangle([x, 0, x2 - 1, H - 1], fill=c)
        x = x2
    return img


# ── de  Germany: black / red / gold ────────────────────────────────────────
save(hbands(["#000000", "#DD0000", "#FFCE00"]), "de")

# ── fr  France: blue / white / red  ────────────────────────────────────────
save(vbands(["#002395", "#FFFFFF", "#ED2939"]), "fr")

# ── es  Spain: red / yellow / red (2:1:2) ──────────────────────────────────
save(hbands(["#AA151B", "#F1BF00", "#AA151B"], [0.25, 0.50, 0.25]), "es")

# ── pt  Portugal: green / red (2:3) ────────────────────────────────────────
save(vbands(["#006600", "#FF0000"], [0.40, 0.60]), "pt")

# ── it  Italy: green / white / red ─────────────────────────────────────────
save(vbands(["#009246", "#FFFFFF", "#CE2B37"]), "it")

# ── pl  Poland: white / red ─────────────────────────────────────────────────
save(hbands(["#FFFFFF", "#DC143C"]), "pl")

# ── ru  Russia: white / blue / red ─────────────────────────────────────────
save(hbands(["#FFFFFF", "#0039A6", "#D52B1E"]), "ru")

# ── uk  Ukraine: blue / yellow ─────────────────────────────────────────────
save(hbands(["#005BBB", "#FFD500"]), "uk")

# ── zh  China: red, large yellow star + 4 small stars ──────────────────────
def make_zh():
    img = Image.new("RGB", (W, H), "#DE2910")
    d = ImageDraw.Draw(img)
    # Large star (5-pointed) centred at (8, 7)
    def star(cx, cy, r_out, r_in, fill):
        pts = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = r_out if i % 2 == 0 else r_in
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        d.polygon(pts, fill=fill)
    star(8, 7, 4.5, 2.0, "#FFDE00")
    for cx, cy in [(16, 3), (19, 6), (19, 10), (16, 13)]:
        star(cx, cy, 1.8, 0.8, "#FFDE00")
    return img
save(make_zh(), "zh")

# ── zh-hant  Taiwan: red, blue canton with white sun ──────────────────────
def make_zh_hant():
    img = Image.new("RGB", (W, H), "#FE0000")
    d = ImageDraw.Draw(img)
    # Blue canton top-left
    d.rectangle([0, 0, W // 2 - 1, H // 2 - 1], fill="#000095")
    # White sun circle
    cx, cy, r = W // 4, H // 4, 4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFFFF")
    # 12-ray sun (simplified: white octagram)
    for i in range(12):
        angle = math.radians(i * 30)
        x1 = cx + (r - 1) * math.cos(angle)
        y1 = cy + (r - 1) * math.sin(angle)
        x2 = cx + (r + 3) * math.cos(angle)
        y2 = cy + (r + 3) * math.sin(angle)
        d.line([(x1, y1), (x2, y2)], fill="#FFFFFF", width=1)
    return img
save(make_zh_hant(), "zh-hant")

# ── ja  Japan: white, red circle ────────────────────────────────────────────
def make_ja():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    r = 7
    d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], fill="#BC002D")
    return img
save(make_ja(), "ja")

# ── ko  South Korea: white, red/blue taeguk, black trigrams ─────────────────
def make_ko():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, H // 2, 6
    # Red top half
    d.pieslice([cx - r, cy - r, cx + r, cy + r], start=-180, end=0, fill="#CD2E3A")
    # Blue bottom half
    d.pieslice([cx - r, cy - r, cx + r, cy + r], start=0, end=180, fill="#003478")
    # Small circles to make yin-yang
    d.ellipse([cx - r // 2 - r // 4, cy - r // 4, cx - r // 2 + r // 4, cy + r - r // 4], fill="#003478")
    d.ellipse([cx + r // 2 - r // 4, cy - r + r // 4, cx + r // 2 + r // 4, cy + r // 4], fill="#CD2E3A")
    # Outer border
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#000000", width=1)
    # Simplified trigrams (3 short lines each side)
    def trigram(x, y, angle_deg, gaps):
        a = math.radians(angle_deg)
        for i, gap in enumerate(gaps):
            oy = (i - 1) * 3
            if gap:
                # broken line (two halves)
                for dx in [-3, 1]:
                    x1 = x + dx * math.cos(a) - oy * math.sin(a)
                    y1 = y + dx * math.sin(a) + oy * math.cos(a)
                    x2 = x + (dx + 2) * math.cos(a) - oy * math.sin(a)
                    y2 = y + (dx + 2) * math.sin(a) + oy * math.cos(a)
                    d.line([(x1, y1), (x2, y2)], fill="#000000", width=1)
            else:
                x1 = x - 4 * math.cos(a) - oy * math.sin(a)
                y1 = y - 4 * math.sin(a) + oy * math.cos(a)
                x2 = x + 4 * math.cos(a) - oy * math.sin(a)
                y2 = y + 4 * math.sin(a) + oy * math.cos(a)
                d.line([(x1, y1), (x2, y2)], fill="#000000", width=1)
    # 4 trigrams at corners (simplified to solid lines for clarity at 40px)
    for angle, ox, oy in [(135, cx - 12, cy - 9), (45, cx + 12, cy - 9),
                          (225, cx - 12, cy + 9), (315, cx + 12, cy + 9)]:
        for i in range(3):
            offset = (i - 1) * 2.5
            a = math.radians(angle)
            x1 = ox + (-3) * math.cos(a) - offset * math.sin(a)
            y1 = oy + (-3) * math.sin(a) + offset * math.cos(a)
            x2 = ox + 3 * math.cos(a) - offset * math.sin(a)
            y2 = oy + 3 * math.sin(a) + offset * math.cos(a)
            d.line([(x1, y1), (x2, y2)], fill="#000000", width=1)
    return img
save(make_ko(), "ko")

# ── th  Thailand: red/white/blue/white/red (1:1:2:1:1) ──────────────────────
save(hbands(["#A51931", "#F4F5F8", "#2D2A4A", "#F4F5F8", "#A51931"],
            [1/6, 1/6, 2/6, 1/6, 1/6]), "th")

# ── tl  Philippines: blue/red + white triangle + yellow sun ─────────────────
def make_tl():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    # Blue top half
    d.rectangle([0, 0, W - 1, H // 2 - 1], fill="#0038A8")
    # Red bottom half
    d.rectangle([0, H // 2, W - 1, H - 1], fill="#CE1126")
    # White equilateral triangle on the left
    tw = int(H * 0.866)  # height for equilateral based on width H
    d.polygon([(0, 0), (0, H - 1), (tw, H // 2)], fill="#FFFFFF")
    # Yellow sun in triangle
    cx, cy = tw // 2, H // 2
    r_sun = 4
    d.ellipse([cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun], fill="#FCD116")
    # 8 rays
    for i in range(8):
        angle = math.radians(i * 45)
        x1 = cx + (r_sun + 1) * math.cos(angle)
        y1 = cy + (r_sun + 1) * math.sin(angle)
        x2 = cx + (r_sun + 3) * math.cos(angle)
        y2 = cy + (r_sun + 3) * math.sin(angle)
        d.line([(x1, y1), (x2, y2)], fill="#FCD116", width=1)
    return img
save(make_tl(), "tl")

# ── en  USA: red/white stripes + blue canton + white stars ──────────────────
def make_en():
    img = Image.new("RGB", (W, H), "#B22234")
    d = ImageDraw.Draw(img)
    # 7 white stripes (13 stripes total, 6 white alternating)
    stripe_h = H / 13
    for i in range(6):
        y = round((2 * i + 1) * stripe_h)
        y2 = round((2 * i + 2) * stripe_h)
        d.rectangle([0, y, W - 1, y2], fill="#FFFFFF")
    # Blue canton (covering top 7 stripes wide as rows, ~7/13 H × ~40% W)
    canton_w = round(W * 0.40)
    canton_h = round(H * 7 / 13)
    d.rectangle([0, 0, canton_w - 1, canton_h - 1], fill="#3C3B6E")
    # Stars — 5 columns × 4 rows of simplified dots
    cols, rows = 5, 4
    for row in range(rows):
        for col in range(cols):
            sx = round(canton_w * (col + 0.5) / cols)
            sy = round(canton_h * (row + 0.5) / rows)
            r = 1
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill="#FFFFFF")
    return img
save(make_en(), "en")

# ── pgl  Pig Latin / Pirate: black jolly roger ──────────────────────────────
def make_pgl():
    img = Image.new("RGB", (W, H), "#000000")
    d = ImageDraw.Draw(img)
    # Skull circle
    cx, cy = W // 2, H // 2 - 2
    r = 5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFFFF")
    # Eye sockets
    d.ellipse([cx - 3, cy - 2, cx - 1, cy], fill="#000000")
    d.ellipse([cx + 1, cy - 2, cx + 3, cy], fill="#000000")
    # Teeth
    for i in range(3):
        tx = cx - 3 + i * 3
        d.rectangle([tx, cy + 2, tx + 2, cy + 4], fill="#FFFFFF")
    # Crossbones (two diagonal lines)
    d.line([(cx - 8, H - 3), (cx + 8, H - 9)], fill="#FFFFFF", width=2)
    d.line([(cx + 8, H - 3), (cx - 8, H - 9)], fill="#FFFFFF", width=2)
    return img
save(make_pgl(), "pgl")

# ── eo  Esperanto: green, white star ────────────────────────────────────────
def make_eo():
    img = Image.new("RGB", (W, H), "#009A44")
    d = ImageDraw.Draw(img)
    # White square canton top-left
    cs = H // 2
    d.rectangle([0, 0, cs - 1, cs - 1], fill="#FFFFFF")
    # Green 5-pointed star on white
    cx, cy = cs // 2, cs // 2
    r_out, r_in = cs // 2 - 1, cs // 4
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, fill="#009A44")
    return img
save(make_eo(), "eo")

print("Flags generated:")
for f in sorted(os.listdir(OUT)):
    if f.endswith(".png"):
        print(f"  {OUT}/{f}")
