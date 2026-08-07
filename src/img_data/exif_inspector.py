"""
exif_inspector.py

Functions for collecting, decoding, classifying, and preparing EXIF metadata
for inspection.

This module is responsible only for EXIF inspection. It does not inspect
AI metadata and it does not modify image files.
"""

from PIL import ExifTags

# ---------------------------------------------------------------------------
# EXIF constants
# ---------------------------------------------------------------------------

EXIF_IFD_TAG = 0x8769
GPS_IFD_TAG = 0x8825


# ---------------------------------------------------------------------------
# Presentation categories
# ---------------------------------------------------------------------------

EXIF_CATEGORY_ORDER = (
    "Descriptive / Personal",
    "Camera / Device",
    "Capture Information",
    "Location",
    "Image / Technical",
    "Other EXIF",
)


DESCRIPTIVE_FIELDS = {
    "Artist",
    "Copyright",
    "ImageDescription",
    "UserComment",
    "XPTitle",
    "XPComment",
    "XPAuthor",
    "XPKeywords",
    "XPSubject",
    "DocumentName",
    "HostComputer",
}


CAMERA_FIELDS = {
    "Make",
    "Model",
    "Software",
    "CameraOwnerName",
    "BodySerialNumber",
    "LensMake",
    "LensModel",
    "LensSerialNumber",
}


CAPTURE_FIELDS = {
    "DateTime",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "ExposureTime",
    "FNumber",
    "ExposureProgram",
    "ISOSpeedRatings",
    "PhotographicSensitivity",
    "SensitivityType",
    "ShutterSpeedValue",
    "ApertureValue",
    "BrightnessValue",
    "ExposureBiasValue",
    "MaxApertureValue",
    "MeteringMode",
    "LightSource",
    "Flash",
    "FocalLength",
    "FocalLengthIn35mmFilm",
    "DigitalZoomRatio",
    "WhiteBalance",
    "ExposureMode",
    "SceneCaptureType",
}


IMAGE_TECHNICAL_FIELDS = {
    "Orientation",
    "XResolution",
    "YResolution",
    "ResolutionUnit",
    "ColorSpace",
    "ExifImageWidth",
    "ExifImageHeight",
    "PixelXDimension",
    "PixelYDimension",
    "CompressedBitsPerPixel",
    "BitsPerSample",
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "PlanarConfiguration",
    "YCbCrPositioning",
    "ExifVersion",
    "FlashPixVersion",
    "ComponentsConfiguration",
    "SensingMethod",
    "FileSource",
    "CustomRendered",
    "GainControl",
    "Contrast",
    "Saturation",
    "Sharpness",
}


# ---------------------------------------------------------------------------
# Public EXIF inspection API
# ---------------------------------------------------------------------------


def collect_exif_metadata(img) -> dict:
    """
    Collect EXIF metadata using human-readable tag names.

    Pillow's top-level EXIF object may contain references to nested EXIF
    Image File Directories (IFDs). Those nested fields are collected as
    well so values such as ``UserComment`` are available to the inspector.

    Parameters
    ----------
    img : PIL.Image.Image
        Open Pillow image.

    Returns
    -------
    dict
        EXIF fields keyed by human-readable tag names.
    """

    exif = img.getexif()

    if not exif:
        return {}

    metadata = {}

    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(
            tag_id,
            str(tag_id),
        )

        if tag_id in (EXIF_IFD_TAG, GPS_IFD_TAG):
            continue

        metadata[tag_name] = decode_exif_value(
            tag_name,
            value,
        )

    collect_nested_exif_ifd(
        exif,
        EXIF_IFD_TAG,
        metadata,
    )

    collect_gps_ifd(
        exif,
        metadata,
    )

    return metadata


def prepare_exif_for_display(
    exif: dict,
    ai_source,
) -> dict:
    """
    Prepare EXIF metadata for normal inspection output.

    AI metadata already displayed by the AI inspector is removed from the
    EXIF display so the user does not see the same information twice.

    The dictionary remains flat for compatibility with the existing CLI.
    Category grouping is available separately through
    ``classify_exif_metadata()``.
    """

    display = dict(exif)

    if ai_source is not None:
        source_type, source_name = ai_source

        if source_type == "exif":
            display.pop(
                source_name,
                None,
            )

    return {key: prepare_value_for_display(value) for key, value in display.items()}


def classify_exif_metadata(exif: dict) -> dict[str, dict]:
    """
    Group EXIF fields into human-oriented categories.

    No EXIF field is intentionally discarded. Fields that are not currently
    recognized are placed into ``Other EXIF``.

    Parameters
    ----------
    exif : dict
        EXIF metadata keyed by human-readable tag names.

    Returns
    -------
    dict
        Category names containing dictionaries of EXIF fields.
    """

    sections = {category: {} for category in EXIF_CATEGORY_ORDER}

    for key, value in exif.items():
        category = classify_exif_field(key)

        sections[category][key] = prepare_value_for_display(value)

    return {category: fields for category, fields in sections.items() if fields}


def classify_exif_field(field_name: str) -> str:
    """
    Return the human-oriented category for one EXIF field.
    """

    if field_name == "GPSInfo":
        return "Location"

    if field_name in DESCRIPTIVE_FIELDS:
        return "Descriptive / Personal"

    if field_name in CAMERA_FIELDS:
        return "Camera / Device"

    if field_name in CAPTURE_FIELDS:
        return "Capture Information"

    if field_name in IMAGE_TECHNICAL_FIELDS:
        return "Image / Technical"

    return "Other EXIF"


