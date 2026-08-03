"""
cli.py

Command-line interface for img-data.
"""

import argparse

from .inspector import inspect_image
from .utils import format_bytes


def print_section(title: str):
    """Print a section heading."""
    print()
    print(title)
    print("-" * 60)


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

    if args.command != "inspect":
        parser.print_help()
        return

    data = inspect_image(args.image)

    #
    # Image information
    #

    print()

    print("Image Information")
    print("=" * 60)

    print(f"Filename   : {data['filename']}")
    print(f"Format     : {data['format']}")
    print(f"Mode       : {data['mode']}")
    print(f"Resolution : {data['width']} x {data['height']}")
    print(f"File Size  : {format_bytes(data['filesize'])}")

    #
    # AI Metadata
    #

    print_section("AI Metadata")

    if data["ai"] is None:

        print("None")

    else:

        ai = data["ai"]

        print("Prompt")
        print(f"  {ai['prompt']}")

        print()

        print("Negative Prompt")
        print(f"  {ai['negative_prompt']}")

        print()

        print("Generation Settings")

        if ai["settings"]:

            for key, value in ai["settings"].items():
                print(f"  {key}: {value}")

        else:

            print("  None")

        print()

        print("Plugins")

        if ai["plugins"]:

            for plugin, fields in ai["plugins"].items():

                print(f"  {plugin}")

                for key, value in fields.items():
                    print(f"    {key}: {value}")

                print()

        else:

            print("  None")

    #
    # Other PNG Metadata
    #

    print_section("Other Metadata")

    other_png = dict(data["png_info"])

    other_png.pop("parameters", None)

    if other_png:

        for key, value in other_png.items():
            print(f"{key}: {value}")

    else:

        print("None")

    #
    # EXIF
    #

    print_section("EXIF Metadata")

    if data["exif"]:

        for key, value in data["exif"].items():
            print(f"{key}: {value}")

    else:

        print("None")
