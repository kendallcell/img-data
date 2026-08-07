"""
inspector.py

Coordinates image metadata inspection.

This module opens an image, delegates specialized metadata inspection, locates
AI generation metadata, and returns a structured dictionary for presentation
by the command-line interface.
"""

from pathlib import Path

from PIL import Image

from .ai_inspector import (
    looks_like_ai_metadata,
    parse_ai_metadata,
)
from .container_inspector import collect_container_metadata
from .exif_inspector import (
    collect_exif_metadata,
    prepare_exif_for_display,
)

AI_EXIF_TEXT_FIELDS = (
    "UserComment",
    "ImageDescription",
    "Comment",
)


def inspect_image(filename: str) -> dict:
    """
    Read an image and return structured metadata.

    AI metadata is detected independently of the image format. It may come
    from container metadata such as a PNG ``parameters`` text chunk or from
    an EXIF text field such as ``UserComment``.

    Parameters
    ----------
    filename : str
        Path to the image file.

    Returns
    -------
    dict
        Structured image, AI, container, and EXIF metadata.
    """

    path = Path(filename)

    with Image.open(path) as img:
        container = collect_container_metadata(img)
        exif = collect_exif_metadata(img)

        raw_ai_text, ai_source = extract_ai_metadata(
            container,
            exif,
        )

        ai = parse_ai_metadata(raw_ai_text)

        display_exif = prepare_exif_for_display(
            exif,
            ai_source,
        )

        return {
            "filename": path.name,
            "filesize": path.stat().st_size,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "container": container,
            "exif": display_exif,
            "ai": ai,
        }


def extract_ai_metadata(
    container: dict,
    exif: dict,
) -> tuple[str | None, tuple[str, str] | None]:
    """
    Search available metadata sources for AI generation information.

    Container ``parameters`` metadata is checked first. EXIF text fields are
    then checked for text that resembles AI generation metadata.

    Parameters
    ----------
    container : dict
        Container metadata collected from Pillow.

    exif : dict
        Human-readable EXIF metadata.

    Returns
    -------
    tuple
        Raw AI metadata text and a source descriptor. Both values are None
        when no AI metadata is found.
    """

    parameters = container.get("parameters")

    if isinstance(parameters, str) and looks_like_ai_metadata(parameters):
        return parameters, ("container", "parameters")

    for field_name in AI_EXIF_TEXT_FIELDS:
        value = exif.get(field_name)

        if isinstance(value, str) and looks_like_ai_metadata(value):
            return value, ("exif", field_name)

    return None, None
