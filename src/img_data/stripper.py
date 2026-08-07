"""
stripper.py

Functions for removing selected metadata from image files.

The first implementation supports removing AI generation metadata while
preserving image content and unrelated metadata whenever the image format
allows it.
"""

from pathlib import Path

from PIL import ExifTags, Image, PngImagePlugin

from .ai_inspector import looks_like_ai_metadata
from .exif_inspector import decode_exif_user_comment

AI_EXIF_TEXT_FIELDS = (
    "UserComment",
    "ImageDescription",
    "Comment",
)

EXIF_IFD_TAG = 0x8769


def strip_ai_metadata(
    filename: str,
    output_filename: str | None = None,
    force: bool = False,
) -> Path:
    """
    Remove AI generation metadata and write a new image file.

    PNG ``parameters`` metadata is removed when it contains recognizable AI
    generation data. JPEG EXIF text fields are removed only when their content
    resembles AI metadata.

    Existing output files are preserved unless ``force`` is True.

    Parameters
    ----------
    filename : str
        Source image path.

    output_filename : str | None
        Optional destination path. When omitted, a new filename ending in
        ``-AI-Stripped`` is created beside the source image.

    force : bool
        Overwrite an existing destination when True.

    Returns
    -------
    pathlib.Path
        Path to the newly written image.

    Raises
    ------
    FileExistsError
        If the destination exists and ``force`` is False.
    """

    source = Path(filename)

    if output_filename is None:
        destination = build_ai_stripped_filename(source)
    else:
        destination = Path(output_filename)

    with Image.open(source) as img:
        if destination.exists() and not force:
            raise FileExistsError(destination)

        if img.format == "PNG":
            save_png_without_ai_metadata(
                img,
                destination,
            )

        elif img.format == "JPEG":
            save_jpeg_without_ai_metadata(
                img,
                destination,
            )

        else:
            raise ValueError(f"AI metadata stripping is not supported for {img.format}")

    return destination


def build_ai_stripped_filename(source: Path) -> Path:
    """
    Build the default output filename for AI metadata stripping.
    """

    return source.with_name(f"{source.stem}-AI-Stripped{source.suffix}")


def save_png_without_ai_metadata(
    img,
    destination: Path,
) -> None:
    """
    Save a PNG while removing recognized AI generation text metadata.

    Non-AI textual metadata is preserved. EXIF and ICC profile data are passed
    through separately because Pillow does not store them in ``PngInfo``.
    """

    pnginfo = PngImagePlugin.PngInfo()

    for key, value in img.info.items():
        if key in {
            "parameters",
            "exif",
            "icc_profile",
            "dpi",
        }:
            continue

        if isinstance(value, str):
            pnginfo.add_text(
                key,
                value,
            )

    save_kwargs = {
        "pnginfo": pnginfo,
    }

    exif = img.info.get("exif")

    if exif is not None:
        save_kwargs["exif"] = exif

    icc_profile = img.info.get("icc_profile")

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    dpi = img.info.get("dpi")

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    img.save(
        destination,
        format="PNG",
        **save_kwargs,
    )


def save_jpeg_without_ai_metadata(
    img,
    destination: Path,
) -> None:
    """
    Save a JPEG after removing EXIF text fields containing AI metadata.

    Other EXIF fields and the ICC profile are preserved.
    """

    exif = img.getexif()

    remove_ai_exif_fields(exif)

    save_kwargs = {
        "exif": exif,
    }

    icc_profile = img.info.get("icc_profile")

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    dpi = img.info.get("dpi")

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    img.save(
        destination,
        format="JPEG",
        **save_kwargs,
    )


def remove_ai_exif_fields(exif) -> None:
    """
    Remove EXIF text fields only when they contain recognizable AI metadata.
    """

    if not exif:
        return

    tag_ids_by_name = {
        name: tag_id
        for tag_id, name in ExifTags.TAGS.items()
        if name in AI_EXIF_TEXT_FIELDS
    }

    for field_name in AI_EXIF_TEXT_FIELDS:
        tag_id = tag_ids_by_name.get(field_name)

        if tag_id is None:
            continue

        value = find_exif_value(
            exif,
            tag_id,
        )

        if value is None:
            continue

        text = normalize_exif_text_value(
            field_name,
            value,
        )

        if text and looks_like_ai_metadata(text):
            delete_exif_value(
                exif,
                tag_id,
            )


def find_exif_value(
    exif,
    tag_id: int,
):
    """
    Find an EXIF value in the top-level or nested EXIF IFD.
    """

    if tag_id in exif:
        return exif[tag_id]

    try:
        nested = exif.get_ifd(EXIF_IFD_TAG)

    except (KeyError, TypeError, ValueError):
        return None

    return nested.get(tag_id)


def delete_exif_value(
    exif,
    tag_id: int,
) -> None:
    """
    Delete an EXIF value from the top-level or nested EXIF IFD.
    """

    if tag_id in exif:
        del exif[tag_id]
        return

    try:
        nested = exif.get_ifd(EXIF_IFD_TAG)

    except (KeyError, TypeError, ValueError):
        return

    if tag_id in nested:
        del nested[tag_id]


def normalize_exif_text_value(
    field_name: str,
    value,
) -> str | None:
    """
    Convert an EXIF text value into readable text for AI detection.
    """

    if isinstance(value, str):
        return value

    if isinstance(value, bytes):
        if field_name == "UserComment":
            return decode_exif_user_comment(value)

        return value.decode(
            "utf-8",
            errors="replace",
        )

    return None
