"""
Cropper module - extracts the actual video area from camera screenshots.
Removes borders, headers, footers, and UI elements.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image

from config import get_config

logger = logging.getLogger(__name__)


class Cropper:
    """Crops screenshots to extract the actual beach video area."""

    def __init__(self):
        self.config = get_config()

    def crop(
        self,
        image_path: str,
        camera_name: str = None,
        crop_box: Tuple[int, int, int, int] = None,
    ) -> Optional[Image.Image]:
        """
        Crop image to extract video area.

        Args:
            image_path: Path to raw screenshot.
            camera_name: Name of camera (to look up crop settings).
            crop_box: Manual crop box (left, top, right, bottom).
                     If None, tries to auto-detect or use config.

        Returns:
            Cropped PIL Image or None if failed.
        """
        try:
            img = Image.open(image_path)
            logger.debug(f"Loaded image: {img.size}")

            # Get crop box from arguments, config, or auto-detect
            if crop_box is None:
                crop_box = self._get_crop_box(img, camera_name)

            if crop_box:
                logger.info(f"Cropping to: {crop_box}")
                img = img.crop(crop_box)
            else:
                logger.info("No crop box - using full image")

            return img

        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            return None

    def _get_crop_box(
        self, img: Image.Image, camera_name: str = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """Get crop box from config or auto-detect."""
        # First, try to get from camera config
        if camera_name:
            for cam in self.config.cameras:
                if cam.get("name") == camera_name:
                    box = cam.get("crop_box")
                    # crop_box: false means explicitly no cropping
                    if box is False:
                        logger.debug("Cropping explicitly disabled for this camera")
                        return None
                    if box:
                        return tuple(box)

        # Try auto-detection
        return self._auto_detect_video_area(img)

    def _auto_detect_video_area(
        self, img: Image.Image
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Attempt to auto-detect the video area in the screenshot.

        Strategy:
        1. Look for large rectangular region with video-like content
        2. Detect borders/UI by looking for uniform color regions
        3. Find the main content area

        Returns crop box or None if detection fails.
        """
        try:
            arr = np.array(img)
            height, width = arr.shape[:2]

            # Simple heuristic: assume video is in center-ish area
            # Look for rows/columns that are mostly uniform (UI elements)

            # Convert to grayscale for analysis
            if len(arr.shape) == 3:
                gray = np.mean(arr, axis=2)
            else:
                gray = arr

            # Find top border: look for uniform rows from top
            top = self._find_content_start(gray, axis=0)

            # Find bottom border: look for uniform rows from bottom
            bottom = height - self._find_content_start(gray[::-1], axis=0)

            # Find left border
            left = self._find_content_start(gray.T, axis=0)

            # Find right border
            right = width - self._find_content_start(gray.T[::-1], axis=0)

            # Validate the detected region
            if right - left < width * 0.3 or bottom - top < height * 0.3:
                logger.warning("Auto-detected region too small, using full image")
                return None

            logger.info(f"Auto-detected video area: ({left}, {top}, {right}, {bottom})")
            return (left, top, right, bottom)

        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}")
            return None

    def _find_content_start(self, gray: np.ndarray, axis: int = 0) -> int:
        """Find where content starts (after uniform border area)."""
        # Calculate variance along the axis
        variance = np.var(gray, axis=axis)

        # Threshold: content has higher variance than solid borders
        threshold = np.median(variance) * 0.5

        # Find first row/col with high variance
        content_mask = variance > threshold
        content_indices = np.where(content_mask)[0]

        if len(content_indices) > 0:
            return int(content_indices[0])
        return 0

    def crop_and_save(
        self,
        image_path: str,
        output_path: str = None,
        camera_name: str = None,
        crop_box: Tuple[int, int, int, int] = None,
    ) -> Optional[str]:
        """
        Crop image and save to file.

        Returns output path if successful, None otherwise.
        """
        img = self.crop(image_path, camera_name, crop_box)
        if img is None:
            return None

        if output_path is None:
            output_path = Path(image_path).parent / "cropped.png"

        img.save(output_path)
        logger.info(f"Saved cropped image: {output_path}")
        return str(output_path)


def crop_image(
    image_path: str,
    camera_name: str = None,
    crop_box: Tuple[int, int, int, int] = None,
) -> Optional[Image.Image]:
    """Convenience function to crop an image."""
    cropper = Cropper()
    return cropper.crop(image_path, camera_name, crop_box)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        result = crop_image(sys.argv[1])
        if result:
            result.save("cropped_test.png")
            print("Saved to cropped_test.png")
    else:
        print("Usage: python cropper.py <image_path>")
