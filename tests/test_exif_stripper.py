"""
Tests for privacy-oriented EXIF metadata stripping.

These tests verify that identifying, descriptive, location, and editing
metadata is removed while useful technical image metadata and image pixels
remain intact.
"""

from pathlib import Path

import pytest
from PIL import Image

from img_data.exif_stripper import (
    build_exif_stripped_filename,
    remove_private_exif_fields,
    strip_exif_metadata,
)
from img_data.inspector import inspect_image

DATA_DIR = Path("tests/data")
OTHER_DATA_DIR = DATA_DIR / "other"


def test_build_exif_stripped_filename_for_png():
    source = Path("example.png")

    result = build_exif_stripped_filename(source)

    assert result == Path("example-EXIF-Stripped.png")


def test_build_exif_stripped_filename_for_jpeg():
    source = Path("example.jpeg")

    result = build_exif_stripped_filename(source)

    assert result == Path("example-EXIF-Stripped.jpeg")


def test_build_exif_stripped_filename_for_jpg():
    source = Path("example.jpg")

    result = build_exif_stripped_filename(source)

    assert result == Path("example-EXIF-Stripped.jpg")


def test_remove_private_exif_fields_removes_personal_data():
    exif = Image.Exif()

    exif[315] = "Jane Photographer"
    exif[270] = "Personal description"
    exif[305] = "Editing Software"
    exif[306] = "2026:08:07 12:00:00"

    remove_private_exif_fields(exif)

    assert 315 not in exif
    assert 270 not in exif
    assert 305 not in exif
    assert 306 not in exif


def test_remove_private_exif_fields_removes_device_identity():
    exif = Image.Exif()

    exif[271] = "Example Camera Company"
    exif[272] = "Example Camera Model"
    exif[42033] = "BODY-123456"

    remove_private_exif_fields(exif)

    assert 271 not in exif
    assert 272 not in exif
    assert 42033 not in exif


def test_remove_private_exif_fields_removes_gps_pointer():
    exif = Image.Exif()

    exif[34853] = 123

    remove_private_exif_fields(exif)

    assert 34853 not in exif


def test_remove_private_exif_fields_preserves_technical_data():
    exif = Image.Exif()

    exif[274] = 1
    exif[282] = 300
    exif[283] = 300
    exif[33434] = 0.008
    exif[33437] = 2.8

    remove_private_exif_fields(exif)

    assert exif[274] == 1
    assert exif[282] == 300
    assert exif[283] == 300
    assert exif[33434] == 0.008
    assert exif[33437] == 2.8


def test_strip_png_removes_personal_exif_metadata(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "ImageDescription" not in result["exif"]
    assert "UserComment" not in result["exif"]
    assert "Software" not in result["exif"]
    assert "DateTime" not in result["exif"]


def test_strip_png_preserves_technical_exif_metadata(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)
    exif = result["exif"]

    assert exif["BitsPerSample"] == (8, 8, 8)
    assert exif["ResolutionUnit"] == 3
    assert exif["Orientation"] == 1
    assert exif["ColorSpace"] == 1
    assert exif["ImageWidth"] == 896
    assert exif["ImageLength"] == 1152


def test_strip_png_removes_comment_container_metadata(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "Comment" not in result["container"]


def test_strip_png_removes_xmp_metadata(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "xmp" not in result["container"]
    assert "XML:com.adobe.xmp" not in result["container"]


def test_strip_png_removes_raw_exif_profile(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "Raw profile type exif" not in result["container"]


def test_strip_png_preserves_cleaned_exif_block(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "exif" in result["container"]
    assert result["exif"]


def test_strip_png_preserves_icc_profile(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    with Image.open(source) as original:
        original_icc = original.info.get("icc_profile")

    strip_exif_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped_icc = stripped.info.get("icc_profile")

    assert original_icc is not None
    assert stripped_icc == original_icc


def test_strip_png_preserves_dpi(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "dpi" in result["container"]


def test_strip_png_preserves_dimensions_and_mode(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    original = inspect_image(source)

    strip_exif_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]
    assert stripped["mode"] == original["mode"]
    assert stripped["format"] == original["format"]


def test_strip_png_preserves_pixels_exactly(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    with Image.open(source) as original:
        original.load()

        original_mode = original.mode
        original_size = original.size
        original_pixels = original.tobytes()

    strip_exif_metadata(
        source,
        destination,
    )

    with Image.open(destination) as stripped:
        stripped.load()

        assert stripped.mode == original_mode
        assert stripped.size == original_size
        assert stripped.tobytes() == original_pixels


def test_strip_png_output_can_be_opened_by_pillow(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    strip_exif_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "PNG"
        assert img.size == (896, 1152)


def test_existing_destination_requires_force(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    destination.write_bytes(b"existing output")

    with pytest.raises(FileExistsError):
        strip_exif_metadata(
            source,
            destination,
        )


def test_existing_destination_is_not_modified_without_force(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    original_contents = b"existing output"
    destination.write_bytes(original_contents)

    with pytest.raises(FileExistsError):
        strip_exif_metadata(
            source,
            destination,
        )

    assert destination.read_bytes() == original_contents


def test_force_overwrites_existing_destination(tmp_path):
    source = DATA_DIR / "Attorney1.png"
    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    destination.write_bytes(b"existing output")

    strip_exif_metadata(
        source,
        destination,
        force=True,
    )

    result = inspect_image(destination)

    assert result["format"] == "PNG"
    assert "Comment" not in result["container"]
    assert "UserComment" not in result["exif"]


def test_strip_jpeg_removes_private_ai_comment(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-EXIF-Stripped.jpeg"

    strip_exif_metadata(
        source,
        destination,
    )

    result = inspect_image(destination)

    assert "UserComment" not in result["exif"]
    assert result["ai"] is None


def test_strip_jpeg_preserves_dimensions(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-EXIF-Stripped.jpeg"

    original = inspect_image(source)

    strip_exif_metadata(
        source,
        destination,
    )

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]


def test_strip_jpeg_output_can_be_opened_by_pillow(tmp_path):
    source = OTHER_DATA_DIR / "Attorney8.jpeg"
    destination = tmp_path / "Attorney8-EXIF-Stripped.jpeg"

    strip_exif_metadata(
        source,
        destination,
    )

    with Image.open(destination) as img:
        img.load()

        assert img.format == "JPEG"


def test_jpg_default_output_preserves_jpg_extension(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = strip_exif_metadata(source)

    assert destination.name == "Attorney6b-EXIF-Stripped.jpg"
    assert destination.suffix == ".jpg"
    assert destination.exists()


def test_strip_jpg_output_can_be_opened_by_pillow(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = strip_exif_metadata(source)

    with Image.open(destination) as img:
        img.load()

        assert img.format == "JPEG"


def test_strip_jpg_preserves_dimensions(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    original = inspect_image(source)

    destination = strip_exif_metadata(source)

    stripped = inspect_image(destination)

    assert stripped["width"] == original["width"]
    assert stripped["height"] == original["height"]


def test_force_on_jpg_overwrites_same_jpg_destination(tmp_path):
    specimen = OTHER_DATA_DIR / "Attorney6b.jpg"
    source = tmp_path / specimen.name

    source.write_bytes(specimen.read_bytes())

    destination = tmp_path / "Attorney6b-EXIF-Stripped.jpg"
    destination.write_bytes(b"existing output")

    result = strip_exif_metadata(
        source,
        force=True,
    )

    assert result == destination
    assert result.suffix == ".jpg"

    with Image.open(result) as img:
        img.load()

        assert img.format == "JPEG"
