"""
Surf data module - fetches wave and weather data from Open-Meteo API.
Free API, no key required.

Data sources:
- Marine API: wave height, swell, period
- Weather API: wind, temperature
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

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

        wave_cm = self.wave_height * 100  # Convert to cm

        # --- Wave height: base score 0-7 ---
        # Linear triangle: peak at 90cm, zero at 40cm and 120cm
        peak_cm = 90
        low_cm = 40   # Below this = flat
        high_cm = 120  # Above this = too big

        if wave_cm < low_cm:
            height_score = 0.0
        elif wave_cm <= peak_cm:
            height_score = 7.0 * (wave_cm - low_cm) / (peak_cm - low_cm)
        elif wave_cm <= high_cm:
            height_score = 7.0 * (high_cm - wave_cm) / (high_cm - peak_cm)
        else:
            height_score = 0.0

        # --- Wave period: 0-3 points ---
        # Mediterranean tuned: 10s+ is great, 4s is chop
        if self.wave_period and self.wave_period >= 4:
            period_score = min(3.0, (self.wave_period - 4) / 6.0 * 3.0)
        else:
            period_score = 0.0

        base_score = height_score + period_score

        # --- Wind: penalty only (subtract 0-3) ---
        wind_penalty = 0.0
        if self.wind_speed is not None:
            # Classify direction
            wind_type = "cross"
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
                wind_penalty = 0.0  # Glass, no penalty
            elif self.wind_speed <= 10:
                if wind_type == "onshore":
                    wind_penalty = 0.5
                elif wind_type == "cross":
                    wind_penalty = 0.25
                # Offshore: 0
            elif self.wind_speed <= 20:
                if wind_type == "onshore":
                    wind_penalty = 2.0
                elif wind_type == "cross":
                    wind_penalty = 1.0
                else:
                    wind_penalty = 0.5  # Strong offshore still not perfect
            else:
                # 20+ km/h
                if wind_type == "onshore":
                    wind_penalty = 3.0
                elif wind_type == "cross":
                    wind_penalty = 2.0
                else:
                    wind_penalty = 1.0

        score = base_score - wind_penalty

        # Round and clamp to 0-10
        rating = max(0, min(10, round(score)))
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


@dataclass
class ForecastHour:
    """One hour of tomorrow's forecast, already scored."""
    hour: int
    rating: int
    wave: float
    period: float
    wind: float
    wind_direction: int


@dataclass
class DayForecast:
    """A scored day, plus the daylight bounds the best window is chosen within."""
    date: str                       # ISO date
    sunrise: str                    # "HH:MM" local
    sunset: str                     # "HH:MM" local
    hours: List[ForecastHour]

    def best_window(self, length: int = 2) -> Optional[Tuple[float, int, int]]:
        """
        (average rating, start hour, end hour) for the best contiguous DAYLIGHT run.

        Daylight-only is not a nicety. The wind usually drops after sunset, so the
        rating function happily peaks in the dark — an early version of this
        recommended a 19:00-21:00 session on a day whose sunset was 19:01.
        Returns None when nothing scores above `FLAT_RATING`.
        """
        lo, hi = int(self.sunrise[:2]), int(self.sunset[:2])
        day = [h for h in self.hours if lo <= h.hour < hi]
        best = None
        for n in (3, length):
            for i in range(len(day) - n + 1):
                seg = day[i:i + n]
                if seg[-1].hour - seg[0].hour != n - 1:
                    continue        # non-contiguous (a gap in the API data)
                avg = sum(h.rating for h in seg) / n
                if best is None or avg > best[0]:
                    best = (avg, seg[0].hour, seg[-1].hour + 1)
        return best

    def window_conditions(self, a: int, b: int) -> dict:
        """
        Mean wave/period/wind ACROSS the window, not the window's best hour.

        The card shows these directly beneath "06:00 through 08:00", so they have
        to describe those two hours. Reporting the peak hour there reads as the
        window's conditions while quietly flattering the forecast.
        """
        seg = [h for h in self.hours if a <= h.hour < b] or self.hours
        n = len(seg)
        return {
            "wave": sum(h.wave for h in seg) / n,
            "period": sum(h.period for h in seg) / n,
            "wind": sum(h.wind for h in seg) / n,
        }


