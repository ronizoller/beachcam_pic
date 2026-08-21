"""
Scorer module - rates frame composition quality.

Two scoring methods:
- "jaffa" profile: Zone-based — detects beach at bottom + Jaffa buildings at top-left
- "beach" profile: Composition-based — color ratio matching for guest beaches
"""

import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# Scoring profiles
SCORING_PROFILES = {
    # Main Tel Aviv camera: zone-based (beach + Jaffa detection)
    "jaffa": {
        "method": "zones",
        "beach_weight": 0.50,
        "jaffa_weight": 0.30,
        "synergy_weight": 0.20,
    },
    # Guest beaches: composition-based (color ratios)
    "beach": {
        "method": "composition",
        "sea_sky": 0.55,
        "beach": 0.25,
        "buildings": 0.20,
    },
}


def score_frame(
    image: Image.Image,
    profile: str = "jaffa",
    golden_hour: bool = False,
    details: Optional[dict] = None,
) -> float:
    """
    Score a frame's composition quality.

    Args:
        image: PIL Image to score.
        profile: Scoring profile name ("jaffa" or "beach").
        golden_hour: If True, add a sunset/sunrise bonus on top of the base
            profile score. The bonus rewards warm-colored skies and is meant
            to be enabled only inside the sunrise/sunset window so the
            "goodnight image" served overnight has a chance to win against
            high-scoring daytime frames still in the candidate pool.
        details: Optional dict, populated in place with the score breakdown
            (base, bonus, sub-signals). Used to archive per-frame diagnostics
            so a night's candidates can be reviewed offline and the selection
            second-guessed against what a human would have picked.

    Returns:
        Score, typically 0.0–1.0 but may exceed 1.0 when golden_hour=True
        and the frame has strong sunset characteristics. The selector just
        picks the maximum so the absolute scale doesn't matter.
    """
    cfg = SCORING_PROFILES.get(profile, SCORING_PROFILES["jaffa"])
    img = image.convert("RGB")
    arr = np.array(img, dtype=np.float32)

    method = cfg.get("method", "composition")

    if method == "zones":
        base = _score_zones(arr, cfg, profile)
    else:
        base = _score_composition(arr, cfg, profile)

    if details is not None:
        details.update({"profile": profile, "base": round(base, 4), "golden_hour": golden_hour})

    if not golden_hour:
        if details is not None:
            details["final"] = round(base, 4)
        return base

    bonus = _golden_hour_bonus(arr, details=details)
    # Additive with a fixed weight. A perfect warm sky adds 0.5 — strong
    # enough to outscore typical daytime frames (which sit around 0.2–0.5
    # base) without making mediocre warm scenes always win.
    weighted = bonus * 0.5
    final = base + weighted
    if details is not None:
        details.update({
            "bonus": round(bonus, 4),
            "bonus_weighted": round(weighted, 4),
            "final": round(final, 4),
        })
    logger.info(
        f"Golden-hour scoring [{profile}]: base={base:.3f}, "
        f"warm_sky_bonus={bonus:.3f} (weighted {weighted:.3f}), final={final:.3f}"
    )
    return final


def _score_zones(arr: np.ndarray, cfg: dict, profile: str) -> float:
    """Zone-based scoring for Jaffa camera."""
    beach = _beach_presence(arr)
    jaffa = _jaffa_presence(arr)

    bw = cfg["beach_weight"]
    jw = cfg["jaffa_weight"]
    sw = cfg["synergy_weight"]

    base = beach * bw + jaffa * jw
    synergy = (beach * jaffa) ** 0.5 * sw
    score = min(1.0, base + synergy)

    logger.debug(
        f"Frame score: {score:.3f} [{profile}] "
        f"(beach={beach:.3f}, jaffa={jaffa:.3f}, synergy={synergy:.3f})"
    )
    return score


