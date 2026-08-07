"""
cli.py

Command-line interface for img-data.

This module parses command-line arguments, handles command-level errors,
and dispatches work to the appropriate inspection and presentation modules.
"""

import argparse
import sys

from PIL import UnidentifiedImageError

from .inspector import inspect_image
from .json_presentation import print_json_inspection
from .pretty_presentation import print_pretty_inspection


def main():
    """
    Parse command-line arguments and dispatch the requested operation.
    """

    parser = argparse.ArgumentParser(
        prog="img-data",
        description="Inspect image metadata.",
    )

    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect image metadata.",
    )

    inspect_parser.add_argument(
        "image",
        help="Image file to inspect.",
    )

    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Output inspection results as compact JSON.",
    )

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

        if args.json:
            print_json_inspection(data)
        else:
            print_pretty_inspection(data)


if __name__ == "__main__":
    main()
