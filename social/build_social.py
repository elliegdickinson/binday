#!/usr/bin/env python3
"""Build the Bin Day social assets from the brand kit.

  bin-day-square.png    1080x1080  main feed
  bin-day-portrait.png  1080x1350  portrait feed
  bin-day-story.png     1080x1920  stories / reels
  bin-day-og.png        1200x630   link preview (served as og:image)

One dominant message per graphic: a problem-led headline, one explanatory
line, one real collection result, a CTA, and the bin cropping off the corner.
Fonts are the brand's own; they download on first run.
"""
from __future__ import annotations

import os
import pathlib
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = pathlib.Path(os.environ.get("FONTS", HERE / "fonts"))

GOOGLE = "https://github.com/google/fonts/raw/main/ofl"
SOURCES = {
    "SpaceGrotesk.ttf":     f"{GOOGLE}/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "Atkinson-Regular.ttf": f"{GOOGLE}/atkinsonhyperlegible/AtkinsonHyperlegible-Regular.ttf",
    "Atkinson-Bold.ttf":    f"{GOOGLE}/atkinsonhyperlegible/AtkinsonHyperlegible-Bold.ttf",
}

CREAM = (247, 244, 234)
INK   = (22, 22, 22)
LIME  = (200, 255, 56)
GREY  = (107, 107, 107)
WHITE = (255, 255, 255)
BLUE  = (69, 108, 255)      # recycling


def ensure_fonts() -> None:
    FONTS.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        if not (FONTS / name).exists():
            urllib.request.urlretrieve(url, FONTS / name)


def display(size: int) -> ImageFont.FreeTypeFont:
    """Space Grotesk is a variable font, and Bold (700) is its heaviest cut -
    there is no 800 to select."""
    font = ImageFont.truetype(str(FONTS / "SpaceGrotesk.ttf"), size)
    font.set_variation_by_name("Bold")
    return font


