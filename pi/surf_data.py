"""
Surf data module - fetches wave and weather data from Open-Meteo API.
Free API, no key required.

Data sources:
- Marine API: wave height, swell, period
- Weather API: wind, temperature
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config import get_config

logger = logging.getLogger(__name__)

# Open-Meteo API endpoints
MARINE_API = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


@dataclass
class SurfPreferences:
    """User's surf preferences for quality rating."""
    min_wave_cm: int = 60   # Minimum wave height in cm
    max_wave_cm: int = 110  # Maximum wave height in cm
    max_wind_kmh: int = 25  # Max acceptable wind speed
    beach_facing: int = 270  # Direction beach faces (degrees). 270 = West (Tel Aviv)


@dataclass
class SurfConditions:
    """Current surf and weather conditions."""
    location: str = "Beach"

    # Wave data
    wave_height: Optional[float] = None  # meters
    wave_period: Optional[float] = None  # seconds
    wave_direction: Optional[int] = None  # degrees

    # Swell data
    swell_height: Optional[float] = None  # meters
    swell_period: Optional[float] = None  # seconds
    swell_direction: Optional[int] = None  # degrees

    # Weather data
    wind_speed: Optional[float] = None  # km/h
    wind_direction: Optional[int] = None  # degrees
    temperature: Optional[float] = None  # celsius

    def calculate_quality(self, prefs: SurfPreferences = None) -> int:
        """
        Calculate surf quality rating 1-10 based on conditions and preferences.

        Factors:
        - Wave height (most important) - must be in preferred range
        - Wave period (longer = better)
        - Wind speed (lower = better)
        """
        if prefs is None:
            prefs = SurfPreferences()

        if self.wave_height is None:
            return 0

        score = 0.0
        wave_cm = self.wave_height * 100  # Convert to cm

        # Wave height score (0-5 points)
        # Perfect score if within preferred range
        if prefs.min_wave_cm <= wave_cm <= prefs.max_wave_cm:
            # Calculate how centered in the range (peak at middle)
            range_mid = (prefs.min_wave_cm + prefs.max_wave_cm) / 2
            range_span = (prefs.max_wave_cm - prefs.min_wave_cm) / 2
            distance_from_mid = abs(wave_cm - range_mid)
            wave_score = 5.0 * (1 - distance_from_mid / range_span * 0.3)
            score += wave_score
        elif wave_cm < prefs.min_wave_cm:
            # Too small - score decreases as it gets smaller
            ratio = wave_cm / prefs.min_wave_cm
            score += 5.0 * ratio * 0.5  # Max 2.5 if just under
        else:
            # Too big - gentle falloff near max, steeper further out
            over_pct = (wave_cm - prefs.max_wave_cm) / prefs.max_wave_cm
            # 10% over → ~4.5, 30% over → ~3.5, 50%+ over → ~2.5
            score += 5.0 * max(0.4, 1.0 - over_pct * 2.0)

        # Wave period score (0-2 points)
        # Longer period = cleaner waves
        # Tuned for Mediterranean (Tel Aviv): 10s+ is great, 7s+ is good
        if self.wave_period:
            if self.wave_period >= 10:
                score += 2.0
            elif self.wave_period >= 5:
                # Smooth gradient: 5s → 1.0, 10s → 2.0
                score += 1.0 + (self.wave_period - 5) * 0.2
            else:
                # Below 5s: choppy
                score += max(0.0, self.wave_period / 5.0 * 1.0)

        # Combined wind score (0-3 points)
        # Direction only matters when wind is strong enough to feel
        if self.wind_speed is not None:
            # Classify direction: offshore, cross, or onshore
            wind_type = "cross"  # default if no direction data
            if self.wind_direction is not None:
                offshore_dir = (prefs.beach_facing + 180) % 360
                angle_diff = abs(self.wind_direction - offshore_dir)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                if angle_diff <= 60:
                    wind_type = "offshore"
                elif angle_diff >= 120:
                    wind_type = "onshore"

            if self.wind_speed <= 5:
                score += 3.0  # Glass, direction irrelevant
            elif self.wind_speed <= 10:
                if wind_type == "offshore":
                    score += 2.5
                elif wind_type == "cross":
                    score += 2.0
                else:
                    score += 1.5  # Light onshore
            elif self.wind_speed <= 20:
                if wind_type == "offshore":
                    score += 2.0
                elif wind_type == "cross":
                    score += 1.5
                else:
                    score += 1.0  # Onshore
            else:
                # 20+ km/h — direction matters a lot
                if wind_type == "offshore":
                    score += 1.0
                elif wind_type == "cross":
                    score += 0.5
                # Onshore 20+ = 0 points

        # Round and clamp to 1-10
        rating = max(1, min(10, round(score)))
        return rating

    def get_quality_label(self, rating: int) -> str:
        """Get a text label for the quality rating."""
        labels = {
            10: "Epic!",
            9: "Excellent",
            8: "Great",
            7: "Good",
            6: "Fair+",
            5: "Fair",
            4: "Poor+",
            3: "Poor",
            2: "Bad",
            1: "Flat",
        }
        return labels.get(rating, "?")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "location": self.location,
            "wave_height": self.wave_height,
            "wave_period": self.wave_period,
            "wave_direction": self.wave_direction,
            "swell_height": self.swell_height,
            "swell_period": self.swell_period,
            "swell_direction": self.swell_direction,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "temperature": self.temperature,
        }

    def format_overlay(self, prefs: SurfPreferences = None) -> dict:
        """Format data for display overlay."""
        rating = self.calculate_quality(prefs)
        return {
            "location": self.location,
            "wave_height": f"{self.wave_height:.1f}m" if self.wave_height else None,
            "wave_height_cm": int(self.wave_height * 100) if self.wave_height else None,
            "wave_period": f"{self.wave_period:.0f}s" if self.wave_period else None,
            "swell_height": f"{self.swell_height:.1f}m" if self.swell_height else None,
            "swell_period": f"{self.swell_period:.0f}s" if self.swell_period else None,
            "wind_speed": f"{self.wind_speed:.0f}km/h" if self.wind_speed else None,
            "wind_direction": self._degrees_to_cardinal(self.wind_direction) if self.wind_direction else None,
            "temperature": f"{self.temperature:.0f}°C" if self.temperature else None,
            "rating": rating,
            "rating_label": self.get_quality_label(rating),
        }

    @staticmethod
    def _degrees_to_cardinal(degrees: int) -> str:
        """Convert degrees to cardinal direction."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degrees / 45) % 8
        return directions[idx]


class SurfDataFetcher:
    """Fetches surf and weather data from Open-Meteo."""

    def __init__(self):
        self.config = get_config()
        self._cache: Optional[SurfConditions] = None

    def fetch(self) -> SurfConditions:
        """
        Fetch current surf conditions.

        Returns:
            SurfConditions with current data.
        """
        weather_config = self.config.get("weather", default={})
        location = weather_config.get("location", {})

        lat = location.get("lat", 32.0853)  # Default: Tel Aviv
        lon = location.get("lon", 34.7818)
        name = location.get("name", "Tel Aviv")

        conditions = SurfConditions(location=name)

        # Fetch marine data (waves, swell)
        try:
            marine_data = self._fetch_marine(lat, lon)
            if marine_data:
                conditions.wave_height = marine_data.get("wave_height")
                conditions.wave_period = marine_data.get("wave_period")
                conditions.wave_direction = marine_data.get("wave_direction")
                conditions.swell_height = marine_data.get("swell_wave_height")
                conditions.swell_period = marine_data.get("swell_wave_period")
                conditions.swell_direction = marine_data.get("swell_wave_direction")
        except Exception as e:
            logger.error(f"Failed to fetch marine data: {e}")

        # Fetch weather data (wind, temp)
        try:
            weather_data = self._fetch_weather(lat, lon)
            if weather_data:
                conditions.wind_speed = weather_data.get("wind_speed")
                conditions.wind_direction = weather_data.get("wind_direction")
                conditions.temperature = weather_data.get("temperature")
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")

        self._cache = conditions
        return conditions

    def _fetch_marine(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch marine/wave data from Open-Meteo Marine API."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "wave_height",
                "wave_period",
                "wave_direction",
                "swell_wave_height",
                "swell_wave_period",
                "swell_wave_direction",
            ],
            "timezone": "auto",
        }

        response = requests.get(MARINE_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        current = data.get("current", {})

        logger.debug(f"Marine data: {current}")
        return current

    def _fetch_weather(self, lat: float, lon: float) -> Optional[dict]:
        """Fetch weather data from Open-Meteo Weather API."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "timezone": "auto",
        }

        response = requests.get(WEATHER_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        current = data.get("current", {})

        # Rename keys to match our format
        result = {
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
        }

        logger.debug(f"Weather data: {result}")
        return result

    @property
    def cached(self) -> Optional[SurfConditions]:
        """Get last fetched conditions."""
        return self._cache


def fetch_surf_conditions() -> SurfConditions:
    """Convenience function to fetch surf conditions."""
    fetcher = SurfDataFetcher()
    return fetcher.fetch()


if __name__ == "__main__":
    # Test the API
    logging.basicConfig(level=logging.DEBUG)

    conditions = fetch_surf_conditions()
    print("\n=== Surf Conditions ===")

    formatted = conditions.format_overlay()
    for key, value in formatted.items():
        if value:
            print(f"{key}: {value}")
