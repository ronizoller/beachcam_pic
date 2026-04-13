"""
Fetcher module - captures frames from beach cameras.
Supports:
- Direct snapshot URLs (simple HTTP GET)
- WebRTC streams (via Playwright headless browser)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from playwright.sync_api import sync_playwright, Browser, Page

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a frame fetch attempt."""
    success: bool
    image_path: Optional[str] = None
    camera_name: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


class Fetcher:
    """Fetches frames from beach cameras using headless browser."""

    def __init__(self):
        self.config = get_config()
        self._browser: Optional[Browser] = None
        self._playwright = None

    def _ensure_browser(self):
        """Start browser if not already running."""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
            logger.info("Browser started")

    def close(self):
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
            logger.info("Browser closed")

    def fetch_frame(self, camera: dict = None) -> FetchResult:
        """
        Fetch a single frame from a camera.

        Args:
            camera: Camera config dict. If None, uses first enabled camera.

        Returns:
            FetchResult with success status and image path.
        """
        if camera is None:
            cameras = self.config.cameras
            if not cameras:
                return FetchResult(success=False, error="No cameras configured")
            camera = cameras[0]

        camera_type = camera.get("type", "webrtc")

        # Route to appropriate fetcher based on camera type
        if camera_type == "snapshot":
            return self._fetch_snapshot(camera)
        elif camera_type == "hls":
            return self._fetch_hls(camera)
        else:
            return self._fetch_webrtc(camera)

    def _fetch_snapshot(self, camera: dict) -> FetchResult:
        """Fetch a direct image snapshot via HTTP GET."""
        camera_name = camera.get("name", "Unknown")
        url = camera.get("url")

        if not url:
            return FetchResult(success=False, error=f"No URL for camera {camera_name}")

        logger.info(f"Fetching snapshot from: {camera_name}")

        try:
            # Simple HTTP GET for the image
            response = requests.get(url, timeout=60, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()

            # Check if response is an image
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                return FetchResult(
                    success=False,
                    camera_name=camera_name,
                    error=f"Not an image: {content_type}"
                )

            # Save the image
            output_dir = Path(self.config.paths.get("data_dir", "./data"))
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now()
            raw_path = output_dir / "current_raw.png"

            with open(raw_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Snapshot saved: {raw_path} ({len(response.content)} bytes)")

            return FetchResult(
                success=True,
                image_path=str(raw_path),
                camera_name=camera_name,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Failed to fetch snapshot from {camera_name}: {e}")
            return FetchResult(success=False, camera_name=camera_name, error=str(e))

    def _fetch_hls(self, camera: dict) -> FetchResult:
        """Extract a single frame from an HLS video stream using ffmpeg."""
        import subprocess

        camera_name = camera.get("name", "Unknown")
        url = camera.get("url")

        if not url:
            return FetchResult(success=False, error=f"No URL for camera {camera_name}")

        logger.info(f"Fetching HLS frame from: {camera_name}")

        try:
            output_dir = Path(self.config.paths.get("data_dir", "./data"))
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now()
            raw_path = output_dir / "current_raw.png"

            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", url,
                    "-frames:v", "1",
                    "-q:v", "2",
                    "-update", "1",
                    str(raw_path),
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0 or not raw_path.exists():
                error = result.stderr.decode()[-200:] if result.stderr else "Unknown error"
                logger.error(f"ffmpeg failed: {error}")
                return FetchResult(success=False, camera_name=camera_name, error=f"ffmpeg failed: {error}")

            logger.info(f"HLS frame saved: {raw_path}")

            return FetchResult(
                success=True,
                image_path=str(raw_path),
                camera_name=camera_name,
                timestamp=timestamp,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timed out for {camera_name}")
            return FetchResult(success=False, camera_name=camera_name, error="ffmpeg timeout")
        except FileNotFoundError:
            logger.error("ffmpeg not found — install with: sudo apt install ffmpeg")
            return FetchResult(success=False, camera_name=camera_name, error="ffmpeg not installed")
        except Exception as e:
            logger.error(f"Failed to fetch HLS from {camera_name}: {e}")
            return FetchResult(success=False, camera_name=camera_name, error=str(e))

    def _fetch_webrtc(self, camera: dict) -> FetchResult:
        """Fetch a frame from WebRTC stream using headless browser."""
        camera_name = camera.get("name", "Unknown")
        url = camera.get("url")
        wait_seconds = camera.get("wait_seconds", 5)

        if not url:
            return FetchResult(success=False, error=f"No URL for camera {camera_name}")

        logger.info(f"Fetching WebRTC frame from: {camera_name}")

        try:
            self._ensure_browser()
            page = self._browser.new_page(
                viewport={"width": 1920, "height": 1080}
            )

            # Navigate to camera page
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for video stream to load
            logger.debug(f"Waiting {wait_seconds}s for stream to load...")
            page.wait_for_timeout(wait_seconds * 1000)

            # Try to find and wait for video/iframe element
            self._wait_for_video(page)

            # Take screenshot
            output_dir = Path(self.config.paths.get("data_dir", "./data"))
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now()
            raw_path = output_dir / "current_raw.png"

            page.screenshot(path=str(raw_path), full_page=False)
            logger.info(f"Screenshot saved: {raw_path}")

            page.close()

            return FetchResult(
                success=True,
                image_path=str(raw_path),
                camera_name=camera_name,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Failed to fetch from {camera_name}: {e}")
            return FetchResult(success=False, camera_name=camera_name, error=str(e))

    def _wait_for_video(self, page: Page):
        """Wait for video element to be visible and playing."""
        try:
            # Try to find video element (direct or in iframe)
            video_selectors = [
                "video",
                "iframe",
                "#cam",
                ".video-container",
                "canvas",
            ]
            for selector in video_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=5000)
                    if element:
                        logger.debug(f"Found video element: {selector}")
                        # Wait a bit more for video to actually play
                        page.wait_for_timeout(2000)
                        return
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not find video element: {e}")

    def fetch_with_fallback(self) -> FetchResult:
        """
        Try to fetch from cameras in priority order.
        Falls back to next camera if primary fails.
        """
        cameras = self.config.cameras
        max_retries = self.config.timing.get("max_retries", 3)

        for camera in cameras:
            for attempt in range(max_retries):
                result = self.fetch_frame(camera)
                if result.success:
                    return result
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {camera.get('name')}"
                )

        return FetchResult(success=False, error="All cameras failed")


# Convenience function for one-shot fetching
def fetch_frame() -> FetchResult:
    """Fetch a single frame from the configured camera."""
    fetcher = Fetcher()
    try:
        return fetcher.fetch_with_fallback()
    finally:
        fetcher.close()


if __name__ == "__main__":
    # Test fetcher
    logging.basicConfig(level=logging.DEBUG)
    result = fetch_frame()
    print(f"Success: {result.success}")
    print(f"Image: {result.image_path}")
    if result.error:
        print(f"Error: {result.error}")
