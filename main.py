#!/usr/bin/env python3
"""Aldermere Passport Spread.

Draws one invented passport spread (1024x720 PNG) for the fictional
Republic of Aldermere and writes it to /output/entry.png.

Pure Python 3 standard library only: the sandbox has no network and no
third-party packages, so the PNG encoder, the bitmap font and every shape
are implemented here from scratch. Everything is deterministic.

The spread is built to read as a working document:
  * left page  - data page: emblem, portrait, holder data, signature, MRZ
  * right page - visas page: a visitor-permit condition box, a fee stamp,
    and arrival/departure stamps from two neighbouring countries whose
    dates all fall after the passport's issue date (02 JUN 2026) and
    before its expiry (01 JUN 2036).
MRZ check digits (including the composite check digit) are computed,
not typed, so the strip is internally consistent.
"""

import os
import struct
import zlib

W, H = 1024, 720

# ---------------------------------------------------------------- palette
NAVY = (28, 47, 74)
NAVY_SOFT = (58, 82, 112)
INK = (32, 38, 48)
GREY = (110, 112, 116)
PAPER = (245, 240, 225)
PAPER_EDGE = (214, 205, 182)
DESK = (31, 42, 54)
DESK_SOFT = (43, 56, 70)
GOLD = (176, 138, 62)
STAMP_BLUE = (42, 77, 143)
STAMP_PURPLE = (91, 58, 140)
STAMP_RED = (163, 51, 39)
LIGHT_LINE = (232, 224, 200)
TEAL = (127, 168, 160)
SKIN = (232, 185, 143)
SKIN_DARK = (214, 164, 122)
HAIR = (58, 40, 30)
JACKET = (38, 56, 84)
WHITE = (250, 250, 246)

