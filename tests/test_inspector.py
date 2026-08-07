from pathlib import Path

import pytest

from img_data.inspector import (
    inspect_image,
    parse_ai_metadata,
    tokenize_settings,
)

DATA_DIR = Path("tests/data")
OTHER_DATA_DIR = DATA_DIR / "other"


ALL_IMAGE_FILES = [
    DATA_DIR / "Attorney1.png",
    DATA_DIR / "Attorney2.png",
    DATA_DIR / "Attorney3.png",
    DATA_DIR / "Attorney4.png",
    DATA_DIR / "Attorney5.png",
    DATA_DIR / "Court1.png",
    DATA_DIR / "Logo1.png",
    DATA_DIR / "Logo2.png",
    DATA_DIR / "Logo3.png",
    DATA_DIR / "Logo4.png",
    OTHER_DATA_DIR / "Attorney6.jpeg",
    OTHER_DATA_DIR / "Attorney7.png",
    OTHER_DATA_DIR / "Attorney8.jpeg",
    OTHER_DATA_DIR / "Attorney9.png",
    OTHER_DATA_DIR / "Court2.png",
]


def test_can_read_png():
    data = inspect_image(DATA_DIR / "Attorney1.png")

    assert data["format"] == "PNG"
    assert data["width"] > 0
    assert data["height"] > 0


@pytest.mark.parametrize("image_path", ALL_IMAGE_FILES)
def test_all_specimen_images_can_be_inspected(image_path):
    data = inspect_image(image_path)

    assert data["filename"] == image_path.name
    assert data["filesize"] > 0
    assert data["format"] in {"PNG", "JPEG"}
    assert data["width"] > 0
    assert data["height"] > 0
    assert "png_info" in data
    assert "exif" in data
    assert "ai" in data


def test_image_without_ai_metadata_returns_none():
    data = inspect_image(DATA_DIR / "Attorney1.png")

    assert data["ai"] is None


def test_attorney2_parses_core_generation_settings():
    data = inspect_image(DATA_DIR / "Attorney2.png")
    ai = data["ai"]

    assert ai is not None
    assert ai["prompt"].startswith("<1woman>")
    assert ai["negative_prompt"] == "worst quality,"
    assert ai["settings"]["Steps"] == "20"
    assert ai["settings"]["Sampler"] == "Euler"
    assert ai["settings"]["CFG scale"] == "5"
    assert ai["settings"]["Seed"] == "1685296728"
    assert ai["settings"]["Size"] == "896x1152"
    assert ai["settings"]["Model"] == "realvisxlV50_v50Bakedvae"
    assert ai["settings"]["Model hash"] == "6a35a78557"


def test_attorney2_groups_adetailer_metadata():
    data = inspect_image(DATA_DIR / "Attorney2.png")
    ai = data["ai"]

    assert ai is not None
    assert "ADetailer" in ai["plugins"]

    adetailer = ai["plugins"]["ADetailer"]

    assert adetailer["model"] == "face_yolov8n.pt"
    assert adetailer["confidence"] == "0.3"
    assert adetailer["model 2nd"] == "hand_yolov8n.pt"
    assert adetailer["prompt 2nd"] == '"normal hand, natural looking"'
    assert adetailer["version"] == "26.2.0"


def test_court2_keeps_multiword_settings_out_of_plugins():
    data = inspect_image(OTHER_DATA_DIR / "Court2.png")
    ai = data["ai"]

    assert ai is not None

    assert ai["settings"]["CFG scale"] == "1.5"
    assert ai["settings"]["Model hash"] == "f53945ec37"
    assert ai["settings"]["Model"] == "wildcardxXLLIGHTNING_wildcardxXL"

    assert "CFG" not in ai["plugins"]
    assert "Model" not in ai["plugins"]


def test_court2_preserves_embedded_json():
    data = inspect_image(OTHER_DATA_DIR / "Court2.png")
    ai = data["ai"]

    assert ai is not None
    assert ai["settings"]["Hashes"] == '{"model": "f53945ec37"}'


def test_court2_always_contains_other_dictionary():
    data = inspect_image(OTHER_DATA_DIR / "Court2.png")
    ai = data["ai"]

    assert ai is not None
    assert "other" in ai
    assert ai["other"] == {}


