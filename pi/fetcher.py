"""
Fetcher module - captures frames from beach cameras.
Supports:
- Direct snapshot URLs (simple HTTP GET)
- HLS streams (via ffmpeg frame grab)
- YouTube live streams (HLS extraction + thumbnail fallback)
- EarthCam streams (HLS extraction via ffmpeg)
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

import requests

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
    """Fetches frames from beach cameras."""

    def __init__(self):
        self.config = get_config()

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

        camera_type = camera.get("type", "snapshot")

        # Route to appropriate fetcher based on camera type
        if camera_type == "snapshot":
            return self._fetch_snapshot(camera)
        elif camera_type == "hls":
            return self._fetch_hls(camera)
        elif camera_type == "youtube_live":
            return self._fetch_youtube_live(camera)
        elif camera_type == "earthcam":
            return self._fetch_earthcam(camera)
        else:
            return FetchResult(
                success=False,
                camera_name=camera.get("name"),
                error=f"Unknown camera type: {camera_type}",
            )

    def _fetch_snapshot(self, camera: dict) -> FetchResult:
        """Fetch a direct image snapshot via HTTP GET."""
        camera_name = camera.get("name", "Unknown")
        url = camera.get("url")

        if not url:
            return FetchResult(success=False, error=f"No URL for camera {camera_name}")

        logger.info(f"Fetching snapshot from: {camera_name}")

        try:
            # Add cache-busting param to bypass CDN caches (e.g. Cloudflare)
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            params["_t"] = [str(int(time.time()))]
            cache_busted_url = urlunparse(parsed._replace(
                query=urlencode(params, doseq=True)
            ))

            # Simple HTTP GET for the image
            response = requests.get(cache_busted_url, timeout=60, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cache-Control": "no-cache",
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

    def _fetch_youtube_live(self, camera: dict) -> FetchResult:
        """
        Fetch a frame from a YouTube live stream.

        Two-phase approach optimised for Raspberry Pi Zero 2 W:
          1. PRIMARY: Extract HLS manifest URL from YouTube page HTML
             (the hlsManifestUrl field in the embedded JSON), then grab
             one frame with ffmpeg -- gives full-resolution live video.
          2. FALLBACK: Download the live thumbnail from i.ytimg.com which
             YouTube updates roughly every 30 s.  Lower resolution
             (1280x720) but needs only a single HTTP GET.

        Config fields:
          url  – YouTube video URL, e.g. https://www.youtube.com/watch?v=XXXX
          video_id – (optional) if set, used for the thumbnail fallback
                     without needing to parse the URL.
          channel_id – (optional) resolve the channel's CURRENT live video on
                     every fetch. For cams that restart their stream often
                     (Khao Lak's Valhalla cam had 6 video ids in one week),
                     where a stored id goes dead within days.
        """
        import re as _re
        import subprocess

        camera_name = camera.get("name", "Unknown")
        url = camera.get("url")
        video_id = camera.get("video_id")

        if camera.get("channel_id"):
            video_id = self._resolve_youtube_live_id(camera["channel_id"])
            if not video_id:
                return FetchResult(
                    success=False, camera_name=camera_name,
                    error=f"Channel {camera['channel_id']} is not live",
                )
            url = f"https://www.youtube.com/watch?v={video_id}"

        if not url and not video_id:
            return FetchResult(success=False, error=f"No URL/video_id for camera {camera_name}")

        # Derive video_id from URL if not explicitly given
        if not video_id and url:
            m = _re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', url)
            if m:
                video_id = m.group(1)

        logger.info(f"Fetching YouTube live frame from: {camera_name}")

        output_dir = Path(self.config.paths.get("data_dir", "./data"))
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now()
        raw_path = output_dir / "current_raw.png"

        # ---- Phase 1: try HLS manifest extraction ----
        hls_url = self._extract_youtube_hls(url or f"https://www.youtube.com/watch?v={video_id}")
        if not hls_url and video_id and camera.get("youtube_player_api"):
            hls_url = self._youtube_player_hls(video_id)
        if hls_url:
            try:
                result = subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", hls_url,
                        "-frames:v", "1",
                        "-q:v", "2",
                        "-update", "1",
                        str(raw_path),
                    ],
                    capture_output=True,
                    timeout=60,  # Koh Phangan measured 32.5 s end to end on the Pi Zero
                )
                if result.returncode == 0 and raw_path.exists():
                    logger.info(f"YouTube HLS frame saved: {raw_path}")
                    return FetchResult(
                        success=True,
                        image_path=str(raw_path),
                        camera_name=camera_name,
                        timestamp=timestamp,
                    )
                else:
                    err = result.stderr.decode()[-200:] if result.stderr else "unknown"
                    logger.warning(f"ffmpeg failed on YouTube HLS: {err}")
            except subprocess.TimeoutExpired:
                logger.warning("ffmpeg timed out on YouTube HLS")
            except FileNotFoundError:
                logger.warning("ffmpeg not found, falling back to thumbnail")
            except Exception as e:
                logger.warning(f"YouTube HLS extraction error: {e}")

        # ---- Phase 2: fallback to live thumbnail ----
        if video_id:
            logger.info(f"Falling back to YouTube thumbnail for {camera_name}")
            thumb_camera = dict(camera)
            thumb_camera["url"] = f"https://i.ytimg.com/vi/{video_id}/maxresdefault_live.jpg"
            thumb_camera["type"] = "snapshot"
            return self._fetch_snapshot(thumb_camera)

        return FetchResult(
            success=False,
            camera_name=camera_name,
            error="Could not extract HLS or thumbnail from YouTube live stream",
        )

    @staticmethod
    def _resolve_youtube_live_id(channel_id: str) -> Optional[str]:
        """
        Current live video id of a channel, or None if it is not live.

        youtube.com/channel/<id>/live serves the live video's watch page, and
        its <link rel="canonical"> carries the video id in plain HTML (no JS).
        When the channel is offline the canonical points at the channel
        itself, so there is no v= to find.
        """
        import re as _re

        try:
            resp = requests.get(
                f"https://www.youtube.com/channel/{channel_id}/live",
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
            )
            resp.raise_for_status()
            m = _re.search(
                r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"',
                resp.text,
            )
            if m:
                logger.info(f"YouTube channel {channel_id} is live as {m.group(1)}")
                return m.group(1)
            logger.warning(f"YouTube channel {channel_id} has no live video")
        except Exception as e:
            logger.warning(f"Failed to resolve live video for channel {channel_id}: {e}")
        return None

    @staticmethod
    def _youtube_player_hls(video_id: str, height: int = 720) -> Optional[str]:
        """
        HLS playlist for a live video via YouTube's own player API.

        The watch page stopped embedding hlsManifestUrl, and for many channels
        the live thumbnail is a fixed promo graphic, so neither older path
        yields a real frame. This asks the player endpoint directly while
        presenting as the visionOS app, the client that still returns
        streamingData.hlsManifestUrl without a login (yt-dlp uses the same
        route as of 2026-08). It needs the watch page's VISITOR_DATA, and the
        returned URL is bound to the requesting IP for ~6 h, so it is fetched
        fresh on every call.

        Fragile by nature: YouTube can retire this client at any time. Opt-in
        per camera (youtube_player_api: true), and a failure just returns None.

        Returns the variant playlist closest to `height` (720p keeps ffmpeg's
        decode cheap on a Pi Zero), or None.
        """
        import json as _json
        import re as _re

        try:
            page = requests.get(
                f"https://www.youtube.com/watch?v={video_id}", timeout=15,
                headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"},
            )
            page.raise_for_status()
            m = _re.search(r'"VISITOR_DATA":"([^"]+)"', page.text)
            if not m:
                logger.warning("YouTube player API: no VISITOR_DATA on watch page")
                return None
            visitor = m.group(1)

            body = {
                "videoId": video_id,
                "context": {"client": {
                    "clientName": "VISIONOS", "clientVersion": "1.02",
                    "deviceMake": "Apple", "deviceModel": "RealityDevice17,1",
                    "osName": "visionOS", "osVersion": "26.5.23O471",
                    "hl": "en", "visitorData": visitor,
                }},
            }
            resp = requests.post(
                "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
                data=_json.dumps(body), timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_3) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15"
                    ),
                    "Content-Type": "application/json",
                    "X-YouTube-Client-Name": "101",
                    "X-YouTube-Client-Version": "1.02",
                    "X-Goog-Visitor-Id": visitor,
                    "Origin": "https://www.youtube.com",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            master = (data.get("streamingData") or {}).get("hlsManifestUrl")
            if not master:
                status = (data.get("playabilityStatus") or {}).get("status")
                logger.warning(f"YouTube player API: no HLS (status {status})")
                return None

            # Pick the variant nearest the target height from the master list.
            listing = requests.get(master, timeout=15).text.splitlines()
            best, best_gap = None, None
            for i, line in enumerate(listing[:-1]):
                rm = _re.search(r"RESOLUTION=\d+x(\d+)", line)
                if rm:
                    gap = abs(int(rm.group(1)) - height)
                    if best_gap is None or gap < best_gap:
                        best, best_gap = listing[i + 1].strip(), gap
            logger.info(f"YouTube player API: got HLS for {video_id}")
            return best or master
        except Exception as e:
            logger.warning(f"YouTube player API failed for {video_id}: {e}")
            return None

    @staticmethod
    def _extract_youtube_hls(video_url: str) -> Optional[str]:
        """
        Scrape the YouTube watch page to pull out the hlsManifestUrl.

        Returns the manifest URL string, or None on failure.
        This works because YouTube embeds the HLS manifest in the initial
        HTML response for live broadcasts (no JS execution required).
        """
        import re as _re

        try:
            resp = requests.get(video_url, timeout=15, headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            })
            resp.raise_for_status()
            m = _re.search(r'hlsManifestUrl":"(https://[^"]+)"', resp.text)
            if m:
                manifest = m.group(1).replace("\\u0026", "&")
                logger.info(f"Extracted YouTube HLS manifest ({len(manifest)} chars)")
                return manifest
            logger.warning("hlsManifestUrl not found in YouTube page")
        except Exception as e:
            logger.warning(f"Failed to scrape YouTube page: {e}")
        return None

    def _fetch_earthcam(self, camera: dict) -> FetchResult:
        """
        Fetch a frame from an EarthCam camera.

        EarthCam streams require a dynamic token that is embedded in the
        player page HTML.  Two-phase approach:
          1. Fetch the embed page, extract the HLS m3u8 URL (contains a
             time-limited token), then grab one frame with ffmpeg.
          2. If the stream is offline (404 / no m3u8), return failure.

        Config fields:
          earthcam_vid  - the EarthCam video ID (e.g. "ab911fdb8c")
          url           - (optional) direct m3u8 URL override
        """
        import re as _re
        import subprocess

        camera_name = camera.get("name", "Unknown")
        vid = camera.get("earthcam_vid")

        if not vid:
            return FetchResult(success=False, error=f"No earthcam_vid for camera {camera_name}")

        logger.info(f"Fetching EarthCam frame from: {camera_name} (vid={vid})")

        output_dir = Path(self.config.paths.get("data_dir", "./data"))
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now()
        raw_path = output_dir / "current_raw.png"

        # Phase 1: fetch the embed page to get the m3u8 URL with fresh token
        embed_url = (
            f"https://www.earthcam.com/js/video/embed.php"
            f"?vid={vid}&type=h264&w=auto&app_path=myearthcam"
            f"&ip=0&requested_version=current"
        )

        try:
            resp = requests.get(embed_url, timeout=15, headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": f"https://myearthcam.com/",
            })
            resp.raise_for_status()

            # The m3u8 URL is in a JSON config like:
            # "src":"https:\/\/videos-3.earthcam.com\/fecnetwork\/VID\/playlist.m3u8?t=TOKEN&td=TIMESTAMP"
            m = _re.search(r'"src"\s*:\s*"(https?:\\/\\/[^"]*m3u8[^"]*)"', resp.text)
            if not m:
                logger.warning(f"EarthCam {camera_name}: no m3u8 URL in embed page (camera likely offline)")
                return FetchResult(
                    success=False, camera_name=camera_name,
                    error="EarthCam camera offline (no m3u8 in embed page)"
                )

            m3u8_url = m.group(1).replace("\\/", "/")
            logger.info(f"Extracted EarthCam HLS URL ({len(m3u8_url)} chars)")

            # Phase 2: grab one frame with ffmpeg
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-headers", "Referer: https://www.earthcam.com/\r\n",
                    "-i", m3u8_url,
                    "-frames:v", "1",
                    "-q:v", "2",
                    "-update", "1",
                    str(raw_path),
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0 and raw_path.exists():
                logger.info(f"EarthCam frame saved: {raw_path}")
                return FetchResult(
                    success=True,
                    image_path=str(raw_path),
                    camera_name=camera_name,
                    timestamp=timestamp,
                )
            else:
                err = result.stderr.decode()[-200:] if result.stderr else "unknown"
                logger.warning(f"ffmpeg failed on EarthCam HLS: {err}")
                return FetchResult(
                    success=False, camera_name=camera_name,
                    error=f"ffmpeg failed: {err}"
                )

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timed out for EarthCam {camera_name}")
            return FetchResult(success=False, camera_name=camera_name, error="ffmpeg timeout")
        except FileNotFoundError:
            logger.error("ffmpeg not found — install with: sudo apt install ffmpeg")
            return FetchResult(success=False, camera_name=camera_name, error="ffmpeg not installed")
        except Exception as e:
            logger.error(f"Failed to fetch EarthCam {camera_name}: {e}")
            return FetchResult(success=False, camera_name=camera_name, error=str(e))

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
    return Fetcher().fetch_with_fallback()


if __name__ == "__main__":
    # Test fetcher
    logging.basicConfig(level=logging.DEBUG)
    result = fetch_frame()
    print(f"Success: {result.success}")
    print(f"Image: {result.image_path}")
    if result.error:
        print(f"Error: {result.error}")
