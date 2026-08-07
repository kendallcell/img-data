"""
exif_stripper.py

Privacy-oriented EXIF metadata stripping.

This module removes metadata that may identify a person, device, location,
editing environment, or human-entered description while preserving technical
image metadata whenever possible.
"""

from pathlib import Path

from PIL import ExifTags, Image, PngImagePlugin

# ---------------------------------------------------------------------------
# Privacy policy
# ---------------------------------------------------------------------------

PRIVATE_EXIF_FIELDS = {
    # Human-entered descriptive information
    "Artist",
    "Copyright",
    "DocumentName",
    "HostComputer",
    "ImageDescription",
    "UserComment",
    "XPAuthor",
    "XPComment",
    "XPKeywords",
    "XPSubject",
    "XPTitle",
    # Editing environment
    "Software",
    # Capture dates and times
    "DateTime",
    "DateTimeDigitized",
    "DateTimeOriginal",
    "OffsetTime",
    "OffsetTimeDigitized",
    "OffsetTimeOriginal",
    # Device identity / fingerprinting
    "Make",
    "Model",
    "CameraOwnerName",
    "BodySerialNumber",
    "LensMake",
    "LensModel",
    "LensSerialNumber",
    "ImageUniqueID",
    "MakerNote",
    # Location
    "GPSInfo",
}


PRIVATE_CONTAINER_FIELDS = {
    "author",
    "comment",
    "copyright",
    "description",
    "raw profile type exif",
    "title",
    "xmp",
    "xml:com.adobe.xmp",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def strip_exif_metadata(
    filename: str,
    output_filename: str | None = None,
    force: bool = False,
) -> Path:
    """
    Remove privacy-sensitive metadata and write a new image file.

    Technical EXIF metadata such as exposure settings, orientation, color
    information, and image dimensions is preserved whenever possible.

    Parameters
    ----------
    filename : str
        Source image path.

    output_filename : str | None
        Optional destination path. When omitted, a filename ending in
        ``-EXIF-Stripped`` is created beside the source image.

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
        destination = build_exif_stripped_filename(source)
    else:
        destination = Path(output_filename)

    with Image.open(source) as img:
        if destination.exists() and not force:
            raise FileExistsError(destination)

        if img.format == "PNG":
            save_png_without_private_metadata(
                img,
                destination,
            )

        elif img.format == "JPEG":
            save_jpeg_without_private_metadata(
                img,
                destination,
            )

        else:
            raise ValueError(
                f"EXIF privacy stripping is not supported for {img.format}"
            )

    return destination


def build_exif_stripped_filename(source: Path) -> Path:
    """
    Build the default output filename for EXIF privacy stripping.
    """

    return source.with_name(f"{source.stem}-EXIF-Stripped{source.suffix}")


# ---------------------------------------------------------------------------
# EXIF filtering
# ---------------------------------------------------------------------------


def remove_private_exif_fields(exif) -> None:
    """
    Remove privacy-sensitive fields from top-level and nested EXIF data.
    """

    if not exif:
        return

    tag_ids = {
        tag_id for tag_id, name in ExifTags.TAGS.items() if name in PRIVATE_EXIF_FIELDS
    }

    remove_tags_from_mapping(
        exif,
        tag_ids,
    )

    for ifd_tag in get_nested_ifd_tags():
        try:
            nested = exif.get_ifd(ifd_tag)

        except (KeyError, TypeError, ValueError):
            continue

        remove_tags_from_mapping(
            nested,
            tag_ids,
        )


def remove_tags_from_mapping(
    mapping,
    tag_ids: set[int],
) -> None:
    """
    Delete selected EXIF tag IDs from an EXIF mapping.
    """

    for tag_id in tag_ids:
        if tag_id in mapping:
            del mapping[tag_id]


def get_nested_ifd_tags() -> tuple[int, ...]:
    """
    Return IFD tag identifiers that may contain privacy-sensitive EXIF data.
    """

    return (
        0x8769,  # Exif IFD
        0x8825,  # GPS IFD
    )


# ---------------------------------------------------------------------------
# PNG
# ---------------------------------------------------------------------------


def save_png_without_private_metadata(
    img,
    destination: Path,
) -> None:
    """
    Save a PNG without privacy-sensitive EXIF or container metadata.

    Technical EXIF data, ICC profiles, DPI information, and unrelated textual
    metadata are preserved whenever Pillow exposes them safely.
    """

    pnginfo = PngImagePlugin.PngInfo()

    for key, value in img.info.items():
        normalized = key.lower()

        if normalized in PRIVATE_CONTAINER_FIELDS:
            continue

        if key in {
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

    exif = img.getexif()

    if exif:
        remove_private_exif_fields(exif)

        if exif:
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


# ---------------------------------------------------------------------------
# JPEG
# ---------------------------------------------------------------------------


def save_jpeg_without_private_metadata(
    img,
    destination: Path,
) -> None:
    """
    Save a JPEG after removing privacy-sensitive EXIF metadata.

    Technical EXIF and ICC profile information is preserved. This currently
    uses Pillow's JPEG writer; a future metadata-only JPEG write path should
    replace it so compressed image data can be preserved byte-for-byte.
    """

    exif = img.getexif()

    remove_private_exif_fields(exif)

    save_kwargs = {}

    if exif:
        save_kwargs["exif"] = exif

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
