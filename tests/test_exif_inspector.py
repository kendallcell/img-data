from img_data.exif_inspector import (
    classify_exif_field,
    classify_exif_metadata,
    decode_exif_unicode_payload,
    decode_exif_user_comment,
    describe_binary_value,
    prepare_value_for_display,
)


def test_classifies_descriptive_personal_fields():
    assert classify_exif_field("Artist") == "Descriptive / Personal"
    assert classify_exif_field("Copyright") == "Descriptive / Personal"
    assert classify_exif_field("UserComment") == "Descriptive / Personal"


def test_classifies_camera_device_fields():
    assert classify_exif_field("Make") == "Camera / Device"
    assert classify_exif_field("Model") == "Camera / Device"
    assert classify_exif_field("Software") == "Camera / Device"
    assert classify_exif_field("BodySerialNumber") == "Camera / Device"
    assert classify_exif_field("LensSerialNumber") == "Camera / Device"


def test_classifies_capture_information_fields():
    assert classify_exif_field("DateTimeOriginal") == "Capture Information"
    assert classify_exif_field("ExposureTime") == "Capture Information"
    assert classify_exif_field("FNumber") == "Capture Information"
    assert classify_exif_field("FocalLength") == "Capture Information"


def test_classifies_location_fields():
    assert classify_exif_field("GPSInfo") == "Location"


def test_classifies_image_technical_fields():
    assert classify_exif_field("Orientation") == "Image / Technical"
    assert classify_exif_field("XResolution") == "Image / Technical"
    assert classify_exif_field("YResolution") == "Image / Technical"
    assert classify_exif_field("ColorSpace") == "Image / Technical"


def test_unknown_field_falls_back_to_other_exif():
    assert classify_exif_field("SomeFutureExifTag") == "Other EXIF"


def test_classify_exif_metadata_groups_fields():
    exif = {
        "Artist": "Jane Example",
        "Make": "Canon",
        "ExposureTime": "1/125",
        "GPSInfo": {
            "GPSLatitude": (41, 52, 0),
            "GPSLongitude": (87, 37, 0),
        },
        "Orientation": 1,
        "MysteryTag": "mystery",
    }

    result = classify_exif_metadata(exif)

    assert result["Descriptive / Personal"]["Artist"] == "Jane Example"
    assert result["Camera / Device"]["Make"] == "Canon"
    assert result["Capture Information"]["ExposureTime"] == "1/125"
    assert result["Location"]["GPSInfo"]["GPSLatitude"] == (41, 52, 0)
    assert result["Image / Technical"]["Orientation"] == 1
    assert result["Other EXIF"]["MysteryTag"] == "mystery"


def test_classify_exif_metadata_omits_empty_sections():
    exif = {
        "Artist": "Jane Example",
    }

    result = classify_exif_metadata(exif)

    assert list(result) == ["Descriptive / Personal"]


def test_decode_ascii_user_comment():
    value = b"ASCII\x00\x00\x00Hello from EXIF\x00"

    result = decode_exif_user_comment(value)

    assert result == "Hello from EXIF"


def test_decode_little_endian_unicode_user_comment():
    text = "Attorney metadata test"
    value = b"UNICODE\x00" + text.encode("utf-16-le")

    result = decode_exif_user_comment(value)

    assert result == text


def test_decode_big_endian_unicode_user_comment():
    text = "Attorney metadata test"
    value = b"UNICODE\x00" + text.encode("utf-16-be")

    result = decode_exif_user_comment(value)

    assert result == text


def test_decode_unicode_payload_with_little_endian_bom():
    text = "Little endian"
    payload = b"\xff\xfe" + text.encode("utf-16-le")

    result = decode_exif_unicode_payload(payload)

    assert result == text


def test_decode_unicode_payload_with_big_endian_bom():
    text = "Big endian"
    payload = b"\xfe\xff" + text.encode("utf-16-be")

    result = decode_exif_unicode_payload(payload)

    assert result == text


def test_describe_short_printable_binary_data():
    result = describe_binary_value(b"Adobe Photoshop")

    assert result == "Adobe Photoshop"


def test_describe_empty_binary_data():
    result = describe_binary_value(b"")

    assert result == "<binary data: 0 bytes>"


def test_describe_large_binary_data_without_dumping_contents():
    value = bytes(range(256)) * 4

    result = describe_binary_value(value)

    assert result == "<binary data: 1024 bytes>"


def test_describe_small_non_printable_binary_data():
    value = bytes(range(32))

    result = describe_binary_value(value)

    assert result == "<binary data: 32 bytes>"


def test_prepare_value_for_display_handles_nested_dictionary():
    value = {
        "GPSLatitude": (41, 52, 0),
        "BinaryValue": b"Readable text",
    }

    result = prepare_value_for_display(value)

    assert result == {
        "GPSLatitude": (41, 52, 0),
        "BinaryValue": "Readable text",
    }


def test_prepare_value_for_display_handles_nested_sequences():
    value = [
        b"First",
        (
            b"Second",
            42,
        ),
    ]

    result = prepare_value_for_display(value)

    assert result == [
        "First",
        (
            "Second",
            42,
        ),
    ]


def test_classification_preserves_every_input_field():
    exif = {
        "Artist": "Jane Example",
        "Model": "Camera Model",
        "DateTimeOriginal": "2026:08:06 12:00:00",
        "GPSInfo": {"GPSLatitudeRef": "N"},
        "Orientation": 1,
        "UnknownTagOne": "one",
        "UnknownTagTwo": "two",
    }

    classified = classify_exif_metadata(exif)

    output_fields = {}

    for section in classified.values():
        output_fields.update(section)

    assert set(output_fields) == set(exif)
