"""
Tests for the ``img-data strip`` command.

These tests exercise command-line stripping behavior, including AI stripping,
privacy-oriented EXIF stripping, output creation, overwrite prompting,
cancellation, and forced overwrites.
"""

import shutil
import sys
from pathlib import Path

import pytest

from img_data.cli import (
    confirm_overwrite,
    main,
)
from img_data.inspector import inspect_image


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


def copy_specimen(tmp_path, source):
    """
    Copy a specimen image into pytest's temporary working area.

    CLI stripping tests operate only on temporary copies so the permanent
    specimen collection under ``tests/data`` is never modified.
    """

    destination = tmp_path / source.name

    shutil.copy2(
        source,
        destination,
    )

    return destination


def test_strip_ai_creates_default_output_file(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--ai",
        str(source),
    )

    destination = tmp_path / "Attorney2-AI-Stripped.png"

    assert stderr == ""
    assert destination.exists()
    assert "Removed:" in stdout
    assert "AI metadata" in stdout
    assert f"  {destination}" in stdout

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_exif_creates_default_output_file(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    destination = tmp_path / "Attorney1-EXIF-Stripped.png"

    assert stderr == ""
    assert destination.exists()
    assert f"  {destination}" in stdout


def test_strip_exif_reports_removed_privacy_categories(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    assert stderr == ""
    assert "Removed:" in stdout
    assert "Personal metadata" in stdout
    assert "Location metadata" in stdout
    assert "Device-identifying metadata" in stdout
    assert "Comments and editing information" in stdout


def test_strip_exif_reports_preserved_technical_metadata(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    assert stderr == ""
    assert "Preserved:" in stdout
    assert "Technical image metadata" in stdout
    assert "Image dimensions and mode" in stdout
    assert "Image content" in stdout


def test_strip_exif_output_removes_private_metadata(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    destination = tmp_path / "Attorney1-EXIF-Stripped.png"
    result = inspect_image(destination)

    assert "Comment" not in result["container"]
    assert "xmp" not in result["container"]
    assert "XML:com.adobe.xmp" not in result["container"]
    assert "Raw profile type exif" not in result["container"]

    assert "ImageDescription" not in result["exif"]
    assert "UserComment" not in result["exif"]
    assert "Software" not in result["exif"]
    assert "DateTime" not in result["exif"]


def test_strip_exif_output_preserves_technical_metadata(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    destination = tmp_path / "Attorney1-EXIF-Stripped.png"
    result = inspect_image(destination)

    assert result["exif"]["Orientation"] == 1
    assert result["exif"]["ColorSpace"] == 1
    assert result["exif"]["ImageWidth"] == 896
    assert result["exif"]["ImageLength"] == 1152


@pytest.mark.parametrize(
    "response",
    [
        "",
        "y",
        "Y",
        "yes",
        "YES",
        "YeS",
    ],
)
def test_confirm_overwrite_accepts_yes_responses(
    monkeypatch,
    response,
    tmp_path,
):
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: response,
    )

    destination = tmp_path / "output.png"

    assert confirm_overwrite(destination) is True


@pytest.mark.parametrize(
    "response",
    [
        "n",
        "N",
        "no",
        "NO",
        "No",
    ],
)
def test_confirm_overwrite_accepts_no_responses(
    monkeypatch,
    response,
    tmp_path,
):
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: response,
    )

    destination = tmp_path / "output.png"

    assert confirm_overwrite(destination) is False


def test_confirm_overwrite_reprompts_after_invalid_response(
    monkeypatch,
    capsys,
    tmp_path,
):
    responses = iter(
        [
            "perhaps",
            "n",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: next(responses),
    )

    destination = tmp_path / "output.png"

    result = confirm_overwrite(destination)

    captured = capsys.readouterr()

    assert result is False
    assert "Please answer 'y' or 'n'." in captured.out


def test_existing_ai_output_enter_overwrites(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    destination = tmp_path / "Attorney2-AI-Stripped.png"
    destination.write_bytes(b"old output")

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: "",
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--ai",
        str(source),
    )

    assert stderr == ""
    assert f"{destination} already exists." in stdout
    assert "Removed:" in stdout

    result = inspect_image(destination)

    assert result["ai"] is None


def test_existing_exif_output_enter_overwrites(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    destination = tmp_path / "Attorney1-EXIF-Stripped.png"
    destination.write_bytes(b"old output")

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: "",
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        str(source),
    )

    assert stderr == ""
    assert f"{destination} already exists." in stdout
    assert "Removed:" in stdout

    result = inspect_image(destination)

    assert "Comment" not in result["container"]


def test_existing_output_no_cancels_without_overwriting(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    destination = tmp_path / "Attorney2-AI-Stripped.png"
    original_contents = b"do not overwrite"

    destination.write_bytes(original_contents)

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: "n",
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--ai",
        str(source),
    )

    assert stderr == ""
    assert f"{destination} already exists." in stdout
    assert "Operation cancelled." in stdout
    assert "Removed:" not in stdout
    assert destination.read_bytes() == original_contents


def test_force_overwrites_ai_without_prompt(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    destination = tmp_path / "Attorney2-AI-Stripped.png"
    destination.write_bytes(b"old output")

    def fail_if_prompted(prompt):
        raise AssertionError(f"--force unexpectedly prompted: {prompt}")

    monkeypatch.setattr(
        "builtins.input",
        fail_if_prompted,
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--ai",
        "--force",
        str(source),
    )

    assert stderr == ""
    assert "Removed:" in stdout

    result = inspect_image(destination)

    assert result["ai"] is None


def test_force_overwrites_exif_without_prompt(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney1.png"),
    )

    destination = tmp_path / "Attorney1-EXIF-Stripped.png"
    destination.write_bytes(b"old output")

    def fail_if_prompted(prompt):
        raise AssertionError(f"--force unexpectedly prompted: {prompt}")

    monkeypatch.setattr(
        "builtins.input",
        fail_if_prompted,
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "--exif",
        "--force",
        str(source),
    )

    assert stderr == ""
    assert "Removed:" in stdout

    result = inspect_image(destination)

    assert "Comment" not in result["container"]
    assert "UserComment" not in result["exif"]


def test_short_force_option_overwrites_without_prompt(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    destination = tmp_path / "Attorney2-AI-Stripped.png"
    destination.write_bytes(b"old output")

    def fail_if_prompted(prompt):
        raise AssertionError(f"-f unexpectedly prompted: {prompt}")

    monkeypatch.setattr(
        "builtins.input",
        fail_if_prompted,
    )

    stdout, stderr = run_cli(
        monkeypatch,
        capsys,
        "strip",
        "-f",
        "--ai",
        str(source),
    )

    assert stderr == ""
    assert "Removed:" in stdout

    result = inspect_image(destination)

    assert result["ai"] is None


def test_strip_without_metadata_option_exits_with_error(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "img-data",
            "strip",
            str(source),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 1
    assert captured.out == ""
    assert (
        captured.err
        == "img-data: strip: specify metadata to remove with --ai or --exif\n"
    )


def test_ai_and_exif_options_are_mutually_exclusive(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = copy_specimen(
        tmp_path,
        Path("tests/data/Attorney2.png"),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "img-data",
            "strip",
            "--ai",
            "--exif",
            str(source),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert captured.out == ""
    assert "not allowed with argument" in captured.err
