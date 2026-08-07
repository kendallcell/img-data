"""
cli.py

Command-line interface for img-data.
"""

import argparse
import sys

from PIL import UnidentifiedImageError

from .exif_inspector import classify_exif_metadata
from .inspector import inspect_image
from .utils import format_bytes


def main():
    parser = argparse.ArgumentParser(
        prog="img-data",
        description="Inspect image metadata.",
    )

    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect image metadata.",
    )

    inspect_parser.add_argument("image")

    args = parser.parse_args()

    if args.command == "inspect":
        try:
            data = inspect_image(args.image)

        except FileNotFoundError:
            print(
                f"img-data: {args.image}: No such file or directory",
                file=sys.stderr,
            )
            sys.exit(1)

        except PermissionError:
            print(
                f"img-data: {args.image}: access denied by the filesystem",
                file=sys.stderr,
            )
            sys.exit(1)

        except UnidentifiedImageError:
            print(
                f"img-data: {args.image}: not a supported image file",
                file=sys.stderr,
            )
            sys.exit(1)

        print_image_information(data)
        print_ai_metadata(data)
        print_container_metadata(data)
        print_exif_metadata(data)


def print_image_information(data: dict) -> None:
    """
    Print basic image information.
    """

    print()
    print("Image Information")
    print("=" * 60)

    print(f"Filename   : {data['filename']}")
    print(f"Format     : {data['format']}")
    print(f"Mode       : {data['mode']}")
    print(f"Resolution : {data['width']} x {data['height']}")
    print(f"File Size  : {format_bytes(data['filesize'])}")


def print_ai_metadata(data: dict) -> None:
    """
    Print structured AI metadata when present.
    """

    ai = data["ai"]

    if not ai:
        return

    print()
    print("AI Metadata")
    print("-" * 60)

    if ai["prompt"]:
        print("Prompt")
        print_indented_value(ai["prompt"], 2)
        print()

    if ai["negative_prompt"]:
        print("Negative Prompt")
        print_indented_value(ai["negative_prompt"], 2)
        print()

    if ai["settings"]:
        print("Generation Settings")

        for key, value in ai["settings"].items():
            print(f"  {key}: {value}")

        print()

    if ai["plugins"]:
        print("Plugins")

        for plugin, settings in ai["plugins"].items():
            print(f"  {plugin}")

            for key, value in settings.items():
                print(f"    {key}: {value}")

        print()

    print("Other Metadata")
    print("-" * 60)

    if ai["other"]:
        for key, value in ai["other"].items():
            print(f"{key}: {value}")
    else:
        print("None")


def print_container_metadata(data: dict) -> None:
    """
    Print non-AI metadata stored in the image container.

    The existing structured dictionary key is named ``png_info`` for
    compatibility with earlier versions of img-data, but Pillow uses the
    same ``info`` dictionary for multiple image formats.
    """

    if data["ai"]:
        return

    container_info = data["png_info"]

    print()
    print("Container Metadata")
    print("-" * 60)

    if container_info:
        for key, value in container_info.items():
            print(f"{key}: {value}")
    else:
        print("None")


def print_exif_metadata(data: dict) -> None:
    """
    Print EXIF metadata grouped into human-oriented sections.
    """

    print()
    print("EXIF Metadata")
    print("-" * 60)

    if not data["exif"]:
        print("None")
        return

    sections = classify_exif_metadata(data["exif"])

    if not sections:
        print("None")
        return

    first_section = True

    for section_name, fields in sections.items():
        if not first_section:
            print()

        print(section_name)

        for key, value in fields.items():
            print_exif_field(
                key,
                value,
                indent=2,
            )

        first_section = False


def print_exif_field(
    key: str,
    value,
    indent: int,
) -> None:
    """
    Print one EXIF field, including nested dictionaries and sequences.
    """

    prefix = " " * indent

    if isinstance(value, dict):
        print(f"{prefix}{key}")

        for child_key, child_value in value.items():
            print_exif_field(
                child_key,
                child_value,
                indent + 2,
            )

        return

    print(f"{prefix}{key}: {format_display_value(value)}")


def print_indented_value(
    value: str,
    indent: int,
) -> None:
    """
    Print multiline text with consistent indentation.
    """

    prefix = " " * indent

    for line in str(value).splitlines():
        print(f"{prefix}{line}")


def format_display_value(value) -> str:
    """
    Convert a structured display value to concise terminal text.
    """

    if isinstance(value, tuple):
        return ", ".join(format_display_value(item) for item in value)

    if isinstance(value, list):
        return ", ".join(format_display_value(item) for item in value)

    return str(value)


if __name__ == "__main__":
    main()