def test_attorney8_detects_ai_metadata_from_jpeg_exif():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")
    ai = data["ai"]

    assert data["format"] == "JPEG"
    assert ai is not None
    assert ai["prompt"] == "female lawyer."


def test_attorney8_parses_negative_prompt_from_exif():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")
    ai = data["ai"]

    assert ai is not None
    assert ai["negative_prompt"] == "low quality,  bad resolution"


def test_attorney8_parses_generation_settings_from_exif():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")
    ai = data["ai"]

    assert ai is not None
    assert ai["settings"]["Steps"] == "25"
    assert ai["settings"]["Sampler"] == "DPM++ 2M"
    assert ai["settings"]["CFG scale"] == "7"
    assert ai["settings"]["Seed"] == "597991048"
    assert ai["settings"]["Size"] == "832x1216"
    assert ai["settings"]["Clip skip"] == "2"


def test_attorney8_preserves_civitai_resources():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")
    ai = data["ai"]

    assert ai is not None

    expected = (
        '[{"type":"checkpoint","modelVersionId":128078},'
        '{"type":"lora","weight":1,"modelVersionId":293991}]'
    )

    assert ai["other"]["Civitai resources"] == expected


def test_attorney8_does_not_duplicate_ai_usercomment_in_exif_output():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")

    assert "UserComment" not in data["exif"]


def test_attorney8_preserves_raw_ai_metadata():
    data = inspect_image(OTHER_DATA_DIR / "Attorney8.jpeg")
    ai = data["ai"]

    assert ai is not None
    assert "female lawyer." in ai["raw"]
    assert "Negative prompt:" in ai["raw"]
    assert "Civitai resources:" in ai["raw"]


def test_parser_returns_consistent_schema():
    metadata = (
        "A test image\n"
        "Negative prompt: blurry\n"
        "Steps: 10, Sampler: Euler, Seed: 123"
    )

    ai = parse_ai_metadata(metadata)

    assert ai is not None
    assert set(ai) == {
        "prompt",
        "negative_prompt",
        "settings",
        "plugins",
        "other",
        "raw",
    }


def test_parser_preserves_multiline_prompt():
    metadata = (
        "A lawyer in court\n"
        "BREAK\n"
        "dramatic lighting\n"
        "Negative prompt: blurry\n"
        "Steps: 10, Sampler: Euler"
    )

    ai = parse_ai_metadata(metadata)

    assert ai is not None
    assert ai["prompt"] == "A lawyer in court\nBREAK\ndramatic lighting"
    assert ai["negative_prompt"] == "blurry"


def test_parser_handles_missing_negative_prompt():
    metadata = "A clean product photograph\nSteps: 8, Sampler: Euler"

    ai = parse_ai_metadata(metadata)

    assert ai is not None
    assert ai["prompt"] == "A clean product photograph"
    assert ai["negative_prompt"] == ""
    assert ai["settings"]["Steps"] == "8"
    assert ai["settings"]["Sampler"] == "Euler"


def test_tokenizer_preserves_comma_inside_quoted_value():
    text = (
        'Steps: 20, ADetailer prompt 2nd: "normal hand, natural looking", ' "Seed: 123"
    )

    tokens = tokenize_settings(text)

    assert tokens == [
        ("Steps", "20"),
        ("ADetailer prompt 2nd", '"normal hand, natural looking"'),
        ("Seed", "123"),
    ]


def test_tokenizer_preserves_embedded_json():
    text = 'Steps: 6, Hashes: {"model": "abc123", "vae": "def456"}, ' "Seed: 987"

    tokens = tokenize_settings(text)

    assert tokens == [
        ("Steps", "6"),
        ("Hashes", '{"model": "abc123", "vae": "def456"}'),
        ("Seed", "987"),
    ]


def test_unknown_field_is_preserved_in_other_metadata():
    metadata = "A test image\n" "Steps: 10, Sampler: Euler, MagicPlugin strength: 0.75"

    ai = parse_ai_metadata(metadata)

    assert ai is not None
    assert ai["other"]["MagicPlugin strength"] == "0.75"


def test_raw_metadata_is_preserved_exactly():
    metadata = "A test image\n" "Negative prompt: blurry\n" "Steps: 10, Sampler: Euler"

    ai = parse_ai_metadata(metadata)

    assert ai is not None
    assert ai["raw"] == metadata
