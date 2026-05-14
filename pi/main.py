#!/usr/bin/env python3
"""
Surf E-Ink Frame - Main Entry Point

Orchestrates the pipeline:
1. Fetches frames from beach camera
2. Crops and filters frames
3. Processes for E-Ink display
4. Serves via HTTP for ESP32

Usage:
    python main.py              # Run full service
    python main.py --once       # Fetch once and exit
    python main.py --server     # Run HTTP server only
"""

import argparse
import hashlib
import json
import logging
import random
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz
import schedule

from config import get_config
from fetcher import Fetcher
from cropper import Cropper
from filter import FrameFilter
from processor import Processor
from scorer import score_frame
from server import Server
from surf_data import SurfConditions, SurfDataFetcher, SurfPreferences

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("beachcam")


class BeachCamService:
    """Main service orchestrating all components."""

    def __init__(self, debug: bool = False):
        self.config = get_config()
        self.fetcher = Fetcher()
        self.cropper = Cropper()
        self.filter = FrameFilter()
        self.processor = Processor()
        self.server = Server(on_image_pulled=self._on_image_pulled, get_sleep_minutes=self._get_sleep_minutes, get_guest_info=self._get_guest_info)
        self.surf_data = SurfDataFetcher()

        self._running = False
        self._last_hash: Optional[str] = None
        self._debug = debug  # Skip time checks in debug mode
        self._sun_cache: Optional[dict] = None  # {"date": "2026-04-09", "sunrise": "06:03", "sunset": "19:20"}

        # Candidate tracking — cleared when ESP32 pulls /image or max age reached
        self._candidates: list = []  # [{"path": Path, "score": float, "camera": str}]
        self._candidates_since: datetime = datetime.now()
        self._max_candidates_age_hours = 3
        self.image_pulled = False  # Set by server when ESP32 pulls /image

        # Guest beach — once per day at a random time
        self._guest_today: Optional[dict] = None  # {"date": str, "trigger_minutes": int, "camera": dict}
        self._guest_used_today: Optional[str] = None  # date string when guest was shown
        self._guest_active: bool = False  # True while guest is being served (until ESP32 pulls)
        self._cycle_count: int = 0

        # Setup paths
        self.data_dir = Path(self.config.paths.get("data_dir", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir = self.data_dir / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        # Schedule guest beach for today
        self._schedule_guest()

    def fetch_and_process(self) -> bool:
        """
        Unified pipeline for every cycle:
        1. Determine source (main or guest camera)
        2. Fetch → Crop → Color correct → Filter → Score → Save candidate
        3. Pick best candidate → Process for E-Ink → Overlay → Save

        Returns:
            True if successful, False otherwise.
        """
        # Check if within active hours (skip in debug mode)
        if not self._debug and not self._is_active_time():
            logger.info("Outside active hours, skipping fetch")
            return False

        # Clear candidates if ESP32 pulled or max age reached
        age_hours = (datetime.now() - self._candidates_since).total_seconds() / 3600
        if self.image_pulled or age_hours >= self._max_candidates_age_hours:
            reason = "ESP32 pulled image" if self.image_pulled else f"max age ({self._max_candidates_age_hours}h)"
            self._clear_candidates(reason)

            if self.image_pulled:
                if self._guest_active:
                    # Guest was served — back to main
                    self._guest_active = False
                    self._guest_used_today = datetime.now().strftime("%Y-%m-%d")
                    logger.info("Guest beach served to ESP32, back to main camera")
                elif self._is_guest_cycle():
                    # Trigger time has passed — start guest mode now
                    self._guest_active = True
                    logger.info(f"Guest beach starting: {self._guest_today['camera']['name']}")

            self.image_pulled = False

        self._cycle_count += 1
        is_guest = self._guest_active

        if is_guest:
            camera = self._get_guest_camera()
            logger.info(f"*** Guest beach cycle: {camera['name']} ***")
        else:
            camera = None

        logger.info("Starting fetch cycle...")

        # --- Step 1: Fetch ---
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True

        if is_guest:
            fetch_result = self.fetcher.fetch_frame(camera)
        else:
            fetch_result = self.fetcher.fetch_with_fallback()

        if not fetch_result.success:
            logger.error(f"Fetch failed: {fetch_result.error}")
            return False

        logger.info(f"Fetched from: {fetch_result.camera_name}")

        # --- Step 2: Crop ---
        raw_img = Image.open(fetch_result.image_path)

        if is_guest:
            # Use guest camera's crop_box
            crop_box = camera.get("crop_box")
            cropped_img = raw_img.crop(tuple(crop_box)) if crop_box else raw_img
        else:
            # Use main camera cropper
            cropped_img = self.cropper.crop(
                fetch_result.image_path,
                camera_name=fetch_result.camera_name
            )
            if cropped_img is None:
                logger.error("Crop failed, using raw image")
                cropped_img = raw_img

        # --- Step 2b: Rotation (level tilted cameras) ---
        rotation = camera.get("rotation") if is_guest else None
        if not rotation:
            main_camera = self.config.cameras[0] if self.config.cameras else {}
            rotation = main_camera.get("rotation") if not is_guest else None
        if rotation:
            # Positive = counter-clockwise in PIL
            cropped_img = cropped_img.rotate(rotation, expand=True, fillcolor=(0, 0, 0))
            # Crop out black borders — margin ~1.5x the angle percentage
            w, h = cropped_img.size
            margin = int(max(w, h) * abs(rotation) * 1.5 / 100)
            cropped_img = cropped_img.crop((margin, margin, w - margin, h - margin))
            logger.debug(f"Rotated {rotation}° and trimmed borders")
            logger.debug(f"Rotated {rotation}° and trimmed borders")

        # --- Step 3: Filter ---
        filter_result = self.filter.filter(cropped_img)
        if not filter_result.is_valid:
            logger.warning(f"Frame rejected by filter: {filter_result.reason}")

        # --- Step 5: Score (profile depends on camera) ---
        if is_guest:
            scoring_profile = camera.get("scoring_profile", "beach")
        else:
            main_camera = self.config.cameras[0] if self.config.cameras else {}
            scoring_profile = main_camera.get("scoring_profile", "jaffa")
        score = score_frame(cropped_img, profile=scoring_profile)

        # --- Step 6: Save candidate ---
        candidate_path = self.candidates_dir / f"candidate_{len(self._candidates):03d}.png"
        cropped_img.save(candidate_path)

        self._candidates.append({
            "path": candidate_path,
            "score": score,
            "camera": fetch_result.camera_name,
            "hash": filter_result.image_hash if filter_result.is_valid else None,
            "guest": is_guest,
            "guest_camera": camera if is_guest else None,
        })

        logger.info(
            f"Candidate #{len(self._candidates)} scored {score:.3f} "
            f"(best so far: {self._best_score():.3f})"
        )

        # --- Step 7: Pick best and process ---
        best = self._pick_best()
        if best is None:
            return False

        best_img = Image.open(best["path"])

        # Check if best image changed from what we last processed
        if best["hash"] == self._last_hash:
            logger.info("Best candidate unchanged, skipping reprocessing")
            return True

        # Get weather for the right location
        if best.get("guest") and best.get("guest_camera"):
            weather_data = self._get_guest_weather(best["guest_camera"])
            color_profile = best["guest_camera"].get("scoring_profile")
        else:
            weather_data = self._get_weather_data()
            main_camera = self.config.cameras[0] if self.config.cameras else {}
            color_profile = main_camera.get("scoring_profile")

        # --- Step 8: Process for E-Ink (resize, preprocess, dither, overlay) ---
        processed_img = self.processor.process(best_img, weather_data, color_profile=color_profile)

        # --- Step 9: Save ---
        output_path = self.data_dir / "current.bmp"
        processed_img.save(output_path)
        logger.info(f"Saved best candidate (score={best['score']:.3f}): {output_path}")

        metadata = {
            "hash": best.get("hash", ""),
            "timestamp": datetime.now().isoformat(),
            "camera": best["camera"],
            "weather": weather_data,
            "score": best["score"],
            "candidates_count": len(self._candidates),
            "guest": best.get("guest", False),
        }
        metadata_path = self.data_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self._last_hash = best.get("hash")

        logger.info("Pipeline complete!")
        return True

    def _schedule_guest(self):
        """Pick a random trigger time for today's guest beach."""
        guest_config = self.config.get("guest_beaches", default={})
        if not guest_config.get("enabled", False):
            logger.info("Guest beaches disabled")
            return

        cameras = [c for c in guest_config.get("cameras", []) if c.get("url")]
        if not cameras:
            logger.info("No guest cameras configured")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        if self._guest_today and self._guest_today.get("date") == today:
            return  # Already scheduled

        active_hours = self.config.timing.get("active_hours", {})
        sun_times = self._get_sun_times()
        start_str = sun_times.get("sunrise") or active_hours.get("start", "06:00")
        end_str = sun_times.get("sunset") or active_hours.get("end", "20:00")

        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        esp_interval = self.config.timing.get("esp_sleep_minutes", 30)

        wake_times = list(range(start_minutes, end_minutes, esp_interval))
        if not wake_times:
            return

        trigger_time = random.choice(wake_times)
        self._guest_today = {
            "date": today,
            "trigger_minutes": trigger_time,
            "camera": None,
        }
        logger.info(
            f"Guest beach scheduled at {trigger_time // 60:02d}:{trigger_time % 60:02d} "
            f"(available: {', '.join(c['name'] for c in cameras)})"
        )

    def _is_guest_cycle(self) -> bool:
        """Check if this cycle should show a guest beach."""
        guest_config = self.config.get("guest_beaches", default={})
        if not guest_config.get("enabled", False):
            return False

        cameras = [c for c in guest_config.get("cameras", []) if c.get("url")]
        if not cameras:
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        if self._guest_used_today == today:
            return False

        # Ensure scheduled
        self._schedule_guest()

        # Check if we've passed the trigger time
        active_hours = self.config.timing.get("active_hours", {})
        tz_name = active_hours.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        now_minutes = now.hour * 60 + now.minute
        trigger = self._guest_today["trigger_minutes"]

        if now_minutes < trigger:
            return False

        # Trigger time passed — pick a daytime camera now
        daytime_cameras = [c for c in cameras if self._is_daytime_at(c)]
        if not daytime_cameras:
            logger.info("Guest trigger time passed but no cameras in daytime, skipping")
            self._guest_used_today = today
            return False

        self._guest_today["camera"] = random.choice(daytime_cameras)
        logger.info(
            f"Guest beach picked: {self._guest_today['camera']['name']} "
            f"(local time there: {self._local_hour_at(self._guest_today['camera'])}:00)"
        )
        return True

    def _is_daytime_at(self, camera: dict) -> bool:
        """Check if it's daytime (7:00-18:00) at the camera's location."""
        hour = self._local_hour_at(camera)
        return 7 <= hour <= 18

    def _local_hour_at(self, camera: dict) -> int:
        """Get current local hour at a camera's timezone."""
        tz_name = camera.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        return datetime.now(tz).hour

    def _get_guest_camera(self) -> dict:
        """Get the guest camera config with dynamic URL resolved."""
        camera = dict(self._guest_today["camera"])
        if camera.get("dynamic_url"):
            tz_name = camera.get("timezone", "UTC")
            tz = pytz.timezone(tz_name)
            local_hour = datetime.now(tz).hour
            camera["url"] = camera["url"].format(hour=local_hour)
            logger.debug(f"Dynamic URL resolved: {camera['url']}")
        return camera

    def _pick_best(self) -> Optional[dict]:
        """Pick the highest-scoring candidate."""
        if not self._candidates:
            return None
        return max(self._candidates, key=lambda c: c["score"])

    def _best_score(self) -> float:
        """Get the best score so far."""
        if not self._candidates:
            return 0.0
        return max(c["score"] for c in self._candidates)

    def _clear_candidates(self, reason: str = ""):
        """Remove all candidate files and reset the list."""
        for candidate in self._candidates:
            try:
                Path(candidate["path"]).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete candidate: {e}")
        self._candidates.clear()
        self._candidates_since = datetime.now()
        logger.info(f"Candidates cleared ({reason})")

    def _get_guest_info(self) -> dict:
        """Return today's guest beach schedule info."""
        if not self._guest_today:
            return {"status": "no guest scheduled"}

        trigger = self._guest_today.get("trigger_minutes", 0)
        trigger_time = f"{trigger // 60:02d}:{trigger % 60:02d}"

        camera = self._guest_today.get("camera")
        camera_name = camera["name"] if camera else "not yet picked"

        return {
            "date": self._guest_today.get("date"),
            "trigger_time": trigger_time,
            "camera": camera_name,
            "active": self._guest_active,
            "used_today": self._guest_used_today == datetime.now().strftime("%Y-%m-%d"),
        }

    def _on_image_pulled(self):
        """Called by server when ESP32 pulls /image."""
        self.image_pulled = True

    def _get_sleep_minutes(self) -> int:
        """Calculate how long ESP32 should sleep.

        During active hours: normal interval (e.g. 30 min).
        At night: minutes until next sunrise.
        """
        default = self.config.timing.get("esp_sleep_minutes", 30)

        if self._is_active_time():
            logger.debug(f"ESP32 sleep: {default}min (active hours)")
            return default

        # Night time — calculate minutes until sunrise
        active_hours = self.config.timing.get("active_hours", {})
        tz_name = active_hours.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)

        sun_times = self._get_sun_times()
        sunrise_str = sun_times.get("sunrise") or active_hours.get("start", "06:00")
        sunrise_hour, sunrise_min = map(int, sunrise_str.split(":"))

        # Next sunrise is tomorrow if we're past it today
        next_sunrise = now.replace(hour=sunrise_hour, minute=sunrise_min, second=0)
        if next_sunrise <= now:
            next_sunrise += timedelta(days=1)

        minutes = int((next_sunrise - now).total_seconds() / 60)
        logger.info(f"ESP32 night sleep: {minutes}min (until sunrise at {sunrise_str})")
        return max(minutes, default)  # Never sleep less than default

    def _is_active_time(self) -> bool:
        """Check if current time is within active hours (sunrise to sunset)."""
        active_hours = self.config.timing.get("active_hours", {})
        if not active_hours.get("enabled", True):
            return True

        tz_name = active_hours.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)

        sun_times = self._get_sun_times()
        start_str = sun_times.get("sunrise") or active_hours.get("start", "06:00")
        end_str = sun_times.get("sunset") or active_hours.get("end", "20:00")

        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))

        start_time = now.replace(hour=start_hour, minute=start_min, second=0)
        end_time = now.replace(hour=end_hour, minute=end_min, second=0)

        return start_time <= now <= end_time

    def _get_sun_times(self) -> dict:
        """Fetch today's sunrise/sunset from Open-Meteo. Cached per day."""
        today = datetime.now().strftime("%Y-%m-%d")

        if self._sun_cache and self._sun_cache["date"] == today:
            return self._sun_cache

        weather_config = self.config.get("weather", default={})
        location = weather_config.get("location", {})
        lat = location.get("lat", 32.0853)
        lon = location.get("lon", 34.7818)

        try:
            import requests
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "sunrise,sunset",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # Sunrise: 15 min earlier to catch first light
            sunrise_iso = data["daily"]["sunrise"][0]
            sunrise_dt = datetime.strptime(sunrise_iso, "%Y-%m-%dT%H:%M")
            sunrise_dt -= timedelta(minutes=15)
            sunrise_time = sunrise_dt.strftime("%H:%M")

            # Sunset: 15 min later to catch golden hour
            sunset_iso = data["daily"]["sunset"][0]
            sunset_dt = datetime.strptime(sunset_iso, "%Y-%m-%dT%H:%M")
            sunset_dt += timedelta(minutes=15)
            sunset_time = sunset_dt.strftime("%H:%M")

            self._sun_cache = {"date": today, "sunrise": sunrise_time, "sunset": sunset_time}
            logger.info(
                f"Sun times: sunrise {sunrise_iso.split('T')[1][:5]} (active from {sunrise_time}), "
                f"sunset {sunset_iso.split('T')[1][:5]} (active until {sunset_time})"
            )
            return self._sun_cache
        except Exception as e:
            logger.warning(f"Failed to fetch sun times: {e}")
            return {}

    def _get_weather_data(self) -> Optional[dict]:
        """Fetch surf and weather data for overlay."""
        weather_config = self.config.get("weather", default={})
        if not weather_config.get("enabled", False):
            return {
                "location": weather_config.get("location", {}).get("name", "Beach"),
            }

        try:
            # Load surf preferences from config
            prefs_config = self.config.get("surf_preferences", default={})
            prefs = SurfPreferences(
                min_wave_cm=prefs_config.get("min_wave_cm", 60),
                max_wave_cm=prefs_config.get("max_wave_cm", 110),
                max_wind_kmh=prefs_config.get("max_wind_kmh", 25),
            )

            conditions = self.surf_data.fetch()
            rating = conditions.calculate_quality(prefs)
            logger.info(f"Surf data: {conditions.wave_height}m waves, {conditions.wind_speed} km/h wind, rating: {rating}/10")
            return conditions.format_overlay(prefs)
        except Exception as e:
            logger.error(f"Failed to fetch surf data: {e}")
            return {
                "location": weather_config.get("location", {}).get("name", "Tel Aviv"),
            }

    def _get_guest_weather(self, camera: dict) -> dict:
        """Fetch weather/surf data for a guest beach location."""
        location = camera.get("location", {})
        lat = location.get("lat")
        lon = location.get("lon")
        name = location.get("name", camera.get("name", "Guest"))

        if not lat or not lon:
            return {"location": name}

        try:
            # Create a temporary fetcher for the guest location
            import requests

            # Marine data
            marine_resp = requests.get(
                "https://marine-api.open-meteo.com/v1/marine",
                params={
                    "latitude": lat, "longitude": lon,
                    "current": ["wave_height", "wave_period", "wave_direction"],
                    "timezone": "auto",
                },
                timeout=10,
            )
            marine = marine_resp.json().get("current", {}) if marine_resp.ok else {}

            # Weather data
            weather_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "current": ["wind_speed_10m", "wind_direction_10m"],
                    "timezone": "auto",
                },
                timeout=10,
            )
            weather = weather_resp.json().get("current", {}) if weather_resp.ok else {}

            conditions = SurfConditions(
                location=name,
                wave_height=marine.get("wave_height"),
                wave_period=marine.get("wave_period"),
                wave_direction=marine.get("wave_direction"),
                wind_speed=weather.get("wind_speed_10m"),
                wind_direction=weather.get("wind_direction_10m"),
            )

            prefs_config = self.config.get("surf_preferences", default={})
            prefs = SurfPreferences(
                min_wave_cm=prefs_config.get("min_wave_cm", 60),
                max_wave_cm=prefs_config.get("max_wave_cm", 110),
                max_wind_kmh=prefs_config.get("max_wind_kmh", 25),
            )

            rating = conditions.calculate_quality(prefs)
            logger.info(f"Guest surf data ({name}): {conditions.wave_height}m waves, {conditions.wind_speed} km/h wind, rating: {rating}/10")
            overlay = conditions.format_overlay(prefs)
            overlay["timezone"] = camera.get("timezone")
            return overlay
        except Exception as e:
            logger.error(f"Failed to fetch guest weather for {name}: {e}")
            return {"location": name}

    def run_scheduler(self):
        """Run the fetch/process cycle on a schedule.

        During active hours: fetch every interval.
        At night: sleep until sunrise.
        """
        interval = self.config.timing.get("fetch_interval_minutes", 5)

        # Run immediately on start
        self.fetch_and_process()

        # Schedule periodic runs
        schedule.every(interval).minutes.do(self.fetch_and_process)
        logger.info(f"Scheduled fetch every {interval} minutes")

        self._running = True
        while self._running:
            if not self._debug and not self._is_active_time():
                self._sleep_until_sunrise()
            schedule.run_pending()
            time.sleep(1)

    def _sleep_until_sunrise(self):
        """Sleep until next sunrise instead of polling every minute at night."""
        active_hours = self.config.timing.get("active_hours", {})
        tz_name = active_hours.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)

        sun_times = self._get_sun_times()
        sunrise_str = sun_times.get("sunrise") or active_hours.get("start", "06:00")
        sunrise_hour, sunrise_min = map(int, sunrise_str.split(":"))

        next_sunrise = now.replace(hour=sunrise_hour, minute=sunrise_min, second=0)
        if next_sunrise <= now:
            next_sunrise += timedelta(days=1)

        sleep_seconds = int((next_sunrise - now).total_seconds())
        logger.info(f"Night time — sleeping until {sunrise_str} ({sleep_seconds // 60} minutes)")
        time.sleep(sleep_seconds)

    def run(self):
        """Start the full service (scheduler + HTTP server)."""
        logger.info("Starting BeachCam service...")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        # Start HTTP server in background
        self.server.run(threaded=True)

        # Run scheduler in main thread
        self.run_scheduler()

    def _shutdown(self, signum, frame):
        """Handle shutdown signal."""
        logger.info("Shutting down...")
        self._running = False
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Surf E-Ink Frame - Beach Camera Display Service"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch and process once, then exit"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run HTTP server only (no fetching)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file"
    )
    parser.add_argument(
        "--guest",
        type=str,
        help="Force a guest beach fetch by name (e.g. --guest Baleal)"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.config:
        from config import get_config
        get_config(args.config)

    service = BeachCamService(debug=args.debug)

    if args.guest:
        # Force a guest beach fetch
        guest_config = service.config.get("guest_beaches", default={})
        cameras = guest_config.get("cameras", [])
        match = next((c for c in cameras if c["name"].lower() == args.guest.lower()), None)
        if match is None:
            names = [c["name"] for c in cameras]
            print(f"Guest beach '{args.guest}' not found. Available: {', '.join(names)}")
            sys.exit(1)
        service._guest_today = {"date": datetime.now().strftime("%Y-%m-%d"), "camera": match}
        service._guest_active = True
        success = service.fetch_and_process()
        sys.exit(0 if success else 1)

    elif args.once:
        # Single fetch
        success = service.fetch_and_process()
        sys.exit(0 if success else 1)

    elif args.server:
        # Server only
        service.server.run(threaded=False)

    else:
        # Full service
        service.run()


if __name__ == "__main__":
    main()
