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
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz
import schedule

from config import get_config
from fetcher import Fetcher
from cropper import Cropper
from filter import FrameFilter
from processor import Processor
from server import Server
from surf_data import SurfDataFetcher, SurfPreferences

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
        self.server = Server()
        self.surf_data = SurfDataFetcher()

        self._running = False
        self._last_hash: Optional[str] = None
        self._debug = debug  # Skip time checks in debug mode

        # Setup paths
        self.data_dir = Path(self.config.paths.get("data_dir", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_process(self) -> bool:
        """
        Run the full pipeline once.

        Returns:
            True if successful, False otherwise.
        """
        # Check if within active hours (skip in debug mode)
        if not self._debug and not self._is_active_time():
            logger.info("Outside active hours, skipping fetch")
            return False

        logger.info("Starting fetch cycle...")

        # Step 1: Fetch frame
        fetch_result = self.fetcher.fetch_with_fallback()
        if not fetch_result.success:
            logger.error(f"Fetch failed: {fetch_result.error}")
            return False

        logger.info(f"Fetched from: {fetch_result.camera_name}")

        # Step 2: Crop
        from PIL import Image
        raw_img = Image.open(fetch_result.image_path)
        cropped_img = self.cropper.crop(
            fetch_result.image_path,
            camera_name=fetch_result.camera_name
        )

        if cropped_img is None:
            logger.error("Crop failed, using raw image")
            cropped_img = raw_img

        # Step 3: Filter (ad detection)
        filter_result = self.filter.filter(cropped_img)
        if not filter_result.is_valid:
            logger.warning(f"Frame rejected: {filter_result.reason}")
            return False

        logger.info(f"Frame accepted, hash: {filter_result.image_hash}")

        # Check if image changed
        if filter_result.image_hash == self._last_hash:
            logger.info("Image unchanged, skipping processing")
            return True

        # Step 4: Process for E-Ink
        weather_data = self._get_weather_data()
        processed_img = self.processor.process(cropped_img, weather_data)

        # Save processed image
        output_path = self.data_dir / "current.bmp"
        processed_img.save(output_path)
        logger.info(f"Saved: {output_path}")

        # Save metadata
        metadata = {
            "hash": filter_result.image_hash,
            "timestamp": datetime.now().isoformat(),
            "camera": fetch_result.camera_name,
            "weather": weather_data,
        }
        metadata_path = self.data_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self._last_hash = filter_result.image_hash
        logger.info("Pipeline complete!")
        return True

    def _is_active_time(self) -> bool:
        """Check if current time is within active hours."""
        active_hours = self.config.timing.get("active_hours", {})
        if not active_hours.get("enabled", True):
            return True

        tz_name = active_hours.get("timezone", "UTC")
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)

        start_str = active_hours.get("start", "00:00")
        end_str = active_hours.get("end", "23:59")

        start_hour, start_min = map(int, start_str.split(":"))
        end_hour, end_min = map(int, end_str.split(":"))

        start_time = now.replace(hour=start_hour, minute=start_min, second=0)
        end_time = now.replace(hour=end_hour, minute=end_min, second=0)

        return start_time <= now <= end_time

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

    def run_scheduler(self):
        """Run the fetch/process cycle on a schedule."""
        interval = self.config.timing.get("fetch_interval_minutes", 5)

        # Run immediately on start
        self.fetch_and_process()

        # Schedule periodic runs
        schedule.every(interval).minutes.do(self.fetch_and_process)
        logger.info(f"Scheduled fetch every {interval} minutes")

        self._running = True
        while self._running:
            schedule.run_pending()
            time.sleep(1)

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
        self.fetcher.close()
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

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.config:
        from config import get_config
        get_config(args.config)

    service = BeachCamService(debug=args.debug)

    if args.once:
        # Single fetch
        success = service.fetch_and_process()
        service.fetcher.close()
        sys.exit(0 if success else 1)

    elif args.server:
        # Server only
        service.server.run(threaded=False)

    else:
        # Full service
        service.run()


if __name__ == "__main__":
    main()
