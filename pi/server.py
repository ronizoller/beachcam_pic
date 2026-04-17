"""
Server module - HTTP endpoints for ESP32 to fetch images.
Provides /image, /hash, and /metadata endpoints.
"""

import json
import logging
from pathlib import Path
from threading import Thread
from typing import Optional

from flask import Flask, send_file, jsonify, Response

from config import get_config

logger = logging.getLogger(__name__)


def create_app(on_image_pulled=None, get_sleep_minutes=None, get_guest_info=None) -> Flask:
    """Create and configure Flask application.

    Args:
        on_image_pulled: Optional callback invoked when ESP32 pulls /image.
        get_sleep_minutes: Optional callback returning minutes until next active time.
    """
    app = Flask(__name__)
    config = get_config()

    data_dir = Path(config.paths.get("data_dir", "./data"))
    image_path = data_dir / "current.bmp"
    metadata_path = data_dir / "metadata.json"

    @app.route("/")
    def index():
        """Health check endpoint."""
        return jsonify({
            "status": "ok",
            "service": "beachcam",
            "endpoints": ["/image", "/hash", "/metadata", "/preview", "/raw", "/sleep", "/guest"]
        })

    @app.route("/image")
    def get_image():
        """
        Get the current processed image.
        Returns BMP file optimized for E-Ink display.
        Signals the service to clear candidates for next cycle.
        """
        if not image_path.exists():
            return Response("No image available", status=404)

        if on_image_pulled:
            on_image_pulled()

        return send_file(
            image_path,
            mimetype="image/bmp",
            as_attachment=False,
            download_name="current.bmp"
        )

    @app.route("/preview")
    def get_preview():
        """
        Get preview image (PNG for browser viewing).
        Same as /image but in PNG format.
        """
        if not image_path.exists():
            return Response("No image available", status=404)

        # Convert BMP to PNG on-the-fly for browser preview
        from PIL import Image
        import io

        img = Image.open(image_path)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype="image/png",
            as_attachment=False,
            download_name="preview.png"
        )

    @app.route("/hash")
    def get_hash():
        """
        Get hash of current image.
        ESP32 can check this to avoid downloading unchanged images.
        """
        metadata = _load_metadata(metadata_path)
        if metadata is None:
            return Response("No metadata available", status=404)

        return jsonify({
            "hash": metadata.get("hash", ""),
            "timestamp": metadata.get("timestamp", ""),
        })

    @app.route("/metadata")
    def get_metadata():
        """
        Get full metadata including weather info.
        """
        metadata = _load_metadata(metadata_path)
        if metadata is None:
            return Response("No metadata available", status=404)
        return jsonify(metadata)

    @app.route("/raw")
    def get_raw():
        """Get the raw (unprocessed) image for debugging."""
        raw_path = data_dir / "current_raw.png"
        if not raw_path.exists():
            return Response("No raw image available", status=404)
        return send_file(raw_path, mimetype="image/png")

    @app.route("/guest")
    def get_guest():
        """Get today's guest beach schedule."""
        if get_guest_info:
            return jsonify(get_guest_info())
        return jsonify({"status": "no guest info available"})

    @app.route("/sleep")
    def get_sleep():
        """
        Get recommended sleep duration for ESP32.
        Returns normal interval during active hours,
        or minutes until next sunrise during night.
        """
        default = config.timing.get("esp_sleep_minutes", 30)
        if get_sleep_minutes:
            minutes = get_sleep_minutes()
        else:
            minutes = default
        return jsonify({"sleep_minutes": minutes})

    return app


def _load_metadata(path: Path) -> Optional[dict]:
    """Load metadata from JSON file."""
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return None


class Server:
    """HTTP server for serving images to ESP32."""

    def __init__(self, on_image_pulled=None, get_sleep_minutes=None, get_guest_info=None):
        self.config = get_config()
        self.app = create_app(on_image_pulled=on_image_pulled, get_sleep_minutes=get_sleep_minutes, get_guest_info=get_guest_info)
        self._thread: Optional[Thread] = None

    def run(self, threaded: bool = False):
        """
        Start the server.

        Args:
            threaded: If True, run in background thread.
        """
        host = self.config.server.get("host", "0.0.0.0")
        port = self.config.server.get("port", 8080)

        if threaded:
            self._thread = Thread(
                target=self._run_server,
                args=(host, port),
                daemon=True
            )
            self._thread.start()
            logger.info(f"Server started in background on {host}:{port}")
        else:
            self._run_server(host, port)

    def _run_server(self, host: str, port: int):
        """Run Flask server."""
        logger.info(f"Starting server on {host}:{port}")
        # Disable Flask's default logging for cleaner output
        import logging as log
        log.getLogger("werkzeug").setLevel(log.WARNING)
        self.app.run(host=host, port=port, debug=False, use_reloader=False)


def run_server(threaded: bool = False):
    """Convenience function to run the server."""
    server = Server()
    server.run(threaded=threaded)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()