def _score_composition(arr: np.ndarray, cfg: dict, profile: str) -> float:
    """Composition-based scoring for guest beaches."""
    sea_sky_pct, beach_pct, buildings_pct = _classify_pixels(arr)

    sea_sky_diff = abs(sea_sky_pct - cfg["sea_sky"])
    beach_diff = abs(beach_pct - cfg["beach"])
    buildings_diff = abs(buildings_pct - cfg["buildings"])

    distance = (sea_sky_diff * 0.3 + beach_diff * 0.3 + buildings_diff * 0.4)
    score = max(0.0, 1.0 - distance * 2.0)

    logger.debug(
        f"Frame score: {score:.3f} [{profile}] "
        f"(sea/sky={sea_sky_pct:.0%}, beach={beach_pct:.0%}, "
        f"buildings={buildings_pct:.0%})"
    )
    return score


# --- Golden-hour bonus (used during sunrise/sunset window) ---

def _golden_hour_bonus(arr: np.ndarray, details: Optional[dict] = None) -> float:
    """
    Detect warm-colored sky in the upper portion of the frame.

    Tel Aviv evenings produce a wide range of golden-hour appearances, and
    pixel-level signals are weaker than they look to the eye:
      - Vivid sunset: R clearly dominates B (R-B > 40), R > 100.
      - Pastel dusk: R only slightly above B (R-B > 5), the bulk of soft
        pinkish-lavender evenings. The mean R-B can still be near zero
        because cool areas drag the average down.
      - Tail warmth: even pastel skies have a small fraction of strongly
        warm pixels near the horizon; the 95th-percentile R-B value
        captures that tail as a tie-breaker between "uniformly muted"
        and "muted overall but with visible warm glow."

    Combining the three lets a strong vivid sunset clearly outscore a
    pastel evening, and a pastel-with-glow outscore a uniform muted dusk.

    Returns:
        Bonus between 0.0 (no warm sky) and 1.0 (sky strongly warm).
    """
    h = arr.shape[0]
    # 60% covers the horizon line where the warm band often sits — at 50%
    # the cutoff sometimes slices through the brightest part of the glow.
    sky = arr[:int(h * 0.60), :, :]
    r, g, b = sky[:, :, 0], sky[:, :, 1], sky[:, :, 2]

    is_vivid = (r > b + 40) & (r > g + 5) & (r > 100)
    is_pastel = (r > b + 5) & (r > 100) & ~is_vivid

    vivid_pct = float(np.sum(is_vivid)) / r.size
    pastel_pct = float(np.sum(is_pastel)) / r.size

    # Tail: how warm are the warmest pixels? Distinguishes "uniformly
    # muted pink" (low tail) from "pink with a glowing horizon" (high tail).
    # p95 R-B for a clear blue sky is ~-15, overcast ~-4, pastel dusk ~5-20,
    # vivid sunset ~30-60. Map 0→0, 30→1.
    rb = r - b
    p95_warm = float(np.percentile(rb, 95))
    tail_score = max(0.0, min(1.0, p95_warm / 30.0))

    # Vivid weighted highest (a real sunset should clearly win), pastel
    # is the main pastel-dusk signal, tail breaks ties between similar
    # pastel coverage levels.
    warm_score = vivid_pct * 1.0 + pastel_pct * 0.5 + tail_score * 0.2

    if details is not None:
        # Mean brightness of the sky region gives context when reviewing:
        # it separates "no warm colour" from "too dark to register".
        details.update({
            "vivid_pct": round(vivid_pct, 4),
            "pastel_pct": round(pastel_pct, 4),
            "p95_r_minus_b": round(p95_warm, 2),
            "tail_score": round(tail_score, 4),
            "warm_score": round(warm_score, 4),
            "sky_mean_r": round(float(r.mean()), 1),
            "sky_mean_b": round(float(b.mean()), 1),
        })

    if warm_score < 0.05:
        return 0.0
    if warm_score >= 0.5:
        return 1.0
    return (warm_score - 0.05) / 0.45


