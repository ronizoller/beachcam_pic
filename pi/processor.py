"""
Processor module - converts images for E-Ink display.

Pipeline: resize → overlay → PIL dithering (6-color)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from config import get_config

logger = logging.getLogger(__name__)

# E-Ink color palettes - balanced for beach scenes
PALETTES = {
    # 7-color palette: black, white, blue, sky, sand, red, gray
    "7color": [
        (0, 0, 0),          # Black
        (255, 255, 255),    # White
        (0, 100, 200),      # Ocean blue (true blue, no purple)
        (100, 160, 210),    # Sky blue (cooler)
        (200, 180, 150),    # Sand tan
        (170, 120, 100),    # Muted terracotta
        (130, 130, 130),    # Gray
    ],
    # 6-color E-Ink (Spectra 6): calibrated to what the panel actually displays
    # rather than RGB primaries. PIL's quantize() picks the nearest palette
    # entry by RGB distance, so using pure primaries makes most natural pixels
    # snap to white/black (e.g. a sky-blue pixel is closer to white than to
    # (0,0,255)). Calibrated values keep the chromatic colors in play and the
    # output looks much more saturated. Tweak to taste — these are a starting
    # estimate based on typical Spectra 6 measurements.
    # IMPORTANT: these numbers are *match targets* for the nearest-colour
    # quantizer, NOT what the panel displays — firmware rgbToPanel6() reclassifies
    # them into 6 fixed inks. So moving an anchor TOWARD the midtones GROWS its
    # share of the image, and moving it AWAY shrinks it. Panel brightness is
    # therefore governed by how much area lands on white/yellow ink, not by
    # gamma or the brightness multiplier.
    "6color": [
        (15, 15, 15),       # Black. Anchor pushed DOWN (was 40) to shrink black's
                            # territory: the neutral black/white boundary moves
                            # 135 -> 113, so mid-grays (shadows, dim sky, hazy
                            # sea) become white ink instead of black. The old
                            # comment here claimed raising the anchor reduced
                            # black coverage — it does the opposite. Raising it
                            # shifts the equidistant plane UP, putting MORE
                            # pixels on the black side. Keep < 50 so firmware
                            # still classifies this as BLACK.
        (215, 212, 205),    # White (paper-like, slightly warm). Anchor pulled
                            # DOWN (was 235) so white claims more midtones.
                            # Keep the channel mean > 200 and the channels within
                            # 30 of each other or firmware drops out of its clean
                            # WHITE branch.
        (40, 70, 150),      # Blue (muted default, not saturated primary —
                            # most cameras override this via PROFILE_OVERRIDES)
        (225, 185, 55),     # Yellow (mustard, not bright cyan-yellow)
        (175, 45, 40),      # Red — darkened and saturated (was 215,75,60). The
                            # lighter value sat close to pale warm neutrals, so
                            # hazy sky and tan sand quantized to red: measured
                            # 16% of a beach frame as red ink, nearly all of it
                            # dither speckle rather than real content. Red ink is
                            # dark on Spectra 6, so that alone dimmed the panel.
                            # Keep r > 150 and r > g+50, r > b+50 for firmware RED.
        (30, 115, 50),      # Green (forest). Also darkened/saturated to stop sea
                            # pixels landing on green. Keep the channel mean > 50
                            # or firmware reclassifies it as BLACK.
    ],
    # 5-color palette (simpler)
    "5color": [
        (0, 0, 0),          # Black
        (255, 255, 255),    # White
        (40, 100, 180),     # Ocean blue
        (190, 170, 145),    # Sand tan
        (128, 128, 128),    # Gray
    ],
    # 3-color E-Ink (Black, White, Red)
    "3color": [
        (0, 0, 0),          # Black
        (255, 255, 255),    # White
        (200, 50, 50),      # Red
    ],
    # Black and white
    "bw": [
        (0, 0, 0),          # Black
        (255, 255, 255),    # White
    ],
}

# Index of each color name within the 6color palette, for profile overrides.
_COLOR_IDX = {"black": 0, "white": 1, "blue": 2, "yellow": 3, "red": 4, "green": 5}

# Per-camera-profile palette tweaks. Keyed by the camera's `scoring_profile`
# in config.yaml. Each entry overrides one or more palette colors only for
# that profile — other cameras still use the default 6color palette above.
# Use this to shift quantization boundaries for a specific scene's color
# distribution (more sky/sea pixels into blue, less into green, etc.).
PROFILE_OVERRIDES = {
    "jaffa": {
        # Cyan-leaning mid-blue: bright enough that sea/sky don't render
        # as a dim navy stripe, but saturated enough that those pixels
        # actually claim blue during quantization instead of collapsing
        # to white. (Previous very-light value of 130,185,220 pulled too
        # many pixels into white, washing out natural sea/sky colors.)
        "blue":  (75, 140, 195),
        # Darkened to shrink green's territory — sea pixels were landing on green
        # ink (measured 5.9% of the frame), which reads dark on the panel.
        "green": (30, 110, 40),
    },
    "beach": {
        # Same rationale for guest beach scenes — sea/sky should read as
        # blue ink, not white.
        "blue": (75, 140, 195),
    },
}


class Processor:
    """Processes images for E-Ink display with smooth, print-like output."""

    def __init__(self):
        self.config = get_config()

    def process(
        self,
        image: Image.Image,
        weather_data: dict = None,
        color_profile: str = None,
    ) -> Image.Image:
        """
        Process image for E-Ink display.

        Pipeline:
        1. Resize to working canvas (landscape if rotation is 90/270, else portrait)
        2. Add overlay (before dithering for transparency effect)
        3. Color reduction with PIL dithering
        4. Rotate to match panel mount + vertical flip to compensate for the
           firmware's bottom-up BMP read order.

        Args:
            image: Input PIL Image.
            weather_data: Optional dict with weather info for overlay.

        Returns:
            Processed PIL Image ready for E-Ink.
        """
        display = self.config.display
        overlay_config = self.config.overlay

        panel_w = display.get("width", 800)
        panel_h = display.get("height", 480)
        rotation = int(display.get("rotation", 0)) % 360
        color_mode = display.get("color_mode", "7color")
        dithering = display.get("dithering", True)
        saturation = float(display.get("saturation", 1.0))
        contrast = float(display.get("contrast", 1.0))
        brightness = float(display.get("brightness", 1.0))
        gamma = float(display.get("gamma", 1.0))
        warm_r = float(display.get("warm_gain_r", 1.0))
        warm_b = float(display.get("warm_gain_b", 1.0))

        # If the panel is mounted rotated 90° (CW or CCW), render against a
        # landscape canvas so the overlay text and aspect ratio look right
        # from the viewer's perspective; the rotation step below will fit
        # this canvas back into the panel's native portrait pixel grid.
        if rotation in (90, 270):
            canvas_w, canvas_h = panel_h, panel_w
        else:
            canvas_w, canvas_h = panel_w, panel_h

        img = self._resize(image, canvas_w, canvas_h)
        logger.debug(f"Resized to {canvas_w}x{canvas_h} (rotation={rotation})")

        # Saturation/contrast boost — applied to the photo BEFORE the overlay
        # so the neutral-gray pills aren't pushed off-color. With only 6
        # palette entries, muted source pixels tend to snap toward white/black
        # rather than the chromatic colors; bumping saturation pulls them
        # toward red/yellow/blue/green and makes the panel use its full gamut.
        if saturation != 1.0:
            img = ImageEnhance.Color(img).enhance(saturation)
            logger.debug(f"Saturation x{saturation}")
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
            logger.debug(f"Contrast x{contrast}")
        # Gamma BEFORE the linear brightness multiplier. A linear multiplier
        # clips bright pixels to white (e.g. mid-morning sand at input ~220
        # becomes 255 under a 1.4x lift, losing all texture). Gamma lifts
        # midtones strongly while compressing highlights, so the same sand
        # ends up ~232 — brighter than the source but still rendering with
        # detail when quantized to the 6-color palette.
        if gamma != 1.0:
            inv_g = 1.0 / gamma
            lut = [int(round(255 * (i / 255.0) ** inv_g)) for i in range(256)]
            img = img.point(lut * 3)
            logger.debug(f"Gamma {gamma}")
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
            logger.debug(f"Brightness x{brightness}")
        # Warm channel gains — the "reddish filter". Applied last among the photo
        # adjustments and BEFORE the overlay, so the neutral-gray pills stay
        # neutral. Per-channel LUTs, same mechanism as the gamma step above.
        #
        # Measured effect on a real sunset frame at 1.10/0.94: brighter (bright
        # ink 45.2% -> 51.9%) but LESS colourful overall (63.4% -> 59.2%),
        # because it converts blue sea into white and red — blue drops 31% ->
        # 20%. Set both back to 1.0 to disable.
        if warm_r != 1.0 or warm_b != 1.0:
            r_lut = [min(255, int(round(i * warm_r))) for i in range(256)]
            g_lut = list(range(256))
            b_lut = [min(255, int(round(i * warm_b))) for i in range(256)]
            img = img.point(r_lut + g_lut + b_lut)
            logger.debug(f"Warm gain R x{warm_r} B x{warm_b}")

        if overlay_config.get("enabled", True) and weather_data:
            img = self._add_pill_overlay(img, weather_data, overlay_config)
            logger.debug("Added overlay")

        import time as _time
        t0 = _time.time()
        img = self._reduce_colors(img, color_mode, dithering, color_profile)
        dt = _time.time() - t0
        logger.info(f"Dithering: {color_mode} palette, profile={color_profile or 'default'}, time={dt:.2f}s")

        img = self._orient_for_panel(img, rotation, panel_w, panel_h)
        return img

    def _orient_for_panel(
        self, img: Image.Image, rotation: int, panel_w: int, panel_h: int,
    ) -> Image.Image:
        """
        Rotate the rendered image to match the panel's physical mount, then
        flip vertically so PIL's bottom-up BMP storage decodes upright on the
        firmware side. The firmware reads rows in storage order (file row 0 =
        visual bottom of saved image) and sends them top-to-bottom on the
        panel, so flipping here cancels that out.
        """
        if rotation == 90:
            img = img.transpose(Image.ROTATE_270)   # 90° CW
        elif rotation == 180:
            img = img.transpose(Image.ROTATE_180)
        elif rotation == 270:
            img = img.transpose(Image.ROTATE_90)    # 90° CCW

        if img.size != (panel_w, panel_h):
            raise ValueError(
                f"Oriented image is {img.size}, expected {(panel_w, panel_h)} "
                f"for rotation={rotation}"
            )

        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return img

    def _resize(self, image: Image.Image, width: int, height: int) -> Image.Image:
        """Resize image to target dimensions, maintaining aspect ratio with crop."""
        img = image.convert("RGB")

        # Calculate aspect ratios
        target_ratio = width / height
        current_ratio = img.width / img.height

        if current_ratio > target_ratio:
            # Image is wider - crop sides
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image is taller - crop top/bottom
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        # Resize to exact dimensions using high-quality resampling
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        return img

    def _reduce_colors(
        self, image: Image.Image, color_mode: str, dithering: bool,
        color_profile: str = None,
    ) -> Image.Image:
        """Reduce image colors to E-Ink palette using PIL's built-in dithering."""
        palette = self._palette_for(color_mode, color_profile)

        if dithering:
            pal_img = Image.new('P', (1, 1))
            flat_pal = [c for rgb in palette for c in rgb] + [0] * (768 - len(palette) * 3)
            pal_img.putpalette(flat_pal)
            quantized = image.quantize(colors=len(palette), palette=pal_img, dither=1)
            return quantized.convert('RGB')
        else:
            return self._nearest_color(image, palette)

    def _palette_for(
        self, color_mode: str, color_profile: str = None,
    ) -> List[Tuple[int, int, int]]:
        """Return the palette for `color_mode`, with per-profile overrides applied."""
        base = list(PALETTES.get(color_mode, PALETTES["5color"]))
        overrides = PROFILE_OVERRIDES.get(color_profile or "", {})
        for name, rgb in overrides.items():
            idx = _COLOR_IDX.get(name)
            if idx is not None and idx < len(base):
                base[idx] = rgb
        return base

    def _nearest_color(
        self, image: Image.Image, palette: List[Tuple[int, int, int]]
    ) -> Image.Image:
        """Nearest-color mapping without dithering (posterized look)."""
        pal_img = Image.new('P', (1, 1))
        flat_pal = [c for rgb in palette for c in rgb] + [0] * (768 - len(palette) * 3)
        pal_img.putpalette(flat_pal)
        quantized = image.quantize(colors=len(palette), palette=pal_img, dither=0)
        return quantized.convert('RGB')

    def _add_pill_overlay(
        self,
        image: Image.Image,
        weather_data: dict,
        config: dict,
    ) -> Image.Image:
        """
        Add semi-transparent pill overlay with surf data.

        Layout: Two stacked rounded pills, bottom-right.
        Top pill: colored rating dot + wave data + wind speed + wind arrow
        Bottom pill: location · time
        Drawn BEFORE dithering so gray background gets dithered = transparency effect.
        """
        import math
        img = image.copy()
        draw = ImageDraw.Draw(img)

        # Load Jost font (free Futura alternative)
        font_dir = Path(__file__).parent / "fonts"
        try:
            font_md = ImageFont.truetype(str(font_dir / "Jost-Medium.ttf"), 22)
            font_sm = ImageFont.truetype(str(font_dir / "Jost-Regular.ttf"), 16)
        except Exception:
            try:
                font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
                font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except Exception:
                font_md = ImageFont.load_default()
                font_sm = ImageFont.load_default()

        width, height = img.size
        bg_color = (80, 80, 80)  # 70% opacity gray (gets dithered)
        text_color = (255, 255, 255)
        padding = 25

        # --- Build text content ---
        wave = weather_data.get("wave_height")
        period = weather_data.get("wave_period")
        if wave and period:
            wave_text = f"{wave}@{period}"
        elif wave:
            wave_text = wave
        else:
            wave_text = ""

        wind_speed = weather_data.get("wind_speed", "")
        wind_dir = weather_data.get("wind_direction", "")

        location = weather_data.get("location", "")
        israel_time = datetime.now().strftime("%H:%M")

        # If guest cam has a timezone, show local time + Israel time
        guest_tz = weather_data.get("timezone")
        if guest_tz:
            try:
                import pytz
                local_now = datetime.now(pytz.timezone(guest_tz))
                time_str = f"{local_now.strftime('%H:%M')} ({israel_time} IL)"
            except Exception:
                time_str = israel_time
        else:
            time_str = israel_time

        rating = weather_data.get("rating")
        if rating is not None:
            if rating <= 3:
                r_color = (200, 80, 80)     # Soft red/coral
            elif rating <= 6:
                r_color = (200, 190, 80)    # Soft gold
            else:
                r_color = (80, 180, 100)    # Soft green

        # --- Top pill: rating + wave + wind + arrow ---
        top_parts = []
        if wave_text:
            top_parts.append(wave_text)
        if wind_speed:
            top_parts.append(f"{wind_speed}")
        top_text = "  ".join(top_parts)

        top_bbox = draw.textbbox((0, 0), top_text, font=font_md)
        top_text_w = top_bbox[2] - top_bbox[0]
        top_text_h = top_bbox[3] - top_bbox[1]

        gap = 12  # Consistent spacing between elements
        dot_space = (8 + 36 + gap) if rating is not None else 0  # margin + circle + gap
        arrow_space = (gap + 26) if wind_dir else 0  # gap + arrow size
        pill_w = dot_space + top_text_w + arrow_space + 10
        pill_h = 42
        pill_r = pill_h // 2

        px = width - pill_w - padding
        py = height - pill_h * 2 - padding - 8

        draw.rounded_rectangle([px, py, px + pill_w, py + pill_h], radius=pill_r, fill=bg_color)

        # Rating dot
        if rating is not None:
            dot_r = 18
            dot_cx = px + 8 + dot_r
            dot_cy = py + pill_h // 2
            draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=r_color)
            r_text = str(rating)
            rb = draw.textbbox((0, 0), r_text, font=font_md)
            rw = rb[2] - rb[0]
            rh = rb[3] - rb[1]
            # Center text in circle using anchor if available, otherwise manual offset
            tx = dot_cx - rw // 2 - rb[0]
            ty = dot_cy - rh // 2 - rb[1]
            draw.text((tx, ty), r_text, fill=(0, 0, 0), font=font_md)

        # Wave + wind text
        draw.text((px + dot_space, py + 8), top_text, fill=text_color, font=font_md)

        # Wind arrow — positioned right after the text
        if wind_dir:
            arrow_x = px + dot_space + top_text_w + gap + 12
            arrow_y = py + pill_h // 2
            angle_map = {
                "N": 180, "NE": 225, "E": 270, "SE": 315,
                "S": 0, "SW": 45, "W": 90, "NW": 135,
            }
            angle = math.radians(angle_map.get(wind_dir, 0))
            # Clock-hand style: fixed center, rotates to show direction
            # Line from center
            line_len = 10
            x1 = arrow_x - line_len * math.sin(angle)
            y1 = arrow_y + line_len * math.cos(angle)
            x2 = arrow_x + line_len * math.sin(angle)
            y2 = arrow_y - line_len * math.cos(angle)
            draw.line([(x1, y1), (x2, y2)], fill=text_color, width=2)
            # Solid triangle head at tip
            hd, ha = 14, 0.6
            hx1 = x2 - hd * math.sin(angle - ha)
            hy1 = y2 + hd * math.cos(angle - ha)
            hx2 = x2 - hd * math.sin(angle + ha)
            hy2 = y2 + hd * math.cos(angle + ha)
            draw.polygon([(x2, y2), (hx1, hy1), (hx2, hy2)], fill=text_color)

        # --- Bottom pill: location · time ---
        bottom_text = f"{location} · {time_str}" if location else time_str
        bot_bbox = draw.textbbox((0, 0), bottom_text, font=font_md)
        bot_text_w = bot_bbox[2] - bot_bbox[0]
        pill2_w = bot_text_w + 30
        pill2_h = 38
        pill2_r = pill2_h // 2

        px2 = width - pill2_w - padding
        py2 = py + pill_h + 8

        draw.rounded_rectangle([px2, py2, px2 + pill2_w, py2 + pill2_h], radius=pill2_r, fill=bg_color)
        draw.text((px2 + 15, py2 + 7), bottom_text, fill=text_color, font=font_md)

        return img

    def _add_minimal_overlay(
        self,
        image: Image.Image,
        weather_data: dict,
        config: dict,
    ) -> Image.Image:
        """
        Add minimal, clean text overlay on the image.

        Layout (bottom-right aligned):
            ● 7
            1.4m@9s
            ─────────────
            08:30 · Tel Aviv · 12NW
        """
        img = image.copy()
        draw = ImageDraw.Draw(img)

        # Load fonts - two sizes for hierarchy
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font_big = ImageFont.truetype(font_path, 28)
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
            )
        except Exception:
            try:
                font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            except Exception:
                font_big = ImageFont.load_default()
                font_small = ImageFont.load_default()

        padding = 20
        width, height = img.size
        shadow_color = (0, 0, 0)
        text_color = (255, 255, 255)

        # --- Build text content ---

        # Primary line: wave height @ period
        wave = weather_data.get("wave_height")
        period = weather_data.get("wave_period")
        if wave and period:
            primary_text = f"{wave}@{period}"
        elif wave:
            primary_text = wave
        else:
            primary_text = ""

        # Secondary line: time · location · wind
        secondary_parts = []
        secondary_parts.append(datetime.now().strftime("%H:%M"))
        location = weather_data.get("location")
        if location:
            secondary_parts.append(location)
        wind_speed = weather_data.get("wind_speed")
        wind_dir = weather_data.get("wind_direction")
        if wind_speed:
            secondary_parts.append(wind_speed)
        secondary_text = " · ".join(secondary_parts)

        # Reserve space for wind arrow after text
        wind_arrow_space = 18 if wind_dir else 0

        # --- Measure text for right-alignment ---
        primary_bbox = draw.textbbox((0, 0), primary_text, font=font_big) if primary_text else (0, 0, 0, 0)
        secondary_bbox = draw.textbbox((0, 0), secondary_text, font=font_small)
        primary_w = primary_bbox[2] - primary_bbox[0]
        primary_h = primary_bbox[3] - primary_bbox[1]
        secondary_text_w = secondary_bbox[2] - secondary_bbox[0]
        secondary_w = secondary_text_w + wind_arrow_space
        secondary_h = secondary_bbox[3] - secondary_bbox[1]

        # Line width = widest of primary/secondary
        line_w = max(primary_w, secondary_w)

        # --- Position everything from bottom-right upward ---
        line_gap = 8
        right_edge = width - padding

        # Block width = widest element (secondary line is usually widest)
        block_w = line_w
        block_left = right_edge - block_w
        block_center = block_left + block_w // 2

        # Secondary text (bottommost) — right-aligned (defines block width)
        secondary_y = height - padding - secondary_h
        secondary_x = right_edge - secondary_w

        # Horizontal rule — full block width
        rule_y = secondary_y - line_gap

        # Primary text (above rule) — centered in block
        primary_y = rule_y - line_gap - primary_h
        primary_x = block_center - primary_w // 2

        # --- Draw content with outline ---
        rating = weather_data.get("rating")

        # Rating dot + number (above primary text) — centered in block
        if rating is not None:
            self._draw_rating_dot(draw, block_center, primary_y - line_gap - 4, rating, font_small)

        # Primary text (wave data, bold)
        if primary_text:
            self._draw_text_with_outline(draw, primary_x, primary_y, primary_text, font_big, text_color, shadow_color)

        # Horizontal rule
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            draw.line([(block_left + dx, rule_y + dy), (right_edge + dx, rule_y + dy)], fill=shadow_color, width=1)
        draw.line([(block_left, rule_y), (right_edge, rule_y)], fill=text_color, width=1)

        # Secondary text (details)
        self._draw_text_with_outline(draw, secondary_x, secondary_y, secondary_text, font_small, text_color, shadow_color)

        # Wind direction arrow after text
        if wind_dir and wind_arrow_space:
            arrow_x = secondary_x + secondary_text_w + 10
            arrow_y = secondary_y + secondary_h // 2
            self._draw_wind_arrow(draw, arrow_x, arrow_y, wind_dir, shadow_color, text_color)

        return img

    def _draw_wind_arrow(self, draw: ImageDraw.Draw, x: int, y: int, direction: str, outline_color, fill_color):
        """Draw a small wind direction arrow with outline."""
        import math

        angle_map = {
            "N": 180, "NE": 225, "E": 270, "SE": 315,
            "S": 0, "SW": 45, "W": 90, "NW": 135,
        }

        angle = math.radians(angle_map.get(direction, 0))
        size = 7
        head = 5

        # Arrow line
        x1 = x - size * math.sin(angle)
        y1 = y + size * math.cos(angle)
        x2 = x + size * math.sin(angle)
        y2 = y - size * math.cos(angle)

        # Arrowhead
        head_angle = 0.5
        hx1 = x2 - head * math.sin(angle - head_angle)
        hy1 = y2 + head * math.cos(angle - head_angle)
        hx2 = x2 - head * math.sin(angle + head_angle)
        hy2 = y2 + head * math.cos(angle + head_angle)

        # Draw outline
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            draw.line([(x1+dx, y1+dy), (x2+dx, y2+dy)], fill=outline_color, width=2)
            draw.line([(x2+dx, y2+dy), (hx1+dx, hy1+dy)], fill=outline_color, width=2)
            draw.line([(x2+dx, y2+dy), (hx2+dx, hy2+dy)], fill=outline_color, width=2)

        # Draw arrow
        draw.line([(x1, y1), (x2, y2)], fill=fill_color, width=2)
        draw.line([(x2, y2), (hx1, hy1)], fill=fill_color, width=2)
        draw.line([(x2, y2), (hx2, hy2)], fill=fill_color, width=2)

    def _draw_text_with_outline(
        self, draw: ImageDraw.Draw, x: int, y: int,
        text: str, font: ImageFont.ImageFont,
        fill: tuple, outline: tuple, thickness: int = 2,
    ):
        """Draw text with a solid outline for readability on any background."""
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, fill=outline, font=font)
        draw.text((x, y), text, fill=fill, font=font)

    def _draw_rating_dot(
        self, draw: ImageDraw.Draw, center_x: int, y: int,
        rating: int, font: ImageFont.ImageFont,
    ):
        """Draw colored dot + rating number, centered horizontally."""
        # Dot color based on rating
        if rating <= 3:
            dot_color = (255, 0, 0)       # Red - poor
        elif rating <= 6:
            dot_color = (255, 255, 0)     # Yellow - fair
        else:
            dot_color = (0, 255, 0)       # Green - good

        rating_text = str(rating)
        text_bbox = draw.textbbox((0, 0), rating_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        dot_radius = 6
        dot_gap = 6

        # Total width of dot + gap + number, centered
        total_w = dot_radius * 2 + dot_gap + text_w
        start_x = center_x - total_w // 2

        dot_cx = start_x + dot_radius
        dot_cy = y - text_h // 2
        text_x = start_x + dot_radius * 2 + dot_gap
        text_y = y - text_h

        # Draw dot with outline for visibility
        draw.ellipse(
            [dot_cx - dot_radius - 2, dot_cy - dot_radius - 2,
             dot_cx + dot_radius + 2, dot_cy + dot_radius + 2],
            fill=(0, 0, 0),
        )
        draw.ellipse(
            [dot_cx - dot_radius, dot_cy - dot_radius,
             dot_cx + dot_radius, dot_cy + dot_radius],
            fill=dot_color,
        )

        # Draw number with outline
        self._draw_text_with_outline(
            draw, text_x, text_y, rating_text, font,
            (255, 255, 255), (0, 0, 0),
        )

    def process_and_save(
        self,
        image: Image.Image,
        output_path: str = None,
        weather_data: dict = None,
    ) -> Optional[str]:
        """Process image and save to file."""
        processed = self.process(image, weather_data)

        if output_path is None:
            data_dir = Path(self.config.paths.get("data_dir", "./data"))
            output_path = data_dir / "current.bmp"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        processed.save(output_path)
        logger.info(f"Saved processed image: {output_path}")

        return str(output_path)


def process_image(image: Image.Image, weather_data: dict = None) -> Image.Image:
    """Convenience function to process an image."""
    processor = Processor()
    return processor.process(image, weather_data)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        img = Image.open(sys.argv[1])
        result = process_image(img, {
            "location": "Tel Aviv",
            "wave_height": "1.4m",
            "wave_period": "9s",
            "wind_speed": "12km/h",
            "wind_direction": "NW",
            "rating": 7,
        })
        result.save("processed_test.bmp")
        print("Saved to processed_test.bmp")
    else:
        print("Usage: python processor.py <image_path>")