# ---------------------------------------------------------------------------
# EXIF collection helpers
# ---------------------------------------------------------------------------


def collect_nested_exif_ifd(
    exif,
    ifd_tag: int,
    metadata: dict,
) -> None:
    """
    Add fields from a nested EXIF IFD to the metadata dictionary.
    """

    try:
        nested_ifd = exif.get_ifd(ifd_tag)

    except (KeyError, TypeError, ValueError):
        return

    if not nested_ifd:
        return

    for tag_id, value in nested_ifd.items():
        tag_name = ExifTags.TAGS.get(
            tag_id,
            str(tag_id),
        )

        metadata[tag_name] = decode_exif_value(
            tag_name,
            value,
        )


def collect_gps_ifd(
    exif,
    metadata: dict,
) -> None:
    """
    Collect GPS EXIF fields using readable GPS tag names.
    """

    try:
        gps_ifd = exif.get_ifd(GPS_IFD_TAG)

    except (KeyError, TypeError, ValueError):
        return

    if not gps_ifd:
        return

    gps_metadata = {}

    for tag_id, value in gps_ifd.items():
        tag_name = ExifTags.GPSTAGS.get(
            tag_id,
            str(tag_id),
        )

        gps_metadata[tag_name] = decode_exif_value(
            tag_name,
            value,
        )

    if gps_metadata:
        metadata["GPSInfo"] = gps_metadata


# ---------------------------------------------------------------------------
# EXIF decoding
# ---------------------------------------------------------------------------


def decode_exif_value(
    tag_name: str,
    value,
):
    """
    Decode EXIF values that require special handling.

    ``UserComment`` uses an EXIF-specific eight-byte encoding prefix and is
    not safely decoded with a normal UTF-8 conversion.
    """

    if tag_name == "UserComment" and isinstance(value, bytes):
        return decode_exif_user_comment(value)

    return value


def decode_exif_user_comment(value: bytes) -> str:
    """
    Decode an EXIF UserComment byte string.

    EXIF UserComment begins with an eight-byte character-code prefix such
    as ``ASCII`` or ``UNICODE``.
    """

    if not value:
        return ""

    if len(value) < 8:
        return decode_bytes_fallback(value)

    prefix = value[:8]
    payload = value[8:]

    if prefix.startswith(b"ASCII"):
        return payload.rstrip(b"\x00").decode(
            "ascii",
            errors="replace",
        )

    if prefix.startswith(b"UNICODE"):
        return decode_exif_unicode_payload(payload)

    if prefix.startswith(b"JIS"):
        return payload.rstrip(b"\x00").decode(
            "shift_jis",
            errors="replace",
        )

    return decode_bytes_fallback(value)


def decode_exif_unicode_payload(payload: bytes) -> str:
    """
    Decode a UTF-16 EXIF UserComment payload.

    A byte-order mark is honored when present. Otherwise, the placement of
    null bytes is used to distinguish big-endian from little-endian text.

    Trailing null characters are removed only after UTF-16 decoding so a
    valid byte belonging to the final character is never discarded.
    """

    if not payload:
        return ""

    if payload.startswith(b"\xfe\xff"):
        decoded = payload.decode(
            "utf-16-be",
            errors="replace",
        ).lstrip("\ufeff")

        return decoded.rstrip("\x00")

    if payload.startswith(b"\xff\xfe"):
        decoded = payload.decode(
            "utf-16-le",
            errors="replace",
        ).lstrip("\ufeff")

        return decoded.rstrip("\x00")

    sample = payload[: min(len(payload), 64)]

    even_nulls = sample[0::2].count(0)
    odd_nulls = sample[1::2].count(0)

    if even_nulls > odd_nulls:
        encoding = "utf-16-be"
    else:
        encoding = "utf-16-le"

    decoded = payload.decode(
        encoding,
        errors="replace",
    ).lstrip("\ufeff")

    return decoded.rstrip("\x00")


def decode_bytes_fallback(value: bytes) -> str:
    """
    Decode an unknown byte string without raising a decoding exception.
    """

    for encoding in (
        "utf-8",
        "utf-16",
        "latin-1",
    ):
        try:
            return value.rstrip(b"\x00").decode(encoding)

        except UnicodeDecodeError:
            continue

    return value.decode(
        "latin-1",
        errors="replace",
    )


# ---------------------------------------------------------------------------
# Display-value preparation
# ---------------------------------------------------------------------------


def prepare_value_for_display(value):
    """
    Convert awkward EXIF values into concise, readable representations.

    Structured values such as GPS dictionaries are preserved recursively.
    Large binary EXIF fields are represented by their size rather than
    dumping unreadable byte strings to the terminal.
    """

    if isinstance(value, bytes):
        return describe_binary_value(value)

    if isinstance(value, dict):
        return {key: prepare_value_for_display(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return tuple(prepare_value_for_display(item) for item in value)

    if isinstance(value, list):
        return [prepare_value_for_display(item) for item in value]

    return value


def describe_binary_value(value: bytes) -> str:
    """
    Return a concise description of binary EXIF data.

    Small printable byte strings are decoded when possible. Large or
    non-printable values are represented by byte count rather than emitted
    as terminal line noise.
    """

    if not value:
        return "<binary data: 0 bytes>"

    if len(value) <= 256:
        decoded = try_decode_printable_bytes(value)

        if decoded is not None:
            return decoded

    return f"<binary data: {len(value)} bytes>"


def try_decode_printable_bytes(value: bytes) -> str | None:
    """
    Decode a byte string only when the result is reasonably printable.
    """

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
