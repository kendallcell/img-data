"""
exif_inspector.py

Functions for collecting, decoding, and presenting EXIF metadata.

This module is responsible only for EXIF inspection.  It does not inspect
AI metadata and it does not modify image files.
"""

from PIL import ExifTags

EXIF_IFD_TAG = 0x8769
GPS_IFD_TAG = 0x8825


def collect_exif_metadata(img):
    """
    Collect EXIF metadata using human-readable tag names.
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


def collect_nested_exif_ifd(
    exif,
    ifd_tag,
    metadata,
):
    """
    Read a nested EXIF Image File Directory.
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
    metadata,
):
    """
    Read the GPS Image File Directory.
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

        gps_metadata[tag_name] = value

    if gps_metadata:
        metadata["GPSInfo"] = gps_metadata


def decode_exif_value(
    tag_name,
    value,
):
    """
    Decode EXIF values requiring special handling.
    """

    if tag_name == "UserComment" and isinstance(value, bytes):
        return decode_exif_user_comment(value)

    return value


def decode_exif_user_comment(value):
    """
    Decode an EXIF UserComment value.
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


def decode_exif_unicode_payload(payload):
    """
    Decode UTF-16 EXIF text.
    """

    payload = payload.rstrip(b"\x00")

    if not payload:
        return ""

    if payload.startswith(b"\xfe\xff"):
        return payload.decode(
            "utf-16-be",
            errors="replace",
        ).lstrip("\ufeff")

    if payload.startswith(b"\xff\xfe"):
        return payload.decode(
            "utf-16-le",
            errors="replace",
        ).lstrip("\ufeff")

    sample = payload[:64]

    even_nulls = sample[0::2].count(0)
    odd_nulls = sample[1::2].count(0)

    encoding = "utf-16-be" if even_nulls > odd_nulls else "utf-16-le"

    return payload.decode(
        encoding,
        errors="replace",
    ).lstrip("\ufeff")


def decode_bytes_fallback(value):
    """
    Decode an unknown byte string.
    """

    for encoding in (
        "utf-8",
        "utf-16",
        "latin-1",
    ):
        try:
            return value.rstrip(b"\x00").decode(encoding)

        except UnicodeDecodeError:
            pass

    return value.decode(
        "latin-1",
        errors="replace",
    )


def prepare_exif_for_display(
    exif,
    ai_source,
):
    """
    Remove AI metadata already shown elsewhere.
    """

    display = dict(exif)

    if ai_source is None:
        return display

    source_type, source_name = ai_source

    if source_type == "exif":
        display.pop(
            source_name,
            None,
        )

    return display
