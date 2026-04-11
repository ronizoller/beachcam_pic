"""
Scorer module - rates frame composition quality.

Classifies pixels into sea, sky, beach, and buildings/land,
then scores how close the frame is to an ideal beach composition:
~60% sea/sky, ~15% beach, ~25% buildings/land.

A frame with only sea scores low. A frame with good mix scores high.
"""

import logging
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# Ideal composition ratios (mostly sea, some land context)
IDEAL_SEA_SKY = 0.75
IDEAL_BEACH = 0.05
IDEAL_BUILDINGS = 0.20

# HSV-based color classification thresholds
# H: 0-180 (OpenCV convention), S: 0-255, V: 0-255
# We use 0-360/0-1/0-1 from colorsys, converted to numpy-friendly ranges


# Scoring profiles: different ideal ratios and components per camera type
SCORING_PROFILES = {
    # Main Tel Aviv camera: mostly sea, some buildings, Jaffa landmark bonus
    "jaffa": {
        "sea_sky": 0.75,
        "beach": 0.05,
        "buildings": 0.20,
        "left_structure": True,  # Jaffa landmark bonus
        "composition_weight": 0.7,
        "structure_weight": 0.3,
    },
    # Guest beaches: prefer beach + sea mix, no landmark bonus
    "beach": {
        "sea_sky": 0.55,
        "beach": 0.25,
        "buildings": 0.20,
        "left_structure": False,
        "composition_weight": 1.0,
        "structure_weight": 0.0,
    },
}


def score_frame(image: Image.Image, profile: str = "jaffa") -> float:
    """
    Score a frame's composition quality.

    Args:
        image: PIL Image to score.
        profile: Scoring profile name ("jaffa" or "beach").

    Returns:
        Score between 0.0 (worst) and 1.0 (best).
    """
    cfg = SCORING_PROFILES.get(profile, SCORING_PROFILES["jaffa"])

    img = image.convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # 1. Composition score
    sea_sky_pct, beach_pct, buildings_pct = _classify_pixels(arr)

    sea_sky_diff = abs(sea_sky_pct - cfg["sea_sky"])
    beach_diff = abs(beach_pct - cfg["beach"])
    buildings_diff = abs(buildings_pct - cfg["buildings"])

    distance = (sea_sky_diff * 0.3 + beach_diff * 0.3 + buildings_diff * 0.4)
    composition_score = max(0.0, 1.0 - distance * 2.0)

    # 2. Structure score (only if enabled for this profile)
    if cfg["left_structure"]:
        structure_score = _left_structure_score(img)
    else:
        structure_score = 0.0

    score = (composition_score * cfg["composition_weight"] +
             structure_score * cfg["structure_weight"])

    logger.debug(
        f"Frame score: {score:.3f} [{profile}] "
        f"(composition={composition_score:.3f}, structure={structure_score:.3f}, "
        f"sea/sky={sea_sky_pct:.0%}, beach={beach_pct:.0%}, "
        f"buildings={buildings_pct:.0%})"
    )

    return score


def _left_structure_score(image: Image.Image) -> float:
    """
    Score structural detail in the left 30% of the image.

    Uses edge detection — high edge density means buildings/structures
    are visible (Jaffa, port wall, jetty). Flat sea has very few edges.

    Returns:
        Score between 0.0 (flat/no structure) and 1.0 (lots of structure).
    """
    width = image.width
    left_region = image.crop((0, 0, int(width * 0.3), image.height))

    # Convert to grayscale and detect edges
    gray = left_region.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)

    # Mean edge intensity (0-255)
    edge_arr = np.array(edges, dtype=np.float32)
    mean_edge = edge_arr.mean()

    # Normalize: ~5 = flat sea, ~30+ = buildings/structure
    # Map to 0-1 with soft clamp
    score = min(1.0, max(0.0, (mean_edge - 5) / 25.0))

    logger.debug(f"Left structure: mean_edge={mean_edge:.1f}, score={score:.3f}")
    return score


def _classify_pixels(arr: np.ndarray) -> Tuple[float, float, float]:
    """
    Classify pixels into sea/sky, beach, and buildings.

    Uses HSV color space for robust classification:
    - Sea/sky: blue-ish hues (H ~180-260) or very bright/white (sky)
    - Beach/sand: warm hues (H ~30-50), moderate saturation
    - Buildings/land: everything else (gray, brown, varied)

    Returns:
        Tuple of (sea_sky_pct, beach_pct, buildings_pct) each 0.0-1.0
    """
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    total_pixels = arr.shape[0] * arr.shape[1]

    # Convert to simple HSV-like features without OpenCV
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c

    # Value (brightness) 0-255
    v = max_c

    # Saturation 0-1
    sat = np.where(max_c > 0, delta / max_c, 0)

    # Hue 0-360
    hue = np.zeros_like(max_c)
    # Red is max
    mask_r = (max_c == r) & (delta > 0)
    hue[mask_r] = (60 * ((g[mask_r] - b[mask_r]) / delta[mask_r])) % 360
    # Green is max
    mask_g = (max_c == g) & (delta > 0)
    hue[mask_g] = 60 * ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 120
    # Blue is max
    mask_b = (max_c == b) & (delta > 0)
    hue[mask_b] = 60 * ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 240

    # --- Classification ---

    # Sea/sky: blue hues, OR bright low-sat (sky/clouds), OR dark low-sat (dark water/shadows)
    is_blue = (hue >= 180) & (hue <= 260) & (sat > 0.1)
    is_bright_sky = (v > 180) & (sat < 0.2)  # White/light gray sky
    is_dark_water = (v <= 180) & (sat < 0.2)  # Dark gray water/shadows
    is_sea_sky = is_blue | is_bright_sky | is_dark_water

    # Beach/sand: warm hues (25-55), moderate saturation, moderate brightness
    is_beach = (
        (hue >= 25) & (hue <= 55) &
        (sat > 0.15) & (sat < 0.7) &
        (v > 80) & (v < 230)
    )

    # Buildings/land: everything else
    is_buildings = ~is_sea_sky & ~is_beach

    sea_sky_pct = np.sum(is_sea_sky) / total_pixels
    beach_pct = np.sum(is_beach) / total_pixels
    buildings_pct = np.sum(is_buildings) / total_pixels

    return sea_sky_pct, beach_pct, buildings_pct


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        img = Image.open(sys.argv[1])
        profile = sys.argv[2] if len(sys.argv) > 2 else "jaffa"
        score = score_frame(img, profile)
        print(f"Score: {score:.3f} (profile: {profile})")
    else:
        print(f"Usage: python scorer.py <image_path> [profile]")
        print(f"Profiles: {', '.join(SCORING_PROFILES.keys())}")
