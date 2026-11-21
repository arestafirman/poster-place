#!/usr/bin/env python3
"""Entrypoint for the LUMARIS travel poster.

Renders one 1024x1024 poster and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (fallback /output/entry.png).
PNG first; if the PNG exceeds 1 MiB, fall back to JPEG quality 90.
Pure stdlib + PIL, no network, no clock, fully deterministic.
"""

import os

from PIL import ImageFont

from generate_image import W, draw_poster

MAX_BYTES = 1_048_576
NAME_SIZE = 110
SUB_SIZE = 28

# Font fallback chain, tried in order; never crash on a missing path.
NAME_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]
SUB_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def load_font(paths, size):
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default(size=size)


def check_name_fits(font_name):
    """Verify the letterspaced place name fits the canvas width."""
    from PIL import Image, ImageDraw

    probe = Image.new("RGB", (W, 10))
    draw = ImageDraw.Draw(probe)
    tracking = 26
    width = sum(draw.textlength(ch, font=font_name) + tracking for ch in "LUMARIS") - tracking
    assert width <= W - 80, f"name too wide for canvas: {width:.0f}px"
    return width


def main():
    font_name = load_font(NAME_FONTS, NAME_SIZE)
    font_sub = load_font(SUB_FONTS, SUB_SIZE)
    check_name_fits(font_name)

    poster = draw_poster(font_name, font_sub)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")

    poster.save(out_path, format="PNG", optimize=True)
    if os.path.getsize(out_path) > MAX_BYTES:
        # Gradient-heavy PNG can exceed 1 MiB; JPEG q90 stays under it.
        poster.save(out_path, format="JPEG", quality=90, optimize=True)
    size = os.path.getsize(out_path)
    assert size <= MAX_BYTES, f"entry image too large: {size} bytes"
    assert poster.size == (1024, 1024), f"unexpected size: {poster.size}"
    print(f"wrote {out_path} ({size} bytes, {poster.size[0]}x{poster.size[1]})")


if __name__ == "__main__":
    main()
