"""
jpeg_rewriter.py

Metadata-only JPEG rewriting.

This module replaces or removes selected JPEG metadata segments while copying
the compressed image stream byte-for-byte. JPEG pixels are therefore never
re-encoded as part of metadata stripping.
"""

from pathlib import Path

SOI = b"\xff\xd8"
SOS_MARKER = 0xDA
APP1_MARKER = 0xE1
COM_MARKER = 0xFE

EXIF_HEADER = b"Exif\x00\x00"
XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


def rewrite_jpeg_metadata(
    source: Path,
    destination: Path,
    exif_bytes: bytes | None,
    remove_xmp: bool = False,
    remove_comments: bool = False,
) -> None:
    """
    Rewrite JPEG metadata without recompressing image data.

    Existing EXIF segments are replaced by ``exif_bytes``. XMP and JPEG comment
    segments may optionally be removed. All unrelated JPEG segments and the
    complete compressed scan stream are copied unchanged.
    """

    data = source.read_bytes()

    if not data.startswith(SOI):
        raise ValueError("not a valid JPEG file")

    output = bytearray(SOI)
    position = len(SOI)
    exif_written = False

    while position < len(data):
        marker_start = position

        if data[position] != 0xFF:
            raise ValueError("invalid JPEG marker structure")

        while position < len(data) and data[position] == 0xFF:
            position += 1

        if position >= len(data):
            raise ValueError("truncated JPEG marker")

        marker = data[position]
        position += 1

        if marker == SOS_MARKER:
            if exif_bytes and not exif_written:
                output.extend(build_app1_segment(exif_bytes))

            output.extend(data[marker_start:])
            break

        if marker in {
            0x01,
            0xD8,
            0xD9,
            0xD0,
            0xD1,
            0xD2,
            0xD3,
            0xD4,
            0xD5,
            0xD6,
            0xD7,
        }:
            output.extend(data[marker_start:position])
            continue

        if position + 2 > len(data):
            raise ValueError("truncated JPEG segment")

        segment_length = int.from_bytes(
            data[position : position + 2],
            "big",
        )

        if segment_length < 2:
            raise ValueError("invalid JPEG segment length")

        segment_end = position + segment_length

        if segment_end > len(data):
            raise ValueError("truncated JPEG segment")

        segment = data[marker_start:segment_end]
        payload = data[position + 2 : segment_end]

        position = segment_end

        if marker == APP1_MARKER and payload.startswith(EXIF_HEADER):
            if exif_bytes and not exif_written:
                output.extend(build_app1_segment(exif_bytes))
                exif_written = True

            continue

        if marker == APP1_MARKER and remove_xmp and payload.startswith(XMP_HEADER):
            continue

        if marker == COM_MARKER and remove_comments:
            continue

        output.extend(segment)

    destination.write_bytes(output)


def build_app1_segment(exif_bytes: bytes) -> bytes:
    """
    Build a JPEG APP1 segment containing serialized EXIF data.
    """

    if not exif_bytes.startswith(EXIF_HEADER):
        raise ValueError("EXIF data is missing the EXIF header")

    segment_length = len(exif_bytes) + 2

    if segment_length > 65535:
        raise ValueError("EXIF data is too large for a JPEG APP1 segment")

    return b"\xff\xe1" + segment_length.to_bytes(2, "big") + exif_bytes
