"""Deterministic renderer for the LUMARIS travel poster.

Draws a single 1024x1024 poster with PIL only: no network, no clock,
no unseeded randomness. Every stochastic element comes from one fixed
seed, so repeated runs produce byte-identical output.
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter

W = 1024
H = 1024
HORIZON = 594  # ~58% of height: sky above, glowing bay below

SEED = 20261121

# Palette (from the build spec).
INDIGO_TOP = (27, 35, 64)
INDIGO_DEEP = (13, 18, 38)
AMBER = (255, 180, 84)
AMBER_DEEP = (255, 140, 66)
CYAN = (55, 224, 200)
CYAN_PALE = (125, 243, 221)
CREAM = (255, 233, 196)
TEAL_DARK = (10, 50, 62)
TEAL_MID = (15, 125, 116)
TEAL_GLOW = (23, 179, 164)
ROCK = (16, 22, 38)
ROCK_EDGE = (38, 50, 78)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _vertical_gradient(img, top_y, bottom_y, top_color, bottom_color):
    draw = ImageDraw.Draw(img)
    span = max(1, bottom_y - top_y)
    for y in range(top_y, bottom_y):
        draw.line([(0, y), (W - 1, y)], fill=_lerp(top_color, bottom_color, (y - top_y) / span))


def _draw_stars(base, rng):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(150):
        x = rng.randint(8, W - 8)
        y = rng.randint(8, 470)
        r = rng.choice([1, 1, 1, 2, 2, 3])
        alpha = rng.randint(70, 210)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(235, 240, 255, alpha))
    base.alpha_composite(layer)


def _draw_sea_glow_streaks(base, rng):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Short curved cyan glints scattered over the bay, denser near the bottom.
    for _ in range(120):
        y = int(HORIZON + 30 + (H - HORIZON - 40) * (rng.random() ** 0.6))
        x = rng.randint(20, W - 20)
        length = rng.randint(14, 70)
        width = rng.randint(1, 3)
        alpha = rng.randint(40, 150)
        draw.arc(
            [x - length // 2, y - 6, x + length // 2, y + 6],
            start=rng.randint(190, 220),
            end=rng.randint(320, 350),
            fill=CYAN_PALE + (alpha,),
            width=width,
        )
    base.alpha_composite(layer)


def _draw_reflection(base, cx, top_y, bottom_y, color, width, rng):
    """A shimmering vertical reflection column under a light source."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Solid tapered column: per-row lines with no gaps, alpha fading down.
    span = max(1, bottom_y - top_y)
    for y in range(top_y, bottom_y):
        t = (y - top_y) / span
        half = int(width * (0.35 + 0.65 * t) * (0.85 + 0.3 * rng.random()))
        alpha = int(150 * (1 - t) + 15)
        draw.line([(cx - half, y), (cx + half, y)], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(4))
    base.alpha_composite(layer)


def _draw_headland_and_lighthouse(base):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Rocky cape occupying the right third, rising from the horizon.
    cape = [
        (660, HORIZON + 6),
        (730, 640),
        (790, 612),
        (860, 648),
        (930, 620),
        (1024, 668),
        (1024, H),
        (640, H),
    ]
    draw.polygon(cape, fill=ROCK + (255,))
    # A faint lit rim along the cape's top edge.
    draw.line(cape[:-2], fill=ROCK_EDGE + (255,), width=3)
    # A few subtler rock facets for shape, hugging the cape's edge.
    draw.polygon([(760, 720), (830, 690), (880, 740), (800, 780)], fill=(22, 30, 50, 255))
    draw.polygon([(920, 730), (990, 710), (1024, 750), (970, 800)], fill=(20, 28, 46, 255))

    # Lighthouse: slim white tower standing on the cape, right of centre.
    tower_x = 838
    tower_top_y = 402
    tower_base_y = 668
    # Tapered tower body.
    draw.polygon(
        [
            (tower_x - 17, tower_top_y),
            (tower_x + 17, tower_top_y),
            (tower_x + 26, tower_base_y),
            (tower_x - 26, tower_base_y),
        ],
        fill=(244, 242, 235, 255),
    )
    # Two dark bands to give the tower its rhythm.
    draw.polygon(
        [(tower_x - 20, 470), (tower_x + 20, 470), (tower_x + 22, 496), (tower_x - 22, 496)],
        fill=(24, 32, 56, 255),
    )
    draw.polygon(
        [(tower_x - 23, 560), (tower_x + 23, 560), (tower_x + 25, 586), (tower_x - 25, 586)],
        fill=(24, 32, 56, 255),
    )
    # Gallery deck and lamp room.
    draw.rectangle([tower_x - 24, 386, tower_x + 24, 402], fill=(24, 32, 56, 255))
    draw.rectangle([tower_x - 13, 358, tower_x + 13, 386], fill=AMBER + (255,))
    draw.rectangle([tower_x - 13, 358, tower_x + 13, 366], fill=(255, 214, 140, 255))
    # Dome cap.
    draw.pieslice([tower_x - 15, 338, tower_x + 15, 366], start=180, end=360, fill=(24, 32, 56, 255))
    draw.rectangle([tower_x - 2, 330, tower_x + 2, 342], fill=(24, 32, 56, 255))

    # Thin beam sweeping down-left across the empty sky below the
    # subtitle, from the lamp room toward the sea.
    beam = [(tower_x - 10, 380), (tower_x - 6, 366), (150, 452), (160, 492)]
    beam_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    beam_draw = ImageDraw.Draw(beam_layer)
    beam_draw.polygon(beam, fill=(255, 220, 150, 70))
    beam_layer = beam_layer.filter(ImageFilter.GaussianBlur(6))
    layer.alpha_composite(beam_layer)

    base.alpha_composite(layer)
    return tower_x


