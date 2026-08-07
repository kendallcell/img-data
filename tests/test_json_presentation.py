import base64
import json
from fractions import Fraction

from img_data.json_presentation import (
    encode_binary_value,
    make_json_safe,
    print_json_inspection,
)


def test_binary_value_is_encoded_losslessly():
    value = b"\x00\xff\x10"

    result = encode_binary_value(value)

    assert result == {
        "type": "binary",
        "size": 3,
        "encoding": "base64",
        "data": "AP8Q",
    }


def test_binary_value_can_be_round_tripped():
    value = b"\x00\x01\x02binary metadata\xff"

    result = encode_binary_value(value)

    decoded = base64.b64decode(result["data"])

    assert decoded == value


def test_make_json_safe_converts_tuple_to_list():
    result = make_json_safe(
        {
            "dpi": (
                300,
                300,
            ),
        }
    )

    assert result == {
        "dpi": [
            300,
            300,
        ],
    }


def test_make_json_safe_handles_nested_binary_data():
    result = make_json_safe(
        {
            "container": {
                "profile": b"ABC",
            },
        }
    )

    assert result == {
        "container": {
            "profile": {
                "type": "binary",
                "size": 3,
                "encoding": "base64",
                "data": "QUJD",
            },
        },
    }


def test_make_json_safe_preserves_native_json_values():
    value = {
        "text": "hello",
        "integer": 42,
        "float": 3.5,
        "boolean": True,
        "nothing": None,
    }

    result = make_json_safe(value)

    assert result == value


def test_make_json_safe_normalizes_specialized_number():
    result = make_json_safe(Fraction(1, 2))

    assert result == 0.5


def test_json_presentation_outputs_one_json_document_per_line(
    capsys,
):
    data = {
        "filename": "example.png",
        "filesize": 1234,
        "format": "PNG",
        "mode": "RGB",
        "width": 100,
        "height": 200,
        "container": {},
        "exif": {},
        "ai": None,
    }

    print_json_inspection(data)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out.count("\n") == 1

    result = json.loads(captured.out)

    assert result == data


def test_json_presentation_is_compact(
    capsys,
):
    data = {
        "filename": "example.png",
        "container": {},
        "exif": {},
        "ai": None,
    }

    print_json_inspection(data)

    captured = capsys.readouterr()

    assert "\n " not in captured.out
    assert ": " not in captured.out
    assert ", " not in captured.out


def test_json_presentation_preserves_unicode(
    capsys,
):
    data = {
        "comment": "café — metadata",
    }

    print_json_inspection(data)

    captured = capsys.readouterr()

    assert "café" in captured.out
    assert "—" in captured.out

    result = json.loads(captured.out)

    assert result["comment"] == "café — metadata"
