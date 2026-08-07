"""
Tests for JSON output through the ``img-data inspect`` command.
"""

import json
import sys

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