def _draw_boat(base, rng):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, water_y = 258, 812
    # Hull: small dark silhouette with a warm rim.
    draw.polygon(
        [(cx - 52, water_y), (cx + 52, water_y), (cx + 34, water_y + 22), (cx - 34, water_y + 22)],
        fill=(12, 18, 32, 255),
    )
    draw.line([(cx - 52, water_y), (cx + 52, water_y)], fill=AMBER + (220,), width=2)
    # Mast and single triangular sail catching the dusk light.
    draw.line([(cx, water_y), (cx, water_y - 108)], fill=(30, 38, 62, 255), width=4)
    draw.polygon(
        [(cx + 4, water_y - 104), (cx + 4, water_y - 6), (cx + 66, water_y - 6)],
        fill=(255, 236, 205, 255),
    )
    draw.polygon(
        [(cx - 4, water_y - 100), (cx - 4, water_y - 6), (cx - 44, water_y - 6)],
        fill=(232, 214, 180, 255),
    )
    # Amber lantern hanging from the stern, with a soft halo.
    lx, ly = cx - 58, water_y - 16
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.ellipse([lx - 16, ly - 16, lx + 16, ly + 16], fill=AMBER + (90,))
    halo = halo.filter(ImageFilter.GaussianBlur(6))
    layer.alpha_composite(halo)
    draw.ellipse([lx - 6, ly - 6, lx + 6, ly + 6], fill=AMBER + (255,))
    draw.ellipse([lx - 3, ly - 3, lx + 3, ly + 3], fill=(255, 236, 190, 255))
    base.alpha_composite(layer)
    return lx, water_y + 26


def _draw_text(base, font_name, font_sub):
    """Name big in the upper third, one-line subtitle beneath it. No other text."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    name = "LUMARIS"
    tracking = 26
    # Soft shadow first so the cream letters read against the indigo sky.
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)

    def letterspaced_width(font, text, track):
        total = 0
        for ch in text:
            total += draw.textlength(ch, font=font) + track
        return total - track

    name_w = letterspaced_width(font_name, name, tracking)
    # Keep the name inside the canvas with margin; shrink only if ever needed.
    size = 110
    while name_w > W - 80 and size > 60:
        size -= 6
        font_name = font_name.font_variant(size=size) if hasattr(font_name, "font_variant") else font_name
        name_w = letterspaced_width(font_name, name, tracking)
    x = (W - name_w) / 2
    y = 138
    cursor = x
    for ch in name:
        shadow_draw.text((cursor + 3, y + 5), ch, font=font_name, fill=(6, 9, 20, 190))
        cursor += shadow_draw.textlength(ch, font=font_name) + tracking
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    layer.alpha_composite(shadow)

    cursor = x
    for ch in name:
        draw.text((cursor, y), ch, font=font_name, fill=CREAM + (255,))
        cursor += draw.textlength(ch, font=font_name) + tracking

    sub = "THE BAY THAT GLOWS AT NIGHT"
    sub_tracking = 9
    sub_w = letterspaced_width(font_sub, sub, sub_tracking)
    sx = (W - sub_w) / 2
    sy = y + 148
    cursor = sx
    for ch in sub:
        draw.text((cursor + 2, sy + 3), ch, font=font_sub, fill=(6, 9, 20, 170))
        cursor += draw.textlength(ch, font=font_sub) + sub_tracking
    cursor = sx
    for ch in sub:
        draw.text((cursor, sy), ch, font=font_sub, fill=(255, 214, 160, 255))
        cursor += draw.textlength(ch, font=font_sub) + sub_tracking

    base.alpha_composite(layer)


def draw_poster(font_name, font_sub):
    """Render the full poster and return an RGB PIL image (1024x1024)."""
    rng = random.Random(SEED)
    img = Image.new("RGB", (W, H), INDIGO_DEEP)
    base = img.convert("RGBA")

    # Sky: indigo gradient with a warm amber band kissing the horizon.
    _vertical_gradient(base, 0, HORIZON, INDIGO_TOP, INDIGO_DEEP)
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band_draw = ImageDraw.Draw(band)
    for i, yy in enumerate(range(HORIZON - 90, HORIZON)):
        t = i / 90
        band_draw.line([(0, yy), (W - 1, yy)], fill=AMBER + (int(110 * t * t),))
    band = band.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(band)

    _draw_stars(base, rng)

    # Sea: dark teal at the horizon warming to a cyan glow in the foreground.
    _vertical_gradient(base, HORIZON, H, TEAL_DARK, TEAL_GLOW)
    # A thin amber horizon line where sky meets water.
    horizon_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hg_draw = ImageDraw.Draw(horizon_glow)
    hg_draw.line([(0, HORIZON), (W, HORIZON)], fill=AMBER + (160,), width=3)
    horizon_glow = horizon_glow.filter(ImageFilter.GaussianBlur(4))
    base.alpha_composite(horizon_glow)

    _draw_sea_glow_streaks(base, rng)

    _draw_headland_and_lighthouse(base)
    lantern_x, lantern_water_y = _draw_boat(base, rng)

    # Amber reflection under the boat lantern (on open water). No reflection
    # under the lighthouse: it stands on the cape, with rock, not water,
    # below it.
    _draw_reflection(base, lantern_x, lantern_water_y, H - 40, AMBER, 14, rng)

    _draw_text(base, font_name, font_sub)

    return base.convert("RGB")
