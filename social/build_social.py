#!/usr/bin/env python3
"""Build the Bin Day social assets from the brand kit.

Two sizes:
  bin-day-square.png   1080x1080  - for posting into a feed
  bin-day-og.png       1200x630   - the link preview, served as og:image

Fonts are the brand's own (Space Grotesk, Atkinson Hyperlegible). Point FONTS
at a directory holding them, or let it download from Google Fonts.
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


def ensure_fonts() -> None:
    FONTS.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        target = FONTS / name
        if not target.exists():
            urllib.request.urlretrieve(url, target)


def display(size: int) -> ImageFont.FreeTypeFont:
    """Space Grotesk is a variable font; pick Bold explicitly."""
    font = ImageFont.truetype(str(FONTS / "SpaceGrotesk.ttf"), size)
    font.set_variation_by_name("Bold")
    return font


def ui(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Atkinson-Bold.ttf" if bold else "Atkinson-Regular.ttf"
    return ImageFont.truetype(str(FONTS / name), size)


def paste_scaled(canvas: Image.Image, path: pathlib.Path, height: int,
                 pos: tuple[int, int]) -> Image.Image:
    art = Image.open(path).convert("RGBA")
    art = art.resize((round(art.width * height / art.height), height), Image.LANCZOS)
    canvas.alpha_composite(art, pos)
    return art


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
         font: ImageFont.FreeTypeFont, pad: tuple[int, int] = (26, 16)) -> int:
    """Ink-outlined lime block, like the site's strapline. Returns its width."""
    x, y = xy
    w = draw.textlength(text, font=font)
    box = (x, y, x + w + pad[0] * 2, y + font.size + pad[1] * 2)
    draw.rounded_rectangle(box, radius=14, fill=LIME, outline=INK, width=4)
    draw.text((x + pad[0], y + pad[1] - font.size * .12), text, font=font, fill=INK)
    return int(box[2] - box[0])


def square() -> Image.Image:
    W = H = 1080
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    m = 78

    paste_scaled(img, ROOT / "static/assets/logo/bin-day-logo-web.png", 92, (m, m - 6))

    # The bin sits bottom-right and crops off the edge, as it does on the site.
    bin_art = Image.open(ROOT / "static/assets/logo/bin-day-mark-clean.png").convert("RGBA")
    bh = 520
    bin_art = bin_art.resize((round(bin_art.width * bh / bin_art.height), bh), Image.LANCZOS)
    img.alpha_composite(bin_art, (W - bin_art.width + 74, H - bh - 40))

    head = display(104)
    y = 300
    for line in ("Your bins.", "Your calendar.", "Sorted."):
        d.text((m, y), line, font=head, fill=INK)
        y += 108

    body = ui(37)
    d.text((m, y + 34), "Free. No account.", font=body, fill=INK)
    d.text((m, y + 84), "Set it up once.", font=body, fill=INK)

    pill(d, (m, H - m - 78), "binday.fly.dev", display(40))
    return img


def og() -> Image.Image:
    W, H = 1200, 630
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    m = 66

    paste_scaled(img, ROOT / "static/assets/logo/bin-day-logo-web.png", 74, (m, m - 4))

    bin_art = Image.open(ROOT / "static/assets/logo/bin-day-mark-clean.png").convert("RGBA")
    bh = 400
    bin_art = bin_art.resize((round(bin_art.width * bh / bin_art.height), bh), Image.LANCZOS)
    img.alpha_composite(bin_art, (W - bin_art.width - 70, H - bh - 46))

    head = display(82)
    d.text((m, 210), "What bin is it", font=head, fill=INK)
    d.text((m, 296), "this week?", font=head, fill=INK)
    d.text((m, 412), "Put your bin collections in your calendar.",
           font=ui(30), fill=GREY)
    pill(d, (m, H - m - 66), "binday.fly.dev", display(32))
    return img


if __name__ == "__main__":
    ensure_fonts()
    HERE.mkdir(exist_ok=True)
    square().convert("RGB").save(HERE / "bin-day-square.png", optimize=True)
    og().convert("RGB").save(ROOT / "static/assets/social/bin-day-og.png", optimize=True)
    print("wrote social/bin-day-square.png and static/assets/social/bin-day-og.png")