# ------------------------------------------------------------------- font
# 5x7 bitmap font, uppercase only (passports are set in capitals).
# Each glyph: 7 rows of 5 bits, '1' = ink.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x, y, length, c, t=1):
        self.fill_rect(x, y, length, t, c)

    def vline(self, x, y, length, c, t=1):
        self.fill_rect(x, y, t, length, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=False):
        if fill:
            for yy in range(cy - r, cy + r + 1):
                half = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
                self.hline(cx - half, yy, half * 2 + 1, c)
            return
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y),
                           (cx - x, cy - y), (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, c)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1.0 - ((yy - cy) / ry) ** 2
            if t < 0:
                continue
            half = int(rx * t ** 0.5)
            self.hline(cx - half, yy, half * 2 + 1, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for yy in range(max(min(ys), 0), min(max(ys), self.h - 1) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), yy, max(1, int(xs[k + 1]) - int(xs[k])), c)

    def round_rect(self, x, y, w, h, r, c, fill=False):
        if fill:
            self.fill_rect(x + r, y, w - 2 * r, h, c)
            self.fill_rect(x, y + r, w, h - 2 * r, c)
            for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                           (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
                self.circle(cx, cy, r, c, fill=True)
        else:
            self.hline(x + r, y, w - 2 * r, c)
            self.hline(x + r, y + h - 1, w - 2 * r, c)
            self.vline(x, y + r, h - 2 * r, c)
            self.vline(x + w - 1, y + r, h - 2 * r, c)
            for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                           (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
                self.circle(cx, cy, r, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s.upper():
            g = GLYPHS.get(ch, GLYPHS[" "])
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, c)
            cx += 6 * scale

    def text_c(self, cx, y, s, scale, c):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, c)

    def text_r(self, x, y, s, scale, c):
        self.text(x - text_width(s, scale), y, s, scale, c)


# --------------------------------------------------------------- png write
def write_png(path, cv):
    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# --------------------------------------------------------------------- mrz
def mrz_check(s):
    vals = {}
    for i in range(10):
        vals[str(i)] = i
    for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        vals[ch] = 10 + i
    vals["<"] = 0
    total = 0
    for i, ch in enumerate(s):
        total += vals[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def build_mrz():
    doc = "ALD004821"
    line1 = ("P<ALD" + "HALE<<MARA<ELISE").ljust(44, "<")
    dob, sex, exp = "940314", "F", "360601"
    personal = "SELKIE19940314"
    body = (doc + mrz_check(doc) + "ALD" + dob + mrz_check(dob) + sex
            + exp + mrz_check(exp) + personal + mrz_check(personal))
    composite_src = (doc + mrz_check(doc) + dob + mrz_check(dob)
                     + exp + mrz_check(exp) + personal + mrz_check(personal))
    line2 = body + mrz_check(composite_src)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ------------------------------------------------------------------ emblem
def draw_emblem(cv, cx, cy, r):
    """Aldermere arms: a lighthouse over three waves, ringed."""
    cv.circle(cx, cy, r, GOLD)
    cv.circle(cx, cy, r - 3, GOLD)
    # light beams
    cv.line(cx - 4, cy - r + 12, cx - 26, cy - r + 2, GOLD)
    cv.line(cx + 4, cy - r + 12, cx + 26, cy - r + 2, GOLD)
    # tower
    cv.poly([(cx - 6, cy - 6), (cx + 6, cy - 6), (cx + 9, cy + 12),
             (cx - 9, cy + 12)], NAVY)
    cv.fill_rect(cx - 8, cy - 12, 16, 6, NAVY)
    cv.circle(cx, cy - 14, 4, GOLD, fill=True)
    # waves
    for k, wy in enumerate((cy + 16, cy + 21, cy + 26)):
        amp = 5 - k
        prev = None
        for dx in range(-r + 6, r - 5):
            yy = wy + int(amp * 0.5 * ((dx * dx) % 3 - 1))
            if prev is not None:
                cv.line(prev[0], prev[1], cx + dx, yy, NAVY_SOFT)
            prev = (cx + dx, yy)


# ---------------------------------------------------------------- portrait
def draw_portrait(cv, x, y, w, h):
    """Flat-style passport portrait of Mara Hale, 32, of Port Selkie."""
    cv.fill_rect(x, y, w, h, TEAL)
    cv.fill_rect(x, y + h - 46, w, 46, (110, 148, 140))
    # shoulders / jacket
    cv.poly([(x + 8, y + h), (x + 38, y + h - 62), (x + 62, y + h - 52),
             (x + w - 62, y + h - 52), (x + w - 38, y + h - 62),
             (x + w - 8, y + h)], JACKET)
    # shirt V
    cv.poly([(x + w // 2 - 16, y + h - 54), (x + w // 2 + 16, y + h - 54),
             (x + w // 2, y + h - 26)], WHITE)
    # neck
    cv.fill_rect(x + w // 2 - 11, y + h - 78, 22, 30, SKIN_DARK)
    # head
    cx, cy = x + w // 2, y + 78
    cv.ellipse(cx, cy, 34, 42, SKIN)
    # ears
    cv.ellipse(cx - 35, cy + 2, 6, 9, SKIN)
    cv.ellipse(cx + 35, cy + 2, 6, 9, SKIN)
    # hair: back mass, fringe, side sweep (kept above the brow line)
    cv.ellipse(cx, cy - 26, 37, 22, HAIR)
    cv.poly([(cx - 37, cy - 18), (cx - 30, cy - 40), (cx + 30, cy - 40),
             (cx + 37, cy - 18)], HAIR)
    cv.poly([(cx - 34, cy - 2), (cx - 36, cy + 26), (cx - 26, cy + 30),
             (cx - 28, cy - 2)], HAIR)
    cv.poly([(cx + 34, cy - 2), (cx + 36, cy + 26), (cx + 26, cy + 30),
             (cx + 28, cy - 2)], HAIR)
    # brows, eyes, nose, mouth
    cv.fill_rect(cx - 22, cy - 8, 15, 3, HAIR)
    cv.fill_rect(cx + 7, cy - 8, 15, 3, HAIR)
    cv.circle(cx - 14, cy, 4, (40, 28, 22), fill=True)
    cv.circle(cx + 14, cy, 4, (40, 28, 22), fill=True)
    cv.line(cx, cy + 2, cx - 2, cy + 16, SKIN_DARK)
    cv.line(cx - 2, cy + 16, cx + 2, cy + 16, SKIN_DARK)
    cv.fill_rect(cx - 9, cy + 26, 18, 4, (150, 70, 60))
    # photo border
    cv.rect(x, y, w, h, NAVY, 2)


# ------------------------------------------------------------------ stamps
def draw_stamp(cv, x, y, w, h, color, top, mid, bottom, sub=""):
    cv.round_rect(x, y, w, h, 6, color)
    cv.round_rect(x + 3, y + 3, w - 6, h - 6, 4, color)
    cv.text_c(x + w // 2, y + 8, top, 1, color)
    cv.hline(x + 10, y + 20, w - 20, color)
    cv.text_c(x + w // 2, y + 26, mid, 2, color)
    cv.hline(x + 10, y + 46, w - 20, color)
    cv.text_c(x + w // 2, y + 52, bottom, 1, color)
    if sub:
        cv.text_c(x + w // 2, y + h - 14, sub, 1, color)


def draw_date_stamp(cv, cx, cy, r, color, top, date, bottom):
    cv.circle(cx, cy, r, color)
    cv.circle(cx, cy, r - 4, color)
    cv.text_c(cx, cy - r + 12, top, 1, color)
    cv.text_c(cx, cy - 7, date, 1, color)
    cv.text_c(cx, cy + r - 20, bottom, 1, color)


def guilloche(cv, x0, y0, x1, y1, color):
    """Faint wavy security lines across a page."""
    import math
    for k in range(4):
        yy0 = y0 + k * 14
        prev = None
        for xx in range(x0, x1, 4):
            yy = yy0 + int(3 * math.sin((xx - x0) / 26.0 + k))
            if prev is not None:
                cv.line(prev[0], prev[1], xx, yy, color)
            prev = (xx, yy)


# -------------------------------------------------------------- left page
def draw_left(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, PAPER)
    cv.rect(x0, y0, x1 - x0, y1 - y0, PAPER_EDGE, 2)
    guilloche(cv, x0 + 14, y0 + 150, x1 - 14, y0 + 150, LIGHT_LINE)
    guilloche(cv, x0 + 14, y0 + 420, x1 - 14, y0 + 420, LIGHT_LINE)

    cx = (x0 + x1) // 2
    draw_emblem(cv, cx, y0 + 52, 30)
    cv.text_c(cx, y0 + 92, "REPUBLIC OF ALDERMERE", 2, NAVY)
    cv.text_c(cx, y0 + 112, "REPUBLIQUE D'ALDERMERE", 1, GREY)
    cv.hline(x0 + 30, y0 + 132, x1 - x0 - 60, NAVY, 2)
    cv.text_c(cx, y0 + 140, "PASSPORT", 3, NAVY)
    cv.text_c(cx, y0 + 168, "PASSEPORT", 1, GREY)

    # portrait
    px, py, pw, ph = x0 + 28, y0 + 196, 150, 190
    draw_portrait(cv, px, py, pw, ph)
    cv.text_c(px + pw // 2, py + ph + 8, "PHOTOGRAPH", 1, GREY)

    # data fields, right of the portrait
    fx = x0 + 196
    fields = [
        ("TYPE", "P"),
        ("CODE", "ALD"),
        ("PASSPORT NO.", "ALD 004821"),
        ("SURNAME", "HALE"),
        ("GIVEN NAMES", "MARA ELISE"),
        ("NATIONALITY", "ALDERMERIAN"),
        ("DATE OF BIRTH", "14 MAR 1994"),
        ("PLACE OF BIRTH", "PORT SELKIE"),
        ("SEX", "F"),
        ("DATE OF ISSUE", "02 JUN 2026"),
        ("DATE OF EXPIRY", "01 JUN 2036"),
        ("AUTHORITY", "PORT SELKIE"),
    ]
    fy = y0 + 192
    for label, value in fields:
        cv.text(fx, fy, label, 1, GREY)
        cv.text(fx, fy + 10, value, 2, INK)
        fy += 26

    # holder's signature
    import math
    sx, sy = x0 + 28, y0 + 452
    cv.text(sx, sy, "HOLDER'S SIGNATURE", 1, GREY)
    prev = None
    for dx in range(0, 150, 3):
        yy = sy + 26 + int(4 * math.sin(dx / 9.0) + 2 * math.sin(dx / 4.0))
        if prev is not None:
            cv.line(prev[0], prev[1], sx + dx, yy, NAVY)
        prev = (sx + dx, yy)
    cv.hline(sx, sy + 34, 150, NAVY)
    cv.text(sx, sy + 40, "M. HALE", 1, NAVY)

    # MRZ
    line1, line2 = build_mrz()
    my = y1 - 78
    cv.fill_rect(x0 + 14, my - 8, x1 - x0 - 28, 62, (238, 232, 212))
    mx = x0 + (x1 - x0 - text_width(line1, 1)) // 2
    cv.text(mx, my, line1, 1, INK)
    cv.text(mx, my + 26, line2, 1, INK)
    cv.text_c(cx, y1 - 16, "1", 1, GREY)


# ------------------------------------------------------------- right page
def draw_right(cv, x0, y0, x1, y1):
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, PAPER)
    cv.rect(x0, y0, x1 - x0, y1 - y0, PAPER_EDGE, 2)
    guilloche(cv, x0 + 14, y0 + 96, x1 - x0 - 28 + x0, y0 + 96, LIGHT_LINE)
    # faint watermark emblem
    cv.circle((x0 + x1) // 2, y0 + 330, 120, (233, 226, 202))
    cv.circle((x0 + x1) // 2, y0 + 330, 112, (233, 226, 202))

    cx = (x0 + x1) // 2
    cv.text_c(cx, y0 + 22, "VISAS", 3, NAVY)
    cv.text_c(cx, y0 + 50, "VISA - ENDORSEMENTS", 1, GREY)
    cv.hline(x0 + 30, y0 + 68, x1 - x0 - 60, NAVY, 2)

    # visitor-permit condition box: the telling detail
    bx, by, bw = x0 + 28, y0 + 84, x1 - x0 - 56
    cv.rect(bx, by, bw, 108, NAVY, 2)
    cv.fill_rect(bx, by, bw, 22, NAVY)
    cv.text_c(cx, by + 6, "VISITOR'S PERMIT - CONDITIONS OF STAY", 1, WHITE)
    cv.text(bx + 12, by + 32,
            "HOLDER MAY REMAIN 90 DAYS FROM ENTRY.", 1, INK)
    cv.text(bx + 12, by + 48,
            "EMPLOYMENT IN THE LIGHTHOUSE SERVICE", 1, INK)
    cv.text(bx + 12, by + 62,
            "REQUIRES A PERMIT FROM THE HARBOUR", 1, INK)
    cv.text(bx + 12, by + 76,
            "MASTER, PORT SELKIE. NO EXTENSION", 1, INK)
    cv.text(bx + 12, by + 90,
            "AT THE BORDER. - ART. 7, ALD. ACT.", 1, INK)
    # fee stamp overlapping the box corner
    draw_stamp(cv, x1 - 168, by + 60, 140, 68, STAMP_RED,
               "FEE PAID", "12 KR", "PORT SELKIE")

    # travel history: every stamp after issue (02 JUN 2026)
    draw_stamp(cv, x0 + 28, y0 + 216, 200, 78, STAMP_BLUE,
               "ALDERMERE", "DEPARTURE", "02 JUN 2026", "PORT SELKIE")
    draw_stamp(cv, x0 + 244, y0 + 216, 200, 78, STAMP_PURPLE,
               "THALASSA", "ARRIVAL", "18 SEP 2026", "KESTREL PORT")
    draw_stamp(cv, x0 + 28, y0 + 312, 200, 78, STAMP_PURPLE,
               "THALASSA", "DEPARTURE", "02 OCT 2026", "KESTREL PORT")
    draw_stamp(cv, x0 + 244, y0 + 312, 200, 78, STAMP_BLUE,
               "VESTLAND", "ARRIVAL", "11 NOV 2026", "NORDHAVN")
    draw_date_stamp(cv, x0 + 96, y0 + 470, 52, STAMP_BLUE,
                    "PORT SELKIE", "11 NOV 2026", "ALD")
    cv.text(x0 + 172, y0 + 448, "SEEN AT NORDHAVN.", 1, INK)
    cv.text(x0 + 172, y0 + 464, "ONWARD TO PORT", 1, INK)
    cv.text(x0 + 172, y0 + 480, "SELKIE, 12 NOV 2026.", 1, INK)
    cv.text(x0 + 172, y0 + 496, "OFFICER 41.", 1, INK)

    cv.text(x0 + 28, y1 - 40,
            "THIS PASSPORT REMAINS THE PROPERTY OF", 1, GREY)
    cv.text(x0 + 28, y1 - 26,
            "THE REPUBLIC OF ALDERMERE.", 1, GREY)
    cv.text_r(x1 - 28, y1 - 16, "12", 1, GREY)


# -------------------------------------------------------------------- main
def main():
    cv = Canvas(W, H, DESK)
    # desk texture: faint speckles, deterministic
    s = 1234567
    for _ in range(900):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        x, y = s % W, (s // W) % H
        cv.set(x, y, DESK_SOFT)
    # page shadows
    cv.fill_rect(40, 44, 956, 648, (18, 24, 32))
    draw_left(cv, 36, 36, 498, 684)
    draw_right(cv, 526, 36, 988, 684)
    # gutter
    cv.fill_rect(498, 36, 28, 648, (210, 200, 176))
    cv.fill_rect(498, 36, 4, 648, (170, 158, 130))
    cv.fill_rect(522, 36, 4, 648, (170, 158, 130))

    outdir = "/output" if os.path.isdir("/output") else "out"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(path, cv)
    print(f"wrote {path} {W}x{H} {size} bytes")
    assert size <= 1048576, "entry.png exceeds 1 MiB"


if __name__ == "__main__":
    main()