# --- Zone-based detection functions (Jaffa profile) ---

def _beach_presence(arr: np.ndarray) -> float:
    """
    Detect beach presence in the bottom 20% of the image.

    Counts warm/sandy pixels. More beach = higher score (linear ramp).

    Returns:
        Score between 0.0 (no beach) and 1.0 (lots of beach).
    """
    h = arr.shape[0]
    bottom = arr[int(h * 0.80):, :, :]
    r, g, b = bottom[:, :, 0], bottom[:, :, 1], bottom[:, :, 2]

    # Warm pixels: R clearly dominates G and B
    is_warm = (r > g + 10) & (r > b + 10) & (r > 100)
    # Sandy pixels: R and G close, both well above B
    is_sandy = (np.abs(r - g) < 30) & (r > b + 25) & (r > 120)

    beach_pct = np.sum(is_warm | is_sandy) / r.size

    # Linear ramp: 0% → 0, 70% → 1.0
    if beach_pct < 0.03:
        return 0.0
    elif beach_pct <= 0.70:
        return beach_pct / 0.70
    else:
        return 1.0


def _jaffa_presence(arr: np.ndarray) -> float:
    """
    Detect Jaffa buildings in the top-left 40% x 30% of the image.

    Uses warm-pixel analysis: Jaffa's stone buildings have R > B (warm tones),
    while sea/sky have B >= R (cool tones). This works even on hazy/overcast days.

    Returns:
        Score between 0.0 (no Jaffa) and 1.0 (Jaffa clearly visible).
    """
    h, w = arr.shape[:2]
    zone = arr[:int(h * 0.30), :int(w * 0.40), :]
    r, b = zone[:, :, 0], zone[:, :, 2]

    # Warm pixels (R > B + 5) = Jaffa stone; cool pixels = sea/sky
    warm_pct = np.sum(r > b + 5) / r.size

    # Below 30% warm = no Jaffa visible (all sea/sky)
    # 30-50% = partial Jaffa (ramp to 0.5)
    # 50-95% = clear Jaffa (ramp to 1.0)
    if warm_pct < 0.30:
        return 0.0
    elif warm_pct < 0.50:
        return (warm_pct - 0.30) / 0.20 * 0.5
    elif warm_pct <= 0.95:
        return 0.5 + (warm_pct - 0.50) / 0.45 * 0.5
    else:
        return 1.0


# --- Composition-based detection functions (beach profile) ---

def _classify_pixels(arr: np.ndarray) -> Tuple[float, float, float]:
    """
    Classify pixels into sea/sky, beach, and buildings.

    Returns:
        Tuple of (sea_sky_pct, beach_pct, buildings_pct) each 0.0-1.0
    """
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    total_pixels = arr.shape[0] * arr.shape[1]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c

    v = max_c

    with np.errstate(divide='ignore', invalid='ignore'):
        sat = np.where(max_c > 0, delta / max_c, 0)

    hue = np.zeros_like(max_c)
    mask_r = (max_c == r) & (delta > 0)
    hue[mask_r] = (60 * ((g[mask_r] - b[mask_r]) / delta[mask_r])) % 360
    mask_g = (max_c == g) & (delta > 0)
    hue[mask_g] = 60 * ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 120
    mask_b = (max_c == b) & (delta > 0)
    hue[mask_b] = 60 * ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 240

    is_blue = (hue >= 180) & (hue <= 260) & (sat > 0.1)
    is_bright_sky = (v > 180) & (sat < 0.2)
    is_dark_water = (v <= 180) & (sat < 0.2)
    is_sea_sky = is_blue | is_bright_sky | is_dark_water

    is_beach = (
        (hue >= 25) & (hue <= 55) &
        (sat > 0.15) & (sat < 0.7) &
        (v > 80) & (v < 230)
    )

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
