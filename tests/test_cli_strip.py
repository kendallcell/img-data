"""
Tests for the ``img-data strip`` command.

These tests exercise command-line stripping behavior, including output
creation, overwrite prompting, cancellation, and forced overwrites.
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


def test_existing_output_enter_overwrites(
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


def test_force_overwrites_without_prompt(
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
    assert captured.err == "img-data: strip: specify metadata to remove with --ai\n"
