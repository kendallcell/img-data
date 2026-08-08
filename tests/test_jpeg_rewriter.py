"""
Tests for metadata-only JPEG rewriting.

These tests verify that JPEG metadata segments may change while the complete
compressed scan stream remains byte-for-byte identical.
"""

from pathlib import Path

import pytest
from PIL import Image

from img_data.exif_stripper import strip_exif_metadata
from img_data.metadata_stripper import strip_all_metadata

OTHER_DATA_DIR = Path("tests/data/other")


def jpeg_scan_stream(path: Path) -> bytes:
    """
    Return the JPEG byte stream beginning with the Start Of Scan marker.

    Everything from SOS through end-of-file includes the compressed image
    stream. Equality therefore proves that image data was not recompressed.
    """

    data = path.read_bytes()

    if not data.startswith(b"\xff\xd8"):
        raise ValueError("not a JPEG file")

    position = 2

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

        if marker == 0xDA:
            return data[marker_start:]

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
            continue

        if position + 2 > len(data):
            raise ValueError("truncated JPEG segment")

        segment_length = int.from_bytes(
            data[position : position + 2],
            "big",
        )

        if segment_length < 2:
            raise ValueError("invalid JPEG segment length")

        position += segment_length

    raise ValueError("JPEG contains no Start Of Scan marker")


def test_scan_stream_helper_rejects_non_jpeg(tmp_path):
    path = tmp_path / "not-a-jpeg.jpg"
    path.write_bytes(b"not a JPEG")

    with pytest.raises(ValueError):
        jpeg_scan_stream(path)


def test_scan_stream_helper_finds_real_jpeg_data():
    source = OTHER_DATA_DIR / "Attorney6b.jpg"

    scan = jpeg_scan_stream(source)

    assert scan.startswith(b"\xff\xda")
    assert len(scan) > 100


def test_exif_stripping_preserves_jpeg_scan_stream(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-EXIF-Stripped.jpeg"

    original_scan = jpeg_scan_stream(source)

    strip_exif_metadata(
        source,
        destination,
    )

    stripped_scan = jpeg_scan_stream(destination)

    assert stripped_scan == original_scan


def test_all_stripping_preserves_jpg_scan_stream(tmp_path):
    source = OTHER_DATA_DIR / "Attorney6b.jpg"
    destination = tmp_path / "Attorney6b-All-Stripped.jpg"

    original_scan = jpeg_scan_stream(source)

    strip_all_metadata(
        source,
        destination,
    )

    stripped_scan = jpeg_scan_stream(destination)

    assert stripped_scan == original_scan


def test_jpeg_dimensions_remain_identical_after_all_strip(tmp_path):
    source = OTHER_DATA_DIR / "Attorney6b.jpg"
    destination = tmp_path / "Attorney6b-All-Stripped.jpg"

    with Image.open(source) as original:
        original_size = original.size
        original_mode = original.mode

    strip_all_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped.load()

        assert stripped.size == original_size
        assert stripped.mode == original_mode


def test_jpg_extension_remains_jpg_after_all_strip(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = strip_all_metadata(source)

    assert source.suffix == ".jpg"
    assert destination.suffix == ".jpg"
