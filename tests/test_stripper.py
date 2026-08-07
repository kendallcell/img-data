from pathlib import Path

import pytest
from PIL import Image

from img_data.inspector import inspect_image
from img_data.stripper import (
    build_ai_stripped_filename,
    strip_ai_metadata,
)

DATA_DIR = Path("tests/data")
OTHER_DATA_DIR = DATA_DIR / "other"


def test_build_ai_stripped_filename_for_png():
    source = Path("example.png")

    result = build_ai_stripped_filename(source)

    assert result == Path("example-AI-Stripped.png")


def test_build_ai_stripped_filename_for_jpeg():
    source = Path("example.jpeg")

    result = build_ai_stripped_filename(source)

    assert result == Path("example-AI-Stripped.jpeg")


def test_strip_png_removes_ai_metadata(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    strip_ai_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_png_preserves_dimensions(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    original = inspect_image(source)

    strip_ai_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]


def test_strip_png_preserves_mode(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    original = inspect_image(source)

    strip_ai_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["mode"] == original["mode"]


def test_strip_png_preserves_format(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    strip_ai_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["format"] == "PNG"


def test_strip_png_output_can_be_opened_by_pillow(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    strip_ai_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.width > 0
        assert img.height > 0


def test_strip_png_preserves_icc_profile(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-AI-Stripped.png"

    with Image.open(source) as original:
        original_icc = original.info.get("icc_profile")

    strip_ai_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped_icc = stripped.info.get("icc_profile")

    assert stripped_icc == original_icc


def test_strip_png_without_ai_metadata_remains_valid(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-AI-Stripped.png"

    strip_ai_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "PNG"
        assert img.size == (896, 1152)


def test_strip_jpeg_removes_ai_metadata(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-AI-Stripped.jpeg"

    strip_ai_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_jpeg_preserves_dimensions(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-AI-Stripped.jpeg"

    original = inspect_image(source)

    strip_ai_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]


def test_strip_jpeg_output_can_be_opened_by_pillow(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-AI-Stripped.jpeg"

    strip_ai_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "JPEG"


def test_existing_destination_requires_force_programmatically(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    destination.write_bytes(b"existing output")

    with pytest.raises(FileExistsError):
        strip_ai_metadata(
            source,
            destination,
        )


def test_existing_destination_is_not_modified_without_force(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    original_contents = b"existing output"
    destination.write_bytes(original_contents)

    with pytest.raises(FileExistsError):
        strip_ai_metadata(
            source,
            destination,
        )

    assert destination.read_bytes() == original_contents


def test_force_overwrites_existing_destination(tmp_path):
    source = DATA_DIR / "Attorney2.png"
    destination = tmp_path / "Attorney2-AI-Stripped.png"

    destination.write_bytes(b"existing output")

    strip_ai_metadata(
        source,
        destination,
        force=True,
    )

    result = inspect_image(destination)

    assert result["format"] == "PNG"
    assert result["ai"] is None
