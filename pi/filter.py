"""
Filter module - detects and rejects ad frames, loading screens, and invalid images.
Uses heuristics based on color distribution, edge density, and image comparison.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of frame filtering."""
    is_valid: bool
    reason: Optional[str] = None
    confidence: float = 1.0
    image_hash: Optional[str] = None


class FrameFilter:
    """Filters out ad frames and invalid images."""

    def __init__(self):
        self.config = get_config()
        self.last_good_hash: Optional[str] = None
        self.last_good_histogram: Optional[np.ndarray] = None

    def filter(self, image: Image.Image) -> FilterResult:
        """
        Check if an image is a valid beach frame.

        Args:
            image: PIL Image to check.

        Returns:
            FilterResult with validation status.
        """
        settings = self.config.filter_settings

        # Calculate image hash for comparison
        img_hash = self._compute_hash(image)

        # Run validation checks
        checks = [
            self._check_not_solid_color(image),
            self._check_color_distribution(image, settings),
            self._check_edge_density(image, settings),
            self._check_similarity_to_last_good(image, settings),
        ]

        # Aggregate results
        failed_checks = [c for c in checks if not c.is_valid]

        if failed_checks:
            # Return first failure reason
            return FilterResult(
                is_valid=False,
                reason=failed_checks[0].reason,
                confidence=failed_checks[0].confidence,
                image_hash=img_hash,
            )

        # Frame is valid - update last good reference
        self.last_good_hash = img_hash
        self.last_good_histogram = self._compute_histogram(image)

        return FilterResult(is_valid=True, image_hash=img_hash)

    def _compute_hash(self, image: Image.Image) -> str:
        """Compute perceptual hash of image."""
        # Resize to small thumbnail and convert to grayscale
        thumb = image.resize((16, 16), Image.Resampling.LANCZOS).convert("L")
        pixels = list(thumb.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return hashlib.md5(bits.encode()).hexdigest()[:16]

    def _compute_histogram(self, image: Image.Image) -> np.ndarray:
        """Compute color histogram of image."""
        img_rgb = image.convert("RGB")
        arr = np.array(img_rgb)
        hist = np.histogram(arr, bins=64, range=(0, 256))[0]
        return hist / hist.sum()  # Normalize

    def _check_not_solid_color(self, image: Image.Image) -> FilterResult:
        """Reject images that are mostly one solid color (loading screens, errors)."""
        arr = np.array(image.convert("RGB"))
        variance = np.var(arr)

        if variance < 100:  # Very low variance = solid color
            return FilterResult(
                is_valid=False,
                reason="Solid color frame (loading/error screen)",
                confidence=0.9,
            )
        return FilterResult(is_valid=True)

    def _check_color_distribution(
        self, image: Image.Image, settings: dict
    ) -> FilterResult:
        """
        Check if image has beach-like color distribution.
        Beach scenes should have blues, tans, whites (sky, sea, sand).
        """
        if not settings.get("check_color_distribution", True):
            return FilterResult(is_valid=True)

        arr = np.array(image.convert("RGB"))

        # Calculate average color
        avg_color = arr.mean(axis=(0, 1))
        r, g, b = avg_color

        # Beach scenes typically have:
        # - Blue dominant (sky/sea): high B, moderate R, G
        # - Tan (sand): R > G > B, warm tones
        # - Gray (overcast): similar R, G, B

        # Reject if too red/magenta (common in ads)
        if r > 180 and r > g * 1.3 and r > b * 1.3:
            return FilterResult(
                is_valid=False,
                reason="Unusual color distribution (too red/warm - likely ad)",
                confidence=0.7,
            )

        # Reject if too saturated green (not typical for beach)
        if g > 180 and g > r * 1.3 and g > b * 1.3:
            return FilterResult(
                is_valid=False,
                reason="Unusual color distribution (too green - likely ad)",
                confidence=0.7,
            )

        return FilterResult(is_valid=True)

    def _check_edge_density(self, image: Image.Image, settings: dict) -> FilterResult:
        """
        Check edge density - ads/UI typically have sharp edges and text.
        Natural beach scenes have smoother gradients.
        """
        # Convert to grayscale
        gray = np.array(image.convert("L"), dtype=np.float32)

        # Simple edge detection (gradient magnitude)
        gx = np.abs(np.diff(gray, axis=1))
        gy = np.abs(np.diff(gray, axis=0))

        # Calculate edge density (percentage of strong edges)
        edge_threshold = 30
        edge_ratio_x = (gx > edge_threshold).mean()
        edge_ratio_y = (gy > edge_threshold).mean()
        edge_ratio = (edge_ratio_x + edge_ratio_y) / 2

        # High edge density suggests UI elements, text, ads
        max_edge_ratio = 0.15  # 15% of pixels with strong edges
        if edge_ratio > max_edge_ratio:
            return FilterResult(
                is_valid=False,
                reason=f"High edge density ({edge_ratio:.1%}) - likely ad/UI",
                confidence=0.6,
            )

        return FilterResult(is_valid=True)

    def _check_similarity_to_last_good(
        self, image: Image.Image, settings: dict
    ) -> FilterResult:
        """
        Compare to last known good frame.
        Very different frames might be ads or errors.
        """
        if self.last_good_histogram is None:
            # No reference yet, accept
            return FilterResult(is_valid=True)

        min_similarity = settings.get("min_similarity", 0.3)

        current_hist = self._compute_histogram(image)
        similarity = np.minimum(current_hist, self.last_good_histogram).sum()

        if similarity < min_similarity:
            return FilterResult(
                is_valid=False,
                reason=f"Too different from last good frame (similarity: {similarity:.1%})",
                confidence=0.5,
            )

        return FilterResult(is_valid=True)


# Convenience function
def filter_image(image: Image.Image) -> FilterResult:
    """Filter a single image."""
    f = FrameFilter()
    return f.filter(image)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        img = Image.open(sys.argv[1])
        result = filter_image(img)
        print(f"Valid: {result.is_valid}")
        print(f"Reason: {result.reason}")
        print(f"Hash: {result.image_hash}")
    else:
        print("Usage: python filter.py <image_path>")
