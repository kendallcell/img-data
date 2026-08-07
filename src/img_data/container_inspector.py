"""
container_inspector.py

Functions for collecting, classifying, and presenting metadata stored in
image containers.

This module deals with metadata exposed by Pillow through an image's ``info``
dictionary. It does not inspect EXIF metadata, interpret AI generation data,
or modify image files.
"""

# ---------------------------------------------------------------------------
# Display categories
# ---------------------------------------------------------------------------

CONTAINER_CATEGORY_ORDER = (
    "Image Profile",
    "Embedded Metadata",
    "Image Properties",
    "Comments",
    "Other Container Metadata",
)


# ---------------------------------------------------------------------------
# Public container inspection API
# ---------------------------------------------------------------------------


def collect_container_metadata(img) -> dict:
    """
    Collect metadata stored in the image container.

    Pillow exposes container-level metadata through ``Image.info`` for
    formats including PNG and JPEG.

    Parameters
    ----------
    img : PIL.Image.Image
        Open Pillow image.

    Returns
    -------
    dict
        Copy of the image's container metadata.
    """

    return dict(img.info)


def classify_container_metadata(metadata: dict) -> dict[str, dict]:
    """
    Group container metadata into human-oriented categories.

    No metadata is intentionally discarded. Unknown fields are preserved
    under ``Other Container Metadata``.

    Parameters
    ----------
    metadata : dict
        Raw container metadata.

    Returns
    -------
    dict
        Categorized container metadata.
    """

    sections = {category: {} for category in CONTAINER_CATEGORY_ORDER}

    for key, value in metadata.items():
        category = classify_container_field(key)

        sections[category][key] = prepare_container_value_for_display(
            key,
            value,
        )

    return {category: fields for category, fields in sections.items() if fields}


def classify_container_field(field_name: str) -> str:
    """
    Return the display category for one container metadata field.
    """

    normalized = field_name.lower()

    if normalized in {
        "icc_profile",
        "srgb",
        "gamma",
        "chromaticity",
    }:
        return "Image Profile"

    if normalized in {
        "exif",
        "xmp",
        "xml:com.adobe.xmp",
        "raw profile type exif",
    }:
        return "Embedded Metadata"

    if normalized in {
        "dpi",
        "jfif",
        "jfif_version",
        "jfif_unit",
        "jfif_density",
        "transparency",
        "aspect",
    }:
        return "Image Properties"

    if normalized in {
        "comment",
        "description",
        "title",
        "author",
        "copyright",
    }:
        return "Comments"

    return "Other Container Metadata"


def friendly_container_field_name(field_name: str) -> str:
    """
    Return a human-readable label for a container metadata field.
    """

    normalized = field_name.lower()

    friendly_names = {
        "icc_profile": "ICC Color Profile",
        "srgb": "sRGB",
        "gamma": "Gamma",
        "chromaticity": "Chromaticity",
        "exif": "EXIF Block",
        "raw profile type exif": "EXIF Profile",
        "xmp": "XMP Metadata",
        "xml:com.adobe.xmp": "Adobe XMP Metadata",
        "dpi": "DPI",
        "jfif": "JFIF Version",
        "jfif_version": "JFIF Version",
        "jfif_unit": "JFIF Density Unit",
        "jfif_density": "JFIF Density",
        "comment": "Comment",
        "description": "Description",
        "title": "Title",
        "author": "Author",
        "copyright": "Copyright",
        "transparency": "Transparency",
        "aspect": "Aspect Ratio",
    }

    return friendly_names.get(
        normalized,
        field_name,
    )


# ---------------------------------------------------------------------------
# Display preparation
# ---------------------------------------------------------------------------


def prepare_container_value_for_display(
    field_name: str,
    value,
):
    """
    Convert container metadata values into concise representations.

    Large binary blobs and embedded metadata packets are summarized instead
    of being dumped directly to the terminal.
    """

    if isinstance(value, bytes):
        return describe_container_bytes(
            field_name,
            value,
        )

    if isinstance(value, dict):
        return {
            key: prepare_container_value_for_display(
                str(key),
                item,
            )
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return tuple(
            prepare_container_value_for_display(
                field_name,
                item,
            )
            for item in value
        )

    if isinstance(value, list):
        return [
            prepare_container_value_for_display(
                field_name,
                item,
            )
            for item in value
        ]

    if isinstance(value, str):
        return describe_container_text(
            field_name,
            value,
        )

    return value


def describe_container_bytes(
    field_name: str,
    value: bytes,
) -> str:
    """
    Return a useful description of binary container metadata.
    """

    normalized = field_name.lower()
    size = len(value)

    if normalized == "icc_profile":
        return f"Present ({size} bytes)"

    if normalized in {
        "xmp",
        "xml:com.adobe.xmp",
    }:
        return f"Present ({size} bytes)"

    if normalized == "exif":
        return f"Present ({size} bytes)"

    decoded = try_decode_printable_bytes(value)

    if decoded is not None:
        return decoded

    return f"<binary data: {size} bytes>"


def describe_container_text(
    field_name: str,
    value: str,
) -> str:
    """
    Summarize very large text-based metadata packets.

    Ordinary short strings are returned unchanged.
    """

    normalized = field_name.lower()

    if (
        normalized
        in {
            "xmp",
            "xml:com.adobe.xmp",
        }
        and len(value) > 256
    ):
        return f"Present ({len(value)} characters)"

    if normalized == "raw profile type exif" and len(value) > 256:
        return f"Present ({len(value)} characters)"

    return value


def try_decode_printable_bytes(value: bytes) -> str | None:
    """
    Decode short binary values only when the result is printable.
    """

    if not value or len(value) > 256:
        return None

    for encoding in (
        "utf-8",
        "ascii",
        "latin-1",
    ):
        try:
            decoded = value.rstrip(b"\x00").decode(encoding)
        except UnicodeDecodeError:
            continue

        if decoded and decoded.isprintable():
            return decoded

    return None
