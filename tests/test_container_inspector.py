from img_data.container_inspector import (
    classify_container_field,
    classify_container_metadata,
    describe_container_bytes,
    describe_container_text,
    friendly_container_field_name,
    prepare_container_value_for_display,
)


def test_classifies_icc_profile():
    assert classify_container_field("icc_profile") == "Image Profile"


def test_classifies_xmp_metadata():
    assert classify_container_field("xmp") == "Embedded Metadata"
    assert classify_container_field("XML:com.adobe.xmp") == "Embedded Metadata"


def test_classifies_exif_container_metadata():
    assert classify_container_field("exif") == "Embedded Metadata"
    assert classify_container_field("Raw profile type exif") == "Embedded Metadata"


def test_classifies_image_properties():
    assert classify_container_field("dpi") == "Image Properties"
    assert classify_container_field("jfif") == "Image Properties"
    assert classify_container_field("jfif_density") == "Image Properties"


def test_classifies_comments():
    assert classify_container_field("Comment") == "Comments"
    assert classify_container_field("Description") == "Comments"


def test_unknown_container_field_is_preserved():
    assert classify_container_field("FutureMetadataThing") == "Other Container Metadata"


def test_classify_container_metadata_preserves_all_fields():
    metadata = {
        "icc_profile": b"profile",
        "xmp": b"<xmp />",
        "dpi": (300, 300),
        "Comment": "Test image",
        "FutureField": "future",
    }

    classified = classify_container_metadata(metadata)

    output_fields = {}

    for section in classified.values():
        output_fields.update(section)

    assert set(output_fields) == set(metadata)


def test_classification_omits_empty_sections():
    metadata = {
        "Comment": "Test image",
    }

    classified = classify_container_metadata(metadata)

    assert list(classified) == ["Comments"]


def test_friendly_container_field_names():
    assert friendly_container_field_name("icc_profile") == "ICC Color Profile"
    assert friendly_container_field_name("Raw profile type exif") == "EXIF Profile"
    assert friendly_container_field_name("XML:com.adobe.xmp") == "Adobe XMP Metadata"
    assert friendly_container_field_name("dpi") == "DPI"


def test_unknown_field_keeps_original_name():
    assert friendly_container_field_name("FutureMetadataThing") == "FutureMetadataThing"


def test_icc_profile_binary_data_is_summarized_in_bytes():
    value = bytes(range(256)) * 2

    result = describe_container_bytes(
        "icc_profile",
        value,
    )

    assert result == "Present (512 bytes)"


def test_exif_binary_data_is_summarized_in_bytes():
    value = b"Exif\x00\x00" + bytes(100)

    result = describe_container_bytes(
        "exif",
        value,
    )

    assert result == "Present (106 bytes)"


def test_xmp_binary_data_is_summarized_in_bytes():
    value = b"<x:xmpmeta>" + bytes(300)

    result = describe_container_bytes(
        "xmp",
        value,
    )

    assert result == "Present (311 bytes)"


def test_short_printable_unknown_bytes_are_decoded():
    result = describe_container_bytes(
        "UnknownField",
        b"Readable metadata",
    )

    assert result == "Readable metadata"


def test_large_unknown_binary_data_is_summarized():
    value = bytes(range(256)) * 4

    result = describe_container_bytes(
        "UnknownField",
        value,
    )

    assert result == "<binary data: 1024 bytes>"


def test_large_xmp_text_is_summarized_in_characters():
    value = "<xmp>" + ("A" * 500) + "</xmp>"

    result = describe_container_text(
        "XML:com.adobe.xmp",
        value,
    )

    assert result == f"Present ({len(value)} characters)"


def test_large_text_exif_profile_is_summarized_in_characters():
    value = "exif\n" + ("0123456789" * 100)

    result = describe_container_text(
        "Raw profile type exif",
        value,
    )

    assert result == f"Present ({len(value)} characters)"


def test_short_comment_is_preserved():
    value = "Created with GIMP"

    result = describe_container_text(
        "Comment",
        value,
    )

    assert result == value


def test_nested_values_are_preserved_and_prepared():
    value = {
        "density": (300, 300),
        "comment": b"Readable",
    }

    result = prepare_container_value_for_display(
        "metadata",
        value,
    )

    assert result == {
        "density": (300, 300),
        "comment": "Readable",
    }
