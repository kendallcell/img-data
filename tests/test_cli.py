import json
import sys

import pytest

from img_data.cli import main


def run_cli(monkeypatch, capsys, *arguments):
    """
    Run img-data's CLI and return captured stdout and stderr.
    """

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "img-data",
            *arguments,
        ],
    )

    main()

    captured = capsys.readouterr()

    return captured.out, captured.err


def test_inspect_prints_image_information(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "Image Information" in stdout
    assert "Filename   : Attorney1.png" in stdout
    assert "Format     : PNG" in stdout


def test_non_ai_image_uses_container_metadata_heading(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "Container Metadata" in stdout
    assert "PNG Metadata" not in stdout


def test_attorney1_container_metadata_is_categorized(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""

    assert "Image Profile" in stdout
    assert "Embedded Metadata" in stdout
    assert "Image Properties" in stdout
    assert "Comments" in stdout

    assert "ICC Color Profile: Present (" in stdout
    assert "EXIF Profile: Present (" in stdout
    assert "XMP Metadata: Present (" in stdout
    assert "Adobe XMP Metadata: Present (" in stdout
    assert "DPI: 299.9994, 299.9994" in stdout

    assert "Comment: Created with Forge UI, " "EXIF data edited with Gimp" in stdout


def test_attorney1_does_not_dump_icc_binary_data(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "icc_profile: b'" not in stdout
    assert "\\x00\\x00\\x02" not in stdout


def test_attorney1_does_not_dump_xmp_packet(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "<?xpacket" not in stdout
    assert "<x:xmpmeta" not in stdout
    assert "<rdf:RDF" not in stdout


def test_attorney1_exif_output_is_categorized(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "EXIF Metadata" in stdout
    assert "Descriptive / Personal" in stdout
    assert "Camera / Device" in stdout
    assert "Capture Information" in stdout
    assert "Image / Technical" in stdout
    assert "Other EXIF" in stdout


def test_ai_image_prints_ai_metadata(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney2.png",
    )

    assert stderr == ""
    assert "AI Metadata" in stdout
    assert "Prompt" in stdout
    assert "Generation Settings" in stdout
    assert "Model: realvisxlV50_v50Bakedvae" in stdout


def test_ai_image_does_not_print_container_metadata(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney2.png",
    )

    assert stderr == ""
    assert "AI Metadata" in stdout
    assert "Container Metadata" not in stdout


def test_missing_file_prints_single_line_error(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "img-data",
            "inspect",
            "does-not-exist.png",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 1
    assert captured.out == ""
    assert (
        captured.err == "img-data: does-not-exist.png: " "No such file or directory\n"
    )


def test_unsupported_file_prints_single_line_error(
    monkeypatch,
    capsys,
    tmp_path,
):
    file_path = tmp_path / "not-an-image.txt"

    file_path.write_text(
        "This is not an image.",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "img-data",
            "inspect",
            str(file_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 1
    assert captured.out == ""
    assert captured.err.endswith(": not a supported image file\n")


def test_jpeg_ai_metadata_is_presented_normally(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/other/Attorney8.jpeg",
    )

    assert stderr == ""
    assert "Format     : JPEG" in stdout
    assert "AI Metadata" in stdout
    assert "female lawyer." in stdout
    assert "Sampler: DPM++ 2M" in stdout


def test_court2_regression_output(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/other/Court2.png",
    )

    assert stderr == ""
    assert "CFG scale: 1.5" in stdout
    assert "Model hash: f53945ec37" in stdout
    assert 'Hashes: {"model": "f53945ec37"}' in stdout


def test_multiline_prompt_is_presented(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney3.png",
    )

    assert stderr == ""
    assert "AI Metadata" in stdout
    assert "Prompt" in stdout


def test_exif_heading_is_always_present(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney1.png",
    )

    assert stderr == ""
    assert "EXIF Metadata" in stdout


def test_json_option_before_filename_produces_valid_json(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "--json",
        "tests/data/Attorney2.png",
    )

    result = json.loads(stdout)

    assert stderr == ""
    assert result["filename"] == "Attorney2.png"
    assert result["format"] == "PNG"


def test_json_option_after_filename_produces_valid_json(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "tests/data/Attorney2.png",
        "--json",
    )

    result = json.loads(stdout)

    assert stderr == ""
    assert result["filename"] == "Attorney2.png"
    assert result["format"] == "PNG"


def test_json_cli_uses_permanent_top_level_schema(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "--json",
        "tests/data/Attorney2.png",
    )

    result = json.loads(stdout)

    assert stderr == ""

    assert set(result) == {
        "filename",
        "filesize",
        "format",
        "mode",
        "width",
        "height",
        "container",
        "exif",
        "ai",
    }

    assert "png_info" not in result


def test_json_output_does_not_include_pretty_headings(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "--json",
        "tests/data/Attorney2.png",
    )

    assert stderr == ""
    assert "Image Information" not in stdout
    assert "AI Metadata\n" not in stdout
    assert "EXIF Metadata\n" not in stdout
    assert "Container Metadata\n" not in stdout


def test_json_output_preserves_structured_ai_metadata(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "--json",
        "tests/data/Attorney2.png",
    )

    result = json.loads(stdout)

    assert stderr == ""
    assert result["ai"]["settings"]["Steps"] == "20"
    assert result["ai"]["settings"]["Model"] == "realvisxlV50_v50Bakedvae"
    assert result["ai"]["plugins"]["ADetailer"]["model"] == "face_yolov8n.pt"


def test_json_output_encodes_binary_container_metadata(
    monkeypatch,
    capsys,
):
    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "inspect",
        "--json",
        "tests/data/Attorney1.png",
    )

    result = json.loads(stdout)

    assert stderr == ""

    profile = result["container"]["icc_profile"]

    assert profile["type"] == "binary"
    assert profile["size"] == 672
    assert profile["encoding"] == "base64"
    assert profile["data"]
