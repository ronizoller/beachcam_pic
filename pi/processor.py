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

        # Step 3: Add overlay BEFORE color reduction (so text gets quantized too)
        if overlay_config.get("enabled", True) and weather_data:
            img = self._add_minimal_overlay(img, weather_data, overlay_config)
            logger.debug("Added overlay")

        # Step 4 & 5: Color reduction with dithering
        img = self._reduce_colors(img, color_mode, dithering)
        logger.debug(f"Reduced to {color_mode} palette, dithering={dithering}")

        return img

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for cleaner E-Ink output.

        - Very light blur to reduce camera noise (not too much!)
        - Slight saturation reduction for muted tones
        - Contrast boost for better definition
        """
        img = image.convert("RGB")

        # 1. Minimal blur - preserve texture/detail
        img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

        # 2. Reduce saturation slightly (0.9 = 90% of original)
        saturation_enhancer = ImageEnhance.Color(img)
        img = saturation_enhancer.enhance(0.9)

        # 3. Boost contrast for better definition
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.25)

        # 4. Add warmth (boost red/yellow, reduce blue)
        img = self._add_warmth(img, 0.25)

        return img

    def _add_warmth(self, image: Image.Image, amount: float = 0.1) -> Image.Image:
        """Add warmth to image by shifting color temperature."""
        import numpy as np
        arr = np.array(image, dtype=np.float32)

        # Warm up: boost red, keep green neutral, minimal blue reduction
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
                # 0.55x error spread - smoother, less noisy
                if x + 1 < width:
                    arr[y, x + 1] += error * 7 / 16 * 0.55
                if y + 1 < height:
                    if x > 0:
                        arr[y + 1, x - 1] += error * 3 / 16 * 0.55
                    arr[y + 1, x] += error * 5 / 16 * 0.55
                    if x + 1 < width:
                        arr[y + 1, x + 1] += error * 1 / 16 * 0.55

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

        Style: Clean white text with subtle shadow for readability.
        Format: "Tel Aviv · 0.8m · 12km/h W"
        """
        img = image.copy()
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            try:
                # macOS fonts
                font_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                font_main = ImageFont.load_default()

        padding = 25
        width, height = img.size

        # Build info line: "08:30 · Tel Aviv · 1.4m@9s · 12km/h ↗"
        parts = []

        # Add current time
        parts.append(datetime.now().strftime("%H:%M"))

        location = weather_data.get("location")
        if location:
            parts.append(location)

        # Wave: height @ period
        wave = weather_data.get("wave_height")
        period = weather_data.get("wave_period")
        if wave and period:
            parts.append(f"{wave}@{period}")
        elif wave:
            parts.append(wave)

        # Wind: speed (arrow drawn separately)
        wind_speed = weather_data.get("wind_speed")
        wind_dir = weather_data.get("wind_direction")
        if wind_speed:
            parts.append(wind_speed)

        info_text = " · ".join(parts)

        # Position: bottom-left
        text_x = padding
        text_y = height - padding - 28

        # Draw text with shadow/outline for readability on any background
        shadow_color = (0, 0, 0)
        text_color = (255, 255, 255)

        # Draw shadow (multiple offsets for thicker outline)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((text_x + dx, text_y + dy), info_text, fill=shadow_color, font=font_main)

        # Draw main text
        draw.text((text_x, text_y), info_text, fill=text_color, font=font_main)

        # Draw wind arrow after text
        if wind_dir:
            # Get text width to position arrow after it
            try:
                text_bbox = draw.textbbox((0, 0), info_text, font=font_main)
                text_width = text_bbox[2] - text_bbox[0]
            except:
                text_width = len(info_text) * 12  # Fallback estimate

            arrow_x = text_x + text_width + 8
            arrow_y = text_y + 12  # Center vertically with text
            self._draw_wind_arrow(draw, arrow_x, arrow_y, wind_dir, shadow_color, text_color)

        # Draw rating circles in top-right
        rating = weather_data.get("rating")
        if rating is not None:
            self._draw_rating_circles(draw, width - padding, padding, rating)

        return img

    def _draw_rating_circles(self, draw: ImageDraw.Draw, x: int, y: int, rating: int):
        """Draw rating 1-10 as circles with half-fill support."""
        num_circles = 5
        circle_size = 14
        spacing = 18

        # Rating 1-10: each circle = 2 points, half circle = 1 point
        # Rating 1 = half of 1st, Rating 2 = full 1st, Rating 3 = full 1st + half 2nd, etc.

        # Draw circles right-to-left from top-right corner
        for i in range(num_circles):
            cx = x - (i * spacing) - circle_size // 2
            cy = y + circle_size // 2

            # Circle bounds
            x0, y0 = cx - circle_size // 2, cy - circle_size // 2
            x1, y1 = cx + circle_size // 2, cy + circle_size // 2

            circle_num = num_circles - i  # 5, 4, 3, 2, 1
            circle_value = circle_num * 2  # Points needed for full circle: 2, 4, 6, 8, 10

            # Black outline
            draw.ellipse([x0-2, y0-2, x1+2, y1+2], fill=(0, 0, 0))

            if rating >= circle_value:
                # Full circle: white
                draw.ellipse([x0, y0, x1, y1], fill=(255, 255, 255))
            elif rating >= circle_value - 1:
                # Half circle: left half white, right half black
                draw.ellipse([x0, y0, x1, y1], fill=(0, 0, 0))
                # Draw left half using pieslice
                draw.pieslice([x0, y0, x1, y1], start=90, end=270, fill=(255, 255, 255))
            else:
                # Empty: black center
                draw.ellipse([x0+2, y0+2, x1-2, y1-2], fill=(0, 0, 0))

    def _draw_wind_arrow(self, draw: ImageDraw.Draw, x: int, y: int, direction: str, shadow_color, fill_color):
        """Draw a simple wind direction arrow."""
        import math

        # Arrow points in direction wind is blowing TO
        angle_map = {
            "N": 180, "NE": 225, "E": 270, "SE": 315,
            "S": 0, "SW": 45, "W": 90, "NW": 135,
        }

        angle = math.radians(angle_map.get(direction, 0))

        # Simple arrow: line + two angled lines for head
        size = 10
        head = 6

        # End points of main line
        x1 = x - size * math.sin(angle)
        y1 = y + size * math.cos(angle)
        x2 = x + size * math.sin(angle)
        y2 = y - size * math.cos(angle)

        # Arrow head lines (two lines from tip at 45 degree angles)
        head_angle = 0.5  # ~30 degrees
        hx1 = x2 - head * math.sin(angle - head_angle)
        hy1 = y2 + head * math.cos(angle - head_angle)
        hx2 = x2 - head * math.sin(angle + head_angle)
        hy2 = y2 + head * math.cos(angle + head_angle)

        # Draw with shadow outline
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1), (-1,1), (1,-1)]:
            draw.line([(x1+dx, y1+dy), (x2+dx, y2+dy)], fill=shadow_color, width=3)
            draw.line([(x2+dx, y2+dy), (hx1+dx, hy1+dy)], fill=shadow_color, width=3)
            draw.line([(x2+dx, y2+dy), (hx2+dx, hy2+dy)], fill=shadow_color, width=3)

        # Draw white arrow
        draw.line([(x1, y1), (x2, y2)], fill=fill_color, width=2)
        draw.line([(x2, y2), (hx1, hy1)], fill=fill_color, width=2)
        draw.line([(x2, y2), (hx2, hy2)], fill=fill_color, width=2)

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
        result = process_image(img, {"location": "Tel Aviv", "wave_height": "1.2m"})
        result.save("processed_test.bmp")
        print("Saved to processed_test.bmp")
    else:
        print("Usage: python processor.py <image_path>")
