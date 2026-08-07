"""
inspector.py

Coordinates image metadata inspection.

This module opens an image, gathers metadata from the available containers,
locates AI generation metadata, delegates specialized inspection work, and
returns a structured dictionary for presentation by the command-line
interface.
"""

from pathlib import Path

from PIL import Image

from .ai_inspector import (
    looks_like_ai_metadata,
    parse_ai_metadata,
)
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
    from a PNG ``parameters`` text chunk or from an EXIF text field such as
    ``UserComment``.

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
        container_info = dict(img.info)
        exif = collect_exif_metadata(img)

        raw_ai_text, ai_source = extract_ai_metadata(
            container_info,
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
            "png_info": container_info,
            "exif": display_exif,
            "ai": ai,
        }


def extract_ai_metadata(
    container_info: dict,
    exif: dict,
) -> tuple[str | None, tuple[str, str] | None]:
    """
    Search available metadata containers for AI generation information.

    PNG ``parameters`` metadata is checked first. EXIF text fields are then
    checked for text that resembles AI generation metadata.

    The AI inspector does not care where the raw text originated. This
    function acts as the bridge between image metadata containers and the
    specialized AI parser.

    Parameters
    ----------
    container_info : dict
        Pillow image ``info`` dictionary.

    exif : dict
        Human-readable EXIF metadata.

    Returns
    -------
    tuple
        Raw AI metadata text and a source descriptor. Both values are None
        when no AI metadata is found.
    """

    parameters = container_info.get("parameters")

    if isinstance(parameters, str) and looks_like_ai_metadata(parameters):
        return parameters, ("container", "parameters")

    for field_name in AI_EXIF_TEXT_FIELDS:
        value = exif.get(field_name)

        if isinstance(value, str) and looks_like_ai_metadata(value):
            return value, ("exif", field_name)

    return None, None
