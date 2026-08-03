"""
cli.py

Command-line interface for img-data.
"""

import argparse
import sys

from PIL import UnidentifiedImageError

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

        print()

        print("Image Information")
        print("=" * 60)

        print(f"Filename   : {data['filename']}")
        print(f"Format     : {data['format']}")
        print(f"Mode       : {data['mode']}")
        print(f"Resolution : {data['width']} x {data['height']}")
        print(f"File Size  : {format_bytes(data['filesize'])}")

        if data["ai"]:
            print()
            print("AI Metadata")
            print("-" * 60)

            ai = data["ai"]

            if ai["prompt"]:
                print("Prompt")
                print(f"  {ai['prompt']}")
                print()

            if ai["negative_prompt"]:
                print("Negative Prompt")
                print(f"  {ai['negative_prompt']}")
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

        else:
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


if __name__ == "__main__":
    main()
