"""
Tests for combined metadata stripping.

These tests verify that the ``--all`` stripping policy removes both AI and
privacy-sensitive metadata while preserving image content, technical metadata,
and the original filename extension.
"""

from pathlib import Path

import pytest
from PIL import Image

from img_data.inspector import inspect_image
from img_data.metadata_stripper import (
    build_all_stripped_filename,
    strip_all_metadata,
)

DATA_DIR = Path("tests/data")
OTHER_DATA_DIR = DATA_DIR / "other"


def test_build_all_stripped_filename_for_png():
    source = Path("example.png")

    result = build_all_stripped_filename(source)

    assert result == Path("example-All-Stripped.png")


def test_build_all_stripped_filename_for_jpeg():
    source = Path("example.jpeg")

    result = build_all_stripped_filename(source)

    assert result == Path("example-All-Stripped.jpeg")


def test_build_all_stripped_filename_for_jpg():
    source = Path("example.jpg")

    result = build_all_stripped_filename(source)

    assert result == Path("example-All-Stripped.jpg")


def test_strip_all_png_removes_ai_metadata(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-All-Stripped.png"

    strip_all_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_all_png_removes_private_metadata(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-All-Stripped.png"

    strip_all_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "Comment" not in result["container"]
    assert "xmp" not in result["container"]
    assert "XML:com.adobe.xmp" not in result["container"]
    assert "Raw profile type exif" not in result["container"]

    assert "ImageDescription" not in result["exif"]
    assert "UserComment" not in result["exif"]
    assert "Software" not in result["exif"]
    assert "DateTime" not in result["exif"]


def test_strip_all_png_preserves_technical_exif(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-All-Stripped.png"

    strip_all_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert result["exif"]["Orientation"] == 1
    assert result["exif"]["ColorSpace"] == 1
    assert result["exif"]["ImageWidth"] == 896
    assert result["exif"]["ImageLength"] == 1152


def test_strip_all_png_preserves_icc_profile(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-All-Stripped.png"

    with Image.open(source) as original:
        original_icc = original.info.get("icc_profile")

    strip_all_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped_icc = stripped.info.get("icc_profile")

    assert original_icc is not None
    assert stripped_icc == original_icc


def test_strip_all_png_preserves_pixels_exactly(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-All-Stripped.png"

    with Image.open(source) as original:
        original.load()

        original_mode = original.mode
        original_size = original.size
        original_pixels = original.tobytes()

    strip_all_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped.load()

        assert stripped.mode == original_mode
        assert stripped.size == original_size
        assert stripped.tobytes() == original_pixels


def test_strip_all_png_output_can_be_opened_by_pillow(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-All-Stripped.png"

    strip_all_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "PNG"


def test_strip_all_jpg_removes_ai_metadata(tmp_path):
    source = OTHER_DATA_DIR / "Attorney6b.jpg"
    destination = tmp_path / "Attorney6b-All-Stripped.jpg"

    strip_all_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_all_jpg_preserves_jpg_extension(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = strip_all_metadata(source)

    assert destination.name == "Attorney6b-All-Stripped.jpg"
    assert destination.suffix == ".jpg"
    assert destination.exists()


def test_strip_all_jpg_preserves_dimensions(tmp_path):
    source = OTHER_DATA_DIR / "Attorney6b.jpg"
    destination = tmp_path / "Attorney6b-All-Stripped.jpg"

    original = inspect_image(source)

    strip_all_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]


def test_strip_all_jpg_output_can_be_opened_by_pillow(tmp_path):
    source = OTHER_DATA_DIR / "Attorney6b.jpg"
    destination = tmp_path / "Attorney6b-All-Stripped.jpg"

    strip_all_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "JPEG"


def test_existing_destination_requires_force(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-All-Stripped.png"

    destination.write_bytes(b"existing output")

    with pytest.raises(FileExistsError):
        strip_all_metadata(
            source,
            destination,
        )


def test_existing_destination_is_not_modified_without_force(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-All-Stripped.png"

    original_contents = b"existing output"
    destination.write_bytes(original_contents)

    with pytest.raises(FileExistsError):
        strip_all_metadata(
            source,
            destination,
        )

    assert destination.read_bytes() == original_contents


def test_force_overwrites_existing_jpg_destination(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = tmp_path / "Attorney6b-All-Stripped.jpg"
    destination.write_bytes(b"existing output")

    result = strip_all_metadata(
        source,
        force=True,
    )

    assert result == destination
    assert result.suffix == ".jpg"

    with Image.open(result) as img:
        img.load()

        assert img.format == "JPEG"