# Below this average rating a day is reported as not worth going out for.
FLAT_RATING = 3.0

# Hours sampled. Outside these the panel is showing a night frame anyway.
FORECAST_FIRST_HOUR = 5
FORECAST_LAST_HOUR = 20


class ForecastFetcher:
    """
    Tomorrow's hourly forecast, scored with the same calculate_quality() the
    live overlay uses, so the card and the badge can never disagree.

    Cached by target date: the Pi renders a frame every few minutes through the
    whole sunset window, and this must not become one API round-trip per frame.
    """

    def __init__(self, prefs: SurfPreferences = None):
        self.prefs = prefs or SurfPreferences()
        self._cache: Optional[DayForecast] = None
        self._cache_date: Optional[str] = None

    def fetch(self, lat: float, lon: float, day_offset: int = 1,
              force: bool = False) -> Optional[DayForecast]:
        target = (datetime.now().date() + timedelta(days=day_offset)).isoformat()
        if not force and self._cache is not None and self._cache_date == target:
            return self._cache
        try:
            fc = self._fetch_uncached(lat, lon, target, day_offset)
        except Exception as e:
            logger.error(f"Forecast fetch failed: {e}")
            return self._cache        # stale beats blank on the goodnight frame
        if fc:
            self._cache, self._cache_date = fc, target
        return fc

    def _fetch_uncached(self, lat, lon, target, day_offset) -> Optional[DayForecast]:
        days = day_offset + 1
        marine = requests.get(MARINE_API, params={
            "latitude": lat, "longitude": lon,
            "hourly": ["wave_height", "wave_period"],
            "timezone": "auto", "forecast_days": days,
        }, timeout=15)
        marine.raise_for_status()
        weather = requests.get(WEATHER_API, params={
            "latitude": lat, "longitude": lon,
            "hourly": ["wind_speed_10m", "wind_direction_10m"],
            "daily": ["sunrise", "sunset"],
            "timezone": "auto", "forecast_days": days,
        }, timeout=15)
        weather.raise_for_status()

        mh = marine.json().get("hourly", {})
        wj = weather.json()
        wh, wd = wj.get("hourly", {}), wj.get("daily", {})
        if not mh.get("time") or not wd.get("sunrise"):
            logger.warning("Forecast response missing hourly/daily blocks")
            return None

        hours = []
        for i, t in enumerate(mh["time"]):
            if not t.startswith(target):
                continue
            h = int(t[11:13])
            if not (FORECAST_FIRST_HOUR <= h <= FORECAST_LAST_HOUR):
                continue
            wave, period = mh["wave_height"][i], mh["wave_period"][i]
            speed, direction = wh["wind_speed_10m"][i], wh["wind_direction_10m"][i]
            if wave is None or speed is None:
                continue
            c = SurfConditions(wave_height=wave, wave_period=period,
                               wind_speed=speed, wind_direction=direction)
            hours.append(ForecastHour(
                hour=h, rating=c.calculate_quality(self.prefs), wave=wave,
                period=period or 0.0, wind=speed, wind_direction=direction or 0,
            ))
        if not hours:
            logger.warning(f"No forecast hours parsed for {target}")
            return None

        # The daily arrays are indexed from today, so day_offset indexes tomorrow.
        try:
            sunrise = wd["sunrise"][day_offset][11:16]
            sunset = wd["sunset"][day_offset][11:16]
        except (IndexError, TypeError):
            logger.warning("Forecast missing sunrise/sunset for target day")
            return None

        logger.info(f"Forecast {target}: {len(hours)} hours, "
                    f"sunrise {sunrise}, sunset {sunset}")
        return DayForecast(date=target, sunrise=sunrise, sunset=sunset, hours=hours)


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
