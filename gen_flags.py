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

# ═══════════════════════════════════════════════════════════════════════════════
# FIFA Country Flags (40×28 px, simplified designs)
# ═══════════════════════════════════════════════════════════════════════════════

def star5(d, cx, cy, r_out, r_in, fill):
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, fill=fill)

def nordic_cross(bg, cross_col, border_col=None):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    cx = W * 2 // 5   # vertical arm ~40% from left
    cw = 3             # half-width of cross bars
    bw = 2             # border width
    if border_col:
        d.rectangle([cx - cw - bw, 0, cx + cw + bw, H - 1], fill=border_col)
        d.rectangle([0, H//2 - cw - bw, W - 1, H//2 + cw + bw], fill=border_col)
    d.rectangle([cx - cw, 0, cx + cw, H - 1], fill=cross_col)
    d.rectangle([0, H//2 - cw, W - 1, H//2 + cw], fill=cross_col)
    return img

def sun_rays(d, cx, cy, r_inner, r_outer, n, fill):
    for i in range(n):
        a = math.radians(i * (360 / n))
        d.line([(cx + r_inner * math.cos(a), cy + r_inner * math.sin(a)),
                (cx + r_outer * math.cos(a), cy + r_outer * math.sin(a))],
               fill=fill, width=1)

# ── CONCACAF ─────────────────────────────────────────────────────────────────

# CAN — Canada: red / white / red vertical + red maple-leaf star
def make_can():
    img = vbands(["#FF0000", "#FFFFFF", "#FF0000"], [0.25, 0.50, 0.25])
    d = ImageDraw.Draw(img)
    star5(d, W // 2, H // 2, 6, 2, "#FF0000")
    return img
save(make_can(), "can")

# MEX — Mexico: green / white / red vertical
save(vbands(["#006847", "#FFFFFF", "#CE1126"]), "mex")

# USA — United States: stripes + blue canton
def make_usa():
    img = Image.new("RGB", (W, H), "#B22234")
    d = ImageDraw.Draw(img)
    stripe_h = H / 13
    for i in range(6):
        y  = round((2 * i + 1) * stripe_h)
        y2 = round((2 * i + 2) * stripe_h)
        d.rectangle([0, y, W - 1, y2], fill="#FFFFFF")
    canton_w = round(W * 0.40)
    canton_h = round(H * 7 / 13)
    d.rectangle([0, 0, canton_w - 1, canton_h - 1], fill="#3C3B6E")
    for row in range(4):
        for col in range(5):
            sx = round(canton_w * (col + 0.5) / 5)
            sy = round(canton_h * (row + 0.5) / 4)
            d.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill="#FFFFFF")
    return img
save(make_usa(), "usa")

# CUW — Curaçao: dark blue + yellow stripe + 2 white stars top-left
def make_cuw():
    img = Image.new("RGB", (W, H), "#002B7F")
    d = ImageDraw.Draw(img)
    y = round(H * 0.60)
    d.rectangle([0, y, W - 1, y + 2], fill="#F9E814")
    star5(d,  7, 8, 4, 2, "#FFFFFF")
    star5(d, 15, 5, 3, 1, "#FFFFFF")
    return img
save(make_cuw(), "cuw")

# HAI — Haiti: blue / red horizontal
save(hbands(["#00209F", "#D21034"]), "hai")

# PAN — Panama: four quadrants (white+blue star | red | blue | white+red star)
def make_pan():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.rectangle([W // 2, 0,      W - 1, H // 2 - 1], fill="#D21034")
    d.rectangle([0,      H // 2, W // 2 - 1, H - 1], fill="#002D62")
    star5(d, W // 4,     H // 4, 4, 2, "#002D62")
    star5(d, W * 3 // 4, H * 3 // 4, 4, 2, "#D21034")
    return img
save(make_pan(), "pan")

# ── ASIA / MIDDLE EAST ───────────────────────────────────────────────────────

# AUS — Australia: dark blue + simplified Union Jack canton + Southern Cross
def make_aus():
    img = Image.new("RGB", (W, H), "#00008B")
    d = ImageDraw.Draw(img)
    uw, uh = W // 2, H // 2
    d.line([(0, 0), (uw, uh)], fill="#FFFFFF", width=2)
    d.line([(uw, 0), (0, uh)], fill="#FFFFFF", width=2)
    d.rectangle([uw // 2 - 1, 0, uw // 2 + 1, uh], fill="#CC0000")
    d.rectangle([0, uh // 2 - 1, uw, uh // 2 + 1], fill="#CC0000")
    for sx, sy in [(W * 3 // 4, H // 2), (W * 3 // 4, H // 4),
                   (W * 3 // 4, H * 3 // 4), (W * 5 // 8, H // 2),
                   (W * 7 // 8, H // 2 - 2)]:
        star5(d, sx, sy, 3, 1, "#FFFFFF")
    return img
save(make_aus(), "aus")

# IRQ — Iraq: black / white / red horizontal
save(hbands(["#000000", "#FFFFFF", "#CE1126"]), "irq")

# IRN — Iran: green / white / red horizontal
save(hbands(["#239F40", "#FFFFFF", "#DA0000"]), "irn")

# JPN — Japan: same design as ja
save(make_ja(), "jpn")

# JOR — Jordan: black / white / green + red left triangle + white star
def make_jor():
    img = hbands(["#000000", "#FFFFFF", "#007A3D"])
    d = ImageDraw.Draw(img)
    tw = W // 3
    d.polygon([(0, 0), (0, H - 1), (tw, H // 2)], fill="#CE1126")
    star5(d, tw // 2, H // 2, 4, 2, "#FFFFFF")
    return img
save(make_jor(), "jor")

# KOR — Korea Republic: same design as ko
save(make_ko(), "kor")

# QAT — Qatar: maroon + white serrated left band
def make_qat():
    img = Image.new("RGB", (W, H), "#8D153A")
    d = ImageDraw.Draw(img)
    bw = W * 3 // 10
    d.rectangle([0, 0, bw, H - 1], fill="#FFFFFF")
    n = 9
    th = H / n
    for i in range(n):
        y1 = round(i * th)
        y2 = round((i + 0.5) * th)
        y3 = round((i + 1) * th)
        d.polygon([(bw, y1), (bw + 5, y2), (bw, y3)], fill="#8D153A")
    return img
save(make_qat(), "qat")

# KSA — Saudi Arabia: green + white crescent + simplified sword
def make_ksa():
    img = Image.new("RGB", (W, H), "#006C35")
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, H // 2 - 4, 5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFFFF")
    d.ellipse([cx - r + 3, cy - r, cx + r + 3, cy + r], fill="#006C35")
    sy = H // 2 + 4
    d.rectangle([W // 4, sy, W * 3 // 4, sy + 2], fill="#FFFFFF")
    d.rectangle([W // 4, sy - 2, W // 4 + 2, sy + 4], fill="#FFFFFF")
    return img
save(make_ksa(), "ksa")

# UZB — Uzbekistan: sky-blue / thin-red / white / thin-red / green
def make_uzb():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    bands = [("#1EBFE5", 10), ("#CE1126", 1), ("#FFFFFF", 6), ("#CE1126", 1), ("#1EB53A", 10)]
    total = sum(b[1] for b in bands)
    y = 0
    for color, weight in bands:
        y2 = round(y + H * weight / total)
        d.rectangle([0, y, W - 1, y2 - 1], fill=color)
        y = y2
    return img
save(make_uzb(), "uzb")

# ── AFRICA ────────────────────────────────────────────────────────────────────

# ALG — Algeria: green / white vertical + red crescent & star
def make_alg():
    img = vbands(["#006233", "#FFFFFF"])
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2 + 2, H // 2, 7
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#D21034")
    d.ellipse([cx - r + 3, cy - r, cx + r + 3, cy + r], fill="#FFFFFF")
    star5(d, cx + 6, cy - 3, 3, 1, "#D21034")
    return img
save(make_alg(), "alg")

# CPV — Cabo Verde: dark blue + horizontal stripe + 10 yellow stars
def make_cpv():
    img = Image.new("RGB", (W, H), "#003893")
    d = ImageDraw.Draw(img)
    sy = round(H * 0.55)
    d.rectangle([0, sy,     W - 1, sy + 2], fill="#FFFFFF")
    d.rectangle([0, sy + 2, W - 1, sy + 4], fill="#CF2027")
    d.rectangle([0, sy + 4, W - 1, sy + 6], fill="#FFFFFF")
    cx, cy, rr = W // 2, H // 2 + 2, 9
    for i in range(10):
        a  = math.radians(i * 36 - 90)
        sx = cx + rr * math.cos(a)
        sy2 = cy + rr * math.sin(a)
        d.ellipse([sx - 1, sy2 - 1, sx + 1, sy2 + 1], fill="#F7D116")
    return img
save(make_cpv(), "cpv")

# COD — Congo DR: sky blue + yellow diagonal stripe + yellow star top-left
def make_cod():
    img = Image.new("RGB", (W, H), "#007FFF")
    d = ImageDraw.Draw(img)
    d.line([(0, H - 1), (W - 1, 0)], fill="#CE1126", width=6)
    d.line([(0, H - 1), (W - 1, 0)], fill="#F7D618", width=3)
    star5(d, 5, 5, 4, 2, "#F7D618")
    return img
save(make_cod(), "cod")

# CIV — Côte d'Ivoire: orange / white / green vertical
save(vbands(["#F77F00", "#FFFFFF", "#009A44"]), "civ")

# EGY — Egypt: red / white / black horizontal
save(hbands(["#CE1126", "#FFFFFF", "#000000"]), "egy")

# GHA — Ghana: red / gold / green + black star
def make_gha():
    img = hbands(["#EF3340", "#FCD116", "#006B3F"])
    d = ImageDraw.Draw(img)
    star5(d, W // 2, H // 2, 5, 2, "#000000")
    return img
save(make_gha(), "gha")

# MAR — Morocco: red + green star
def make_mar():
    img = Image.new("RGB", (W, H), "#C1272D")
    d = ImageDraw.Draw(img)
    star5(d, W // 2, H // 2, 7, 3, "#006233")
    return img
save(make_mar(), "mar")

# SEN — Senegal: green / yellow / red vertical + green star
def make_sen():
    img = vbands(["#00853F", "#FDEF42", "#E31B23"])
    d = ImageDraw.Draw(img)
    star5(d, W // 2, H // 2, 4, 2, "#00853F")
    return img
save(make_sen(), "sen")

# RSA — South Africa: simplified Y-design
def make_rsa():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0,        W - 1, H // 3],     fill="#DE3831")
    d.rectangle([0, H * 2 // 3, W - 1, H - 1],   fill="#002395")
    d.rectangle([0, H // 3,    W - 1, H * 2 // 3], fill="#FFFFFF")
    d.rectangle([0, H // 3 + 2, W - 1, H * 2 // 3 - 2], fill="#007A4D")
    d.polygon([(0, 0), (0, H - 1), (W // 3, H // 2)], fill="#FFB612")
    d.polygon([(0, 3), (0, H - 4), (W // 3 - 4, H // 2)], fill="#000000")
    return img
save(make_rsa(), "rsa")

# TUN — Tunisia: red + white circle + red crescent & star
def make_tun():
    img = Image.new("RGB", (W, H), "#E70013")
    d = ImageDraw.Draw(img)
    r = 8
    cx, cy = W // 2, H // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFFFF")
    r2 = 5
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill="#E70013")
    d.ellipse([cx - r2 + 2, cy - r2, cx + r2 + 2, cy + r2], fill="#FFFFFF")
    star5(d, cx + 5, cy, 3, 1, "#E70013")
    return img
save(make_tun(), "tun")

# ── SOUTH AMERICA ─────────────────────────────────────────────────────────────

# ARG — Argentina: sky-blue / white / sky-blue + sun
def make_arg():
    img = hbands(["#74ACDF", "#FFFFFF", "#74ACDF"])
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, H // 2, 4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#F6B40E")
    sun_rays(d, cx, cy, r + 1, r + 5, 16, "#F6B40E")
    return img
save(make_arg(), "arg")

# BRA — Brazil: green + yellow diamond + blue circle + white arc
def make_bra():
    img = Image.new("RGB", (W, H), "#009C3B")
    d = ImageDraw.Draw(img)
    d.polygon([(W // 2, 3), (W - 4, H // 2), (W // 2, H - 3), (4, H // 2)],
              fill="#FFDF00")
    r = 7
    cx, cy = W // 2, H // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#002776")
    d.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=340,
          fill="#FFFFFF", width=2)
    return img
save(make_bra(), "bra")

# COL — Colombia: yellow (½) / blue (¼) / red (¼)
save(hbands(["#FCD116", "#003087", "#CE1126"], [0.50, 0.25, 0.25]), "col")

# ECU — Ecuador: yellow (½) / blue (¼) / red (¼)
save(hbands(["#FFD100", "#003087", "#EF3340"], [0.50, 0.25, 0.25]), "ecu")

# PAR — Paraguay: red / white / blue horizontal
save(hbands(["#D52B1E", "#FFFFFF", "#002B7F"]), "par")

# URU — Uruguay: white + blue stripes + gold sun top-left
def make_uru():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    for i in range(4):
        y  = round(H * (2 * i + 1) / 9)
        y2 = round(H * (2 * i + 2) / 9)
        d.rectangle([W // 4, y, W - 1, y2], fill="#5EB6E4")
    cx, cy, r = W // 8, H // 4, 4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#F6B40E")
    sun_rays(d, cx, cy, r + 1, r + 4, 16, "#F6B40E")
    return img
save(make_uru(), "uru")

# ── OCEANIA ───────────────────────────────────────────────────────────────────

# NZL — New Zealand: dark blue + small Union Jack canton + 4 red stars
def make_nzl():
    img = Image.new("RGB", (W, H), "#00247D")
    d = ImageDraw.Draw(img)
    uw, uh = W // 3, H // 2
    d.line([(0, 0), (uw, uh)], fill="#FFFFFF", width=2)
    d.line([(uw, 0), (0, uh)], fill="#FFFFFF", width=2)
    d.rectangle([uw // 2 - 1, 0, uw // 2 + 1, uh], fill="#CC0000")
    d.rectangle([0, uh // 2 - 1, uw, uh // 2 + 1], fill="#CC0000")
    for sx, sy in [(W * 2 // 3, H // 4), (W * 5 // 6, H // 2),
                   (W * 3 // 4, H * 3 // 4), (W * 2 // 3 + 2, H // 2)]:
        star5(d, sx, sy, 3, 1, "#CC0000")
    return img
save(make_nzl(), "nzl")

# ── EUROPE ────────────────────────────────────────────────────────────────────

# AUT — Austria: red / white / red horizontal
save(hbands(["#ED2939", "#FFFFFF", "#ED2939"]), "aut")

# BEL — Belgium: black / yellow / red vertical
save(vbands(["#000000", "#F6D800", "#EF3340"]), "bel")

# BIH — Bosnia and Herzegovina: blue + yellow triangle + white stars along diagonal
def make_bih():
    img = Image.new("RGB", (W, H), "#002395")
    d = ImageDraw.Draw(img)
    d.polygon([(W // 3, 0), (W - 1, 0), (W - 1, H - 1)], fill="#FCCA00")
    for i in range(7):
        t  = (i + 0.5) / 7
        sx = W // 3 + t * (W - 1 - W // 3)
        sy = t * (H - 1)
        d.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill="#FFFFFF")
    return img
save(make_bih(), "bih")

# CRO — Croatia: red / white / blue + checkered shield
def make_cro():
    img = hbands(["#FF0000", "#FFFFFF", "#0000CC"])
    d = ImageDraw.Draw(img)
    sq = 2
    ox, oy = W // 2 - 5, H // 2 - 5
    for r in range(5):
        for c in range(5):
            col = "#FF0000" if (r + c) % 2 == 0 else "#FFFFFF"
            d.rectangle([ox + c * sq, oy + r * sq,
                         ox + (c + 1) * sq - 1, oy + (r + 1) * sq - 1], fill=col)
    return img
save(make_cro(), "cro")

# CZE — Czechia: white (top) / red (bottom) + blue left triangle
def make_cze():
    img = hbands(["#FFFFFF", "#D7141A"])
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (0, H - 1), (W // 2, H // 2)], fill="#11457E")
    return img
save(make_cze(), "cze")

# ENG — England: white + red St George's cross
def make_eng():
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)
    cw = 4
    d.rectangle([W // 2 - cw // 2, 0, W // 2 + cw // 2, H - 1], fill="#CF142B")
    d.rectangle([0, H // 2 - cw // 2, W - 1, H // 2 + cw // 2], fill="#CF142B")
    return img
save(make_eng(), "eng")

# FRA — France: same design as fr
save(vbands(["#002395", "#FFFFFF", "#ED2939"]), "fra")

# GER — Germany: same design as de
save(hbands(["#000000", "#DD0000", "#FFCE00"]), "ger")

# NED — Netherlands: red / white / blue horizontal
save(hbands(["#AE1C28", "#FFFFFF", "#21468B"]), "ned")

# NOR — Norway: red + white-bordered blue Nordic cross
save(nordic_cross("#EF2B2D", "#003680", "#FFFFFF"), "nor")

# POR — Portugal: same design as pt
save(vbands(["#006600", "#FF0000"], [0.40, 0.60]), "por")

# SCO — Scotland: blue + white diagonal cross (St Andrew's)
def make_sco():
    img = Image.new("RGB", (W, H), "#003399")
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (W - 1, H - 1)], fill="#FFFFFF", width=4)
    d.line([(W - 1, 0), (0, H - 1)], fill="#FFFFFF", width=4)
    return img
save(make_sco(), "sco")

# ESP — Spain: same design as es
save(hbands(["#AA151B", "#F1BF00", "#AA151B"], [0.25, 0.50, 0.25]), "esp")

# SWE — Sweden: blue + yellow Nordic cross
save(nordic_cross("#006AA7", "#FECC02"), "swe")

# SUI — Switzerland: red + white cross
def make_sui():
    img = Image.new("RGB", (W, H), "#FF0000")
    d = ImageDraw.Draw(img)
    cw, cl = 4, 12
    cx, cy = W // 2, H // 2
    d.rectangle([cx - cw // 2, cy - cl // 2, cx + cw // 2, cy + cl // 2], fill="#FFFFFF")
    d.rectangle([cx - cl // 2, cy - cw // 2, cx + cl // 2, cy + cw // 2], fill="#FFFFFF")
    return img
save(make_sui(), "sui")

# TUR — Türkiye: red + white crescent & star
def make_tur():
    img = Image.new("RGB", (W, H), "#E30A17")
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2 - 3, H // 2, 7
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFFFF")
    d.ellipse([cx - r + 3, cy - r, cx + r + 3, cy + r], fill="#E30A17")
    star5(d, cx + 10, cy, 4, 2, "#FFFFFF")
    return img
save(make_tur(), "tur")

print("Flags generated:")
for f in sorted(os.listdir(OUT)):
    if f.endswith(".png"):
        print(f"  {OUT}/{f}")
