"""
inspector.py

Functions for inspecting image metadata.
"""

from pathlib import Path

from PIL import Image


def inspect_image(filename: str) -> dict:
    """
    Read an image and return its metadata.

    Parameters
    ----------
    filename : str
        Path to the image.

    Returns
    -------
    dict
        Dictionary containing image information.
    """

    path = Path(filename)

    with Image.open(path) as img:
        return {
            "filename": path.name,
            "filesize": path.stat().st_size,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "png_info": dict(img.info),
            "exif": dict(img.getexif()),
        }