def ui(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        str(FONTS / ("Atkinson-Bold.ttf" if bold else "Atkinson-Regular.ttf")), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
         width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def rays(d: ImageDraw.ImageDraw, x: int, y: int, scale: float,
         colour=INK) -> None:
    """The three marks from the logo, as a small recurring device."""
    w = max(3, round(2.6 * scale))
    for x1, y1, x2, y2 in ((4, 13, 1.5, 17), (9.5, 8.5, 8, 3.5), (14.5, 10, 18.5, 7)):
        d.line((x + x1 * scale, y + y1 * scale, x + x2 * scale, y + y2 * scale),
               fill=colour, width=w)


def recycling_mark(d: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Three arrowheads in a ring - the same icon the site uses. Each triangle
    is built pointing up, pushed out from the centre, then rotated, so they
    sit in a ring instead of piling up on the middle."""
    import math
    cx, cy = x + size / 2, y + size / 2
    # The triangles must clear the centre or they merge into one blob: the
    # nearest edge sits at (offset - half_h) from the middle.
    half_w, half_h = size * 0.19, size * 0.15
    offset = size * 0.30
    for turn in (0, 120, 240):
        a = math.radians(turn)
        pts = []
        for px, py in ((0, -half_h), (half_w, half_h), (-half_w, half_h)):
            py -= offset
            pts.append((cx + px * math.cos(a) - py * math.sin(a),
                        cy + px * math.sin(a) + py * math.cos(a)))
        d.polygon(pts, fill=BLUE, outline=INK, width=max(2, size // 18))


def result_card(img: Image.Image, d: ImageDraw.ImageDraw, x: int, y: int,
                s: float) -> tuple[int, int]:
    """One real collection result. Relative timing is the largest thing on it.
    The card sizes itself to its content - TOMORROW is eight characters and
    overflowed a fixed width."""
    pad = round(34 * s)
    icon = round(62 * s)
    f_label = ui(round(24 * s), bold=True)
    f_when  = display(round(68 * s))
    f_date  = ui(round(27 * s))

    when_w = d.textlength("TOMORROW", font=f_when)
    ray_w = round(34 * s)
    w = round(max(when_w + ray_w + round(18 * s),
                  d.textlength("Thursday 24 September", font=f_date)) + pad * 2)
    h = pad * 2 + icon + round(20 * s) + round(34 * s) + round(78 * s) + round(38 * s)

    d.rounded_rectangle((x, y, x + w, y + h), radius=round(22 * s),
                        fill=WHITE, outline=INK, width=max(2, round(3 * s)))
    recycling_mark(d, x + pad, y + pad, icon)
    ty = y + pad + icon + round(20 * s)
    d.text((x + pad, ty), "RECYCLING", font=f_label, fill=GREY)
    ty += round(34 * s)
    d.text((x + pad, ty), "TOMORROW", font=f_when, fill=BLUE)
    rays(d, round(x + pad + when_w + 14 * s), round(ty + 14 * s), s * 1.4)
    ty += round(78 * s)
    d.text((x + pad, ty), "Thursday 24 September", font=f_date, fill=INK)
    return w, h


def pill(d: ImageDraw.ImageDraw, x: int, y: int, text: str,
         font: ImageFont.FreeTypeFont, s: float) -> tuple[int, int]:
    px, py = round(30 * s), round(18 * s)
    w = d.textlength(text, font=font)
    box = (x, y, x + w + px * 2, y + font.size + py * 2)
    d.rounded_rectangle(box, radius=round(14 * s), fill=LIME, outline=INK,
                        width=max(2, round(3.5 * s)))
    d.text((x + px, y + py - font.size * .12), text, font=font, fill=INK)
    return int(box[2] - box[0]), int(box[3] - box[1])


def compose(W: int, H: int, s: float, head_size: int, bin_h: int,
            top_pad: int = 0) -> Image.Image:
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    m = round(84 * s)                       # keeps text clear of platform crops

    # Bin first so everything sits over it. It runs off the right edge but the
    # wheel stays on the canvas - cropped, not beheaded.
    art = Image.open(ROOT / "static/assets/logo/bin-day-mark-clean.png").convert("RGBA")
    art = art.resize((round(art.width * bin_h / art.height), bin_h), Image.LANCZOS)
    img.alpha_composite(art, (W - art.width + round(art.width * .22),
                              H - bin_h - round(28 * s)))

    logo = Image.open(ROOT / "static/assets/logo/bin-day-logo-web.png").convert("RGBA")
    lh = round(74 * s)
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    img.alpha_composite(logo, (m, m - round(6 * s)))

    y = m + lh + round(66 * s) + top_pad
    head = display(head_size)
    for line in ("NEVER MISS", "BIN DAY AGAIN."):
        d.text((m, y), line, font=head, fill=INK)
        y += round(head_size * 1.02)

    y += round(30 * s)
    body = ui(round(32 * s))
    for line in wrap(d, "Find your collection dates and add them straight to "
                        "your phone calendar.", body, round(W * .58)):
        d.text((m, y), line, font=body, fill=INK)
        y += round(44 * s)

    y += round(50 * s)
    _, card_h = result_card(img, d, m, y, s)
    y += card_h + round(56 * s)              # never let the CTA touch the card

    cta_w, cta_h = pill(d, m, y, "TRY BIN DAY  \u2192", display(round(42 * s)), s)
    y += cta_h + round(16 * s)
    d.text((m + round(4 * s), y), "binday.fly.dev",
           font=ui(round(27 * s), bold=True), fill=INK)

    # Brand sign-off, deliberately quiet - it is not the acquisition headline.
    d.text((m + round(4 * s), y + round(46 * s)),
           "Your bins. Your calendar. Sorted.", font=ui(round(23 * s)), fill=GREY)
    return img


def og() -> Image.Image:
    W, H, s = 1200, 630, .78
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    m = 66

    art = Image.open(ROOT / "static/assets/logo/bin-day-mark-clean.png").convert("RGBA")
    bh = 430
    art = art.resize((round(art.width * bh / art.height), bh), Image.LANCZOS)
    img.alpha_composite(art, (W - art.width - 54, H - bh + 40))

    logo = Image.open(ROOT / "static/assets/logo/bin-day-logo-web.png").convert("RGBA")
    logo = logo.resize((round(logo.width * 62 / logo.height), 62), Image.LANCZOS)
    img.alpha_composite(logo, (m, m - 4))

    head = display(76)
    d.text((m, 196), "NEVER MISS", font=head, fill=INK)
    d.text((m, 274), "BIN DAY AGAIN.", font=head, fill=INK)
    d.text((m, 386), "Find your collection dates and add them", font=ui(28), fill=INK)
    d.text((m, 424), "straight to your phone calendar.", font=ui(28), fill=INK)
    pill(d, m, H - m - 76, "TRY BIN DAY  →", display(32), s)
    return img


if __name__ == "__main__":
    ensure_fonts()
    out = {
        "bin-day-square.png":   compose(1080, 1080, 0.86, 92,  430),
        "bin-day-portrait.png": compose(1080, 1350, 1.00, 104, 600, top_pad=96),
        "bin-day-story.png":    compose(1080, 1920, 1.12, 118, 900, top_pad=210),
    }
    for name, image in out.items():
        image.convert("RGB").save(HERE / name, optimize=True)
    (ROOT / "static/assets/social").mkdir(parents=True, exist_ok=True)
    og().convert("RGB").save(ROOT / "static/assets/social/bin-day-og.png", optimize=True)
    print("wrote", ", ".join(out), "and the og card")
