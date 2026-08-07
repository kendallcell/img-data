"""
json_presentation.py

JSON presentation for img-data inspection results.

This module converts structured inspection data into JSON-safe values and
writes one compact JSON document to standard output. It does not inspect,
parse, classify, or modify image metadata.
"""

import base64
import json
from numbers import Number


def print_json_inspection(data: dict) -> None:
    """
    Print one complete inspection result as compact JSON.

    The structure produced by the inspector is preserved, including the
    top-level ``container``, ``exif``, and ``ai`` namespaces. Each invocation
    produces exactly one JSON document on one line, making the output suitable
    for shell pipelines and JSON Lines inventories.
    """

    json_data = make_json_safe(data)

    print(
        json.dumps(
            json_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def make_json_safe(value):
    """
    Recursively convert inspection data into JSON-compatible values.

    Binary data is preserved losslessly using Base64 together with its
    original byte count. Tuples become JSON arrays, and numeric objects that
    are not natively handled by the JSON encoder are converted to ordinary
    Python numbers.
    """

    if isinstance(value, bytes):
        return encode_binary_value(value)

    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (tuple, list)):
        return [make_json_safe(item) for item in value]

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Number):
        return normalize_number(value)

    return str(value)


def encode_binary_value(value: bytes) -> dict:
    """
    Represent binary metadata losslessly in a JSON-compatible structure.

    Base64 avoids corrupting arbitrary binary metadata while the size field
    lets consumers understand the original payload without decoding it.
    """

    encoded = base64.b64encode(value).decode("ascii")

    return {
        "type": "binary",
        "size": len(value),
        "encoding": "base64",
        "data": encoded,
    }


def normalize_number(value):
    """
    Convert specialized numeric objects to ordinary JSON-compatible numbers.

    Some EXIF values are represented by Pillow using numeric classes that
    behave like floats or integers but are not directly serializable by the
    standard JSON encoder.
    """

    try:
        integer_value = int(value)

        if value == integer_value:
            return integer_value

    except (TypeError, ValueError, OverflowError):
        pass

    try:
        return float(value)

    except (TypeError, ValueError, OverflowError):
        return str(value)
