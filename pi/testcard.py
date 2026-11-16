"""
Test card for measuring what the panel's six inks really look like.

The palette RGBs in processor.PALETTES are match targets for the ditherer, not
the colours the glass shows (blue ink, targeted at a light sky blue, prints as
dark navy). To dither against the REAL inks we first have to measure them: show
this card, photograph it in daylight with the white mat in shot, read each ink
off the photo.

Layout (landscape, as the viewer sees it):
  row 1 — six solid ink squares, large enough to sample cleanly
  row 2 — each ink as a 50/50 checkerboard with white (how a dithered mix reads)
  row 3 — black/white steps at 0..100% black (how the panel builds greys)

Every pixel is snapped to an exact palette target with no dithering, so the
firmware's rgbToPanel6() maps each one to the intended ink.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from processor import Processor

INKS = ["black", "white", "blue", "yellow", "red", "green"]
_IDX = {name: i for i, name in enumerate(INKS)}


def build_test_card(color_profile: str = "jaffa") -> Image.Image:
    """Return the test card already oriented and flipped for the panel (BMP-ready)."""
    p = Processor()
    display = p.config.display
    panel_w = display.get("width", 1200)
    panel_h = display.get("height", 1600)
    rotation = int(display.get("rotation", 0)) % 360
    w, h = (panel_h, panel_w) if rotation in (90, 270) else (panel_w, panel_h)

    pal = p._palette_for(display.get("color_mode", "6color"), color_profile)
    black, white = pal[_IDX["black"]], pal[_IDX["white"]]

    img = Image.new("RGB", (w, h), white)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # no anti-aliasing: grey text edges would snap to other inks
    try:
        font = ImageFont.truetype(str(Path(__file__).parent / "fonts" / "Jost-Medium.ttf"), 34)
    except OSError:
        font = ImageFont.load_default()

    # The frame's mat hides roughly the outer 60-80 px (it hides the camera's
    # date line at the top), so everything sits well inside that.
    margin, gap = 110, 24
    cell = (w - 2 * margin - 5 * gap) // 6

    def label(x, y, text):
        d.text((x + cell // 2, y), text, font=font, fill=black, anchor="mt")

    # Row 1: solid inks. White gets a thin black keyline so its edge is visible.
    y1 = 120
    for i, name in enumerate(INKS):
        x = margin + i * (cell + gap)
        d.rectangle([x, y1, x + cell - 1, y1 + cell - 1], fill=pal[i])
        if name == "white":
            d.rectangle([x, y1, x + cell - 1, y1 + cell - 1], outline=black, width=3)

        label(x, y1 + cell + 10, name)

    # Row 2: each ink 50/50 with white, as a 1-pixel checkerboard.
    y2 = y1 + cell + 70
    ch = 200
    for i, name in enumerate(INKS):
        x = margin + i * (cell + gap)
        tile = Image.new("RGB", (cell, ch), white)
        px = tile.load()
        for yy in range(ch):
            for xx in range((yy % 2), cell, 2):
                px[xx, yy] = pal[i]
        img.paste(tile, (x, y2))
        if name == "white":  # white on white: outline it so the box is findable
            d.rectangle([x, y2, x + cell - 1, y2 + ch - 1], outline=black, width=3)
        label(x, y2 + ch + 10, f"{name} 50%")

    # Row 3: black dot coverage 0..100% in 10 steps (ordered 4x4 Bayer pattern,
    # so each step is an even texture, not noise).
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    y3 = y2 + ch + 70
    steps = 11
    sw = (w - 2 * margin) // steps
    sh = h - y3 - 150
    for s in range(steps):
        cover = s / (steps - 1)
        tile = Image.new("RGB", (sw, sh), white)
        px = tile.load()
        for yy in range(sh):
            for xx in range(sw):
                if bayer[yy % 4][xx % 4] < cover * 16:
                    px[xx, yy] = black
        x = margin + s * sw
        img.paste(tile, (x, y3))
        if s == 0:
            d.rectangle([x, y3, x + sw - 1, y3 + sh - 1], outline=black, width=3)
        d.text((x + sw // 2, y3 + sh + 10), f"{int(cover * 100)}%", font=font,
               fill=black, anchor="mt")

    # Snap anti-aliased text edges to exact palette targets (no dithering).
    img = p._nearest_color(img, pal)
    return p._orient_for_panel(img, rotation, panel_w, panel_h)
