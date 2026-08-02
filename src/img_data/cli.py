"""
cli.py

Command-line interface for img-data.
"""

import argparse

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
        help="Inspect an image."
    )

    inspect_parser.add_argument("image")

    args = parser.parse_args()

    if args.command == "inspect":

        data = inspect_image(args.image)

        print()

        print("Image Information")
        print("=" * 60)

        print(f"Filename   : {data['filename']}")
        print(f"Format     : {data['format']}")
        print(f"Mode       : {data['mode']}")
        print(f"Resolution : {data['width']} x {data['height']}")
        print(f"File Size  : {format_bytes(data['filesize'])}")

        print()
        print("PNG Metadata")
        print("-" * 60)

        if data["png_info"]:
            for key, value in data["png_info"].items():
                print(f"{key}: {value}")
        else:
            print("None")

        print()
        print("EXIF Metadata")
        print("-" * 60)

        if data["exif"]:
            for key, value in data["exif"].items():
                print(f"{key}: {value}")
        else:
            print("None")

