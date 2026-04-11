"""
Processor module - converts images for E-Ink display.
Handles resizing, preprocessing, color reduction, and overlay.

Pipeline: resize → preprocess → overlay → color reduction → (optional dithering)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

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
    # 6-color E-Ink (Spectra 6): actual display colors
    "6color": [
        (0, 0, 0),          # Black
        (255, 255, 255),    # White
        (0, 0, 255),        # Blue (pure E-Ink blue)
        (255, 255, 0),      # Yellow (sand/sun)
        (255, 0, 0),        # Red
        (0, 255, 0),        # Green
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


class Processor:
    """Processes images for E-Ink display with smooth, print-like output."""

    def __init__(self):
        self.config = get_config()

    def process(
        self,
        image: Image.Image,
        weather_data: dict = None,
    ) -> Image.Image:
        """
        Process image for E-Ink display.

        Pipeline:
        1. Resize to display dimensions
        2. Preprocess (blur, saturation, contrast)
        3. Add overlay text
        4. Color reduction to palette
        5. Optional dithering

        Args:
            image: Input PIL Image.
            weather_data: Optional dict with weather info for overlay.

        Returns:
            Processed PIL Image ready for E-Ink.
        """
        display = self.config.display
        overlay_config = self.config.overlay

        # Get settings
        width = display.get("width", 800)
        height = display.get("height", 480)
        color_mode = display.get("color_mode", "7color")
        dithering = display.get("dithering", True)  # Default ON for detail

        # Step 1: Resize
        img = self._resize(image, width, height)
        logger.debug(f"Resized to {width}x{height}")

        # Step 2: Preprocess for smoother appearance
        img = self._preprocess(img)
        logger.debug("Applied preprocessing")

        # Step 3: Color reduction with dithering
        img = self._reduce_colors(img, color_mode, dithering)
        logger.debug(f"Reduced to {color_mode} palette, dithering={dithering}")

        # Step 4: Add overlay AFTER color reduction (so text stays crisp)
        if overlay_config.get("enabled", True) and weather_data:
            img = self._add_minimal_overlay(img, weather_data, overlay_config)
            logger.debug("Added overlay")

        return img

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for cleaner E-Ink output.

        - Very light blur to reduce camera noise (not too much!)
        - Slight saturation reduction for muted tones
        - Contrast boost for better definition
        """
        img = image.convert("RGB")

        # 1. Moderate blur - smooth noise while keeping structure
        img = img.filter(ImageFilter.GaussianBlur(radius=1.1))

        # 2. Reduce saturation slightly (0.9 = 90% of original)
        saturation_enhancer = ImageEnhance.Color(img)
        img = saturation_enhancer.enhance(0.9)

        # 3. Compress dynamic range (bring darks up, brights down)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(0.85)

        # 5. Neutral color temperature
        img = self._add_warmth(img, 0.05)

        return img

    def _add_warmth(self, image: Image.Image, amount: float = 0.1) -> Image.Image:
        """Shift color temperature. Positive = warmer (more red), negative = cooler (more blue)."""
        import numpy as np
        arr = np.array(image, dtype=np.float32)

        # Adjust color temperature: positive warms, negative cools
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 + amount), 0, 255)      # Red +
        arr[:, :, 1] = np.clip(arr[:, :, 1] * (1 + amount * 0.1), 0, 255) # Green minimal
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 - amount * 0.15), 0, 255) # Blue slight -

        return Image.fromarray(arr.astype(np.uint8))

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
        self, image: Image.Image, color_mode: str, dithering: bool
    ) -> Image.Image:
        """Reduce image colors to E-Ink palette."""
        palette = PALETTES.get(color_mode, PALETTES["5color"])
        logger.debug(f"Using {len(palette)}-color palette, dithering={dithering}")

        if dithering:
            return self._floyd_steinberg_dither(image, palette)
        else:
            return self._nearest_color(image, palette)

    def _perceptual_distance(self, pixels: np.ndarray, palette: np.ndarray) -> np.ndarray:
        """
        Calculate perceptual color distance using weighted RGB.
        Better approximates human vision than simple Euclidean distance.
        Prevents brown from matching blue, etc.
        """
        # Weighted RGB distance formula (approximates human perception)
        # Weight: R=0.3, G=0.59, B=0.11 (luminance-based)
        # But also penalize hue shifts more
        diff = pixels[:, np.newaxis, :] - palette[np.newaxis, :, :]

        # Weights that emphasize hue differences
        # Blue heavily weighted to ensure ocean/sky stays blue
        weights = np.array([3.0, 3.0, 5.0])

        weighted_diff = diff * weights
        distances = np.sum(weighted_diff ** 2, axis=2)

        return distances

    def _nearest_color(
        self, image: Image.Image, palette: List[Tuple[int, int, int]]
    ) -> Image.Image:
        """
        Nearest-color mapping using perceptual distance.
        Produces smooth look while keeping colors accurate.
        """
        arr = np.array(image, dtype=np.float32)
        palette_arr = np.array(palette, dtype=np.float32)

        # Reshape for efficient distance calculation
        h, w = arr.shape[:2]
        pixels = arr.reshape(-1, 3)

        # Use perceptual distance
        distances = self._perceptual_distance(pixels, palette_arr)

        # Find nearest palette color for each pixel
        nearest_indices = np.argmin(distances, axis=1)
        result = palette_arr[nearest_indices].reshape(h, w, 3).astype(np.uint8)

        return Image.fromarray(result)

    def _floyd_steinberg_dither(
        self, image: Image.Image, palette: List[Tuple[int, int, int]]
    ) -> Image.Image:
        """
        Apply Floyd-Steinberg dithering with perceptual color matching.
        Uses weighted RGB distance to prevent color bleeding.
        """
        arr = np.array(image, dtype=np.float32)
        height, width = arr.shape[:2]
        palette_arr = np.array(palette, dtype=np.float32)

        # Perceptual weights - blue heavily weighted for ocean/sky
        weights = np.array([3.0, 3.0, 5.0])

        for y in range(height):
            for x in range(width):
                old_pixel = arr[y, x].copy()

                # Find nearest color using perceptual distance
                diff = palette_arr - old_pixel
                weighted_diff = diff * weights
                distances = np.sum(weighted_diff ** 2, axis=1)
                nearest_idx = np.argmin(distances)
                new_pixel = palette_arr[nearest_idx]

                arr[y, x] = new_pixel

                # Calculate quantization error
                error = old_pixel - new_pixel

                # Distribute error to neighbors (Floyd-Steinberg coefficients)
                # 0.3x error spread - much smoother, painterly look
                if x + 1 < width:
                    arr[y, x + 1] += error * 7 / 16 * 0.3
                if y + 1 < height:
                    if x > 0:
                        arr[y + 1, x - 1] += error * 3 / 16 * 0.3
                    arr[y + 1, x] += error * 5 / 16 * 0.3
                    if x + 1 < width:
                        arr[y + 1, x + 1] += error * 1 / 16 * 0.3

        # Clip and convert
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

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
