"""
metadata_stripper.py

Coordinates combined metadata stripping.

The ``--all`` operation applies both the AI metadata policy and the
privacy-oriented EXIF/container metadata policy while preserving technical
metadata and image content.
"""

from pathlib import Path

from PIL import Image, PngImagePlugin

from .exif_stripper import (
    PRIVATE_CONTAINER_FIELDS,
    remove_private_exif_fields,
    save_jpeg_without_private_metadata,
)

AI_CONTAINER_FIELDS = {
    "parameters",
}


def strip_all_metadata(
    filename: str,
    output_filename: str | None = None,
    force: bool = False,
) -> Path:
    """
    Remove AI and privacy-sensitive metadata and write a new image.

    ``--all`` represents the union of the existing AI and EXIF privacy
    stripping policies. Technical metadata required for faithful image
    interpretation is preserved.
    """

    source = Path(filename)

    if output_filename is None:
        destination = build_all_stripped_filename(source)
    else:
        destination = Path(output_filename)

    with Image.open(source) as img:
        if destination.exists() and not force:
            raise FileExistsError(destination)

        if img.format == "PNG":
            save_png_without_ai_or_private_metadata(
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
                f"combined metadata stripping is not supported for {img.format}"
            )

    return destination


def build_all_stripped_filename(source: Path) -> Path:
    """
    Build the default output filename for combined metadata stripping.
    """

    return source.with_name(f"{source.stem}-All-Stripped{source.suffix}")


def save_png_without_ai_or_private_metadata(
    img,
    destination: Path,
) -> None:
    """
    Save a PNG without AI or privacy-sensitive metadata.

    Technical EXIF data, ICC profiles, DPI information, and unrelated textual
    metadata are preserved.
    """

    pnginfo = PngImagePlugin.PngInfo()

    excluded_fields = PRIVATE_CONTAINER_FIELDS | AI_CONTAINER_FIELDS

    for key, value in img.info.items():
        normalized = key.lower()

        if normalized in excluded_fields:
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
