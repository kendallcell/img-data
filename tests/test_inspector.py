from img_data.inspector import inspect_image


def test_can_read_png():

    data = inspect_image("tests/data/Attorney1.png")

    assert data["format"] == "PNG"
    assert data["width"] > 0
    assert data["height"] > 0
