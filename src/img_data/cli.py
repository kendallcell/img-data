"""
cli.py

Command-line interface for img-data.

This module parses command-line arguments, handles command-level errors,
and dispatches work to the appropriate inspection, stripping, and
presentation modules.
"""

import argparse
import sys
from pathlib import Path

from PIL import UnidentifiedImageError

from .ai_stripper import strip_ai_metadata
from .exif_stripper import strip_exif_metadata
from .inspector import inspect_image
from .json_presentation import print_json_inspection
from .metadata_stripper import strip_all_metadata
from .pretty_presentation import print_pretty_inspection


def main():
    """
    Parse command-line arguments and dispatch the requested operation.
    """

    parser = argparse.ArgumentParser(
        prog="img-data",
        description="Inspect and scrub image metadata.",
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

    strip_parser = subparsers.add_parser(
        "strip",
        help="Remove selected image metadata.",
    )

    strip_parser.add_argument(
        "image",
        help="Image file to strip.",
    )

    strip_options = strip_parser.add_mutually_exclusive_group()

    strip_options.add_argument(
        "--ai",
        action="store_true",
        help="Remove AI generation metadata.",
    )

    strip_options.add_argument(
        "--exif",
        action="store_true",
        help="Remove privacy-sensitive EXIF and related metadata.",
    )

    strip_options.add_argument(
        "--all",
        action="store_true",
        help="Remove AI and privacy-sensitive metadata.",
    )

    strip_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite an existing output file without prompting.",
    )

    args = parser.parse_args()

    if args.command == "inspect":
        run_inspect_command(args)

    elif args.command == "strip":
        run_strip_command(args)


def run_inspect_command(args) -> None:
    """
    Run the image inspection command.
    """

    try:
        data = inspect_image(args.image)

    except FileNotFoundError:
        print_file_not_found(args.image)

    except PermissionError:
        print_filesystem_access_denied(args.image)

    except UnidentifiedImageError:
        print_unsupported_image(args.image)

    if args.json:
        print_json_inspection(data)
    else:
        print_pretty_inspection(data)


def run_strip_command(args) -> None:
    """
    Run the requested metadata stripping command.
    """

    if not args.ai and not args.exif and not args.all:
        print(
            "img-data: strip: specify metadata to remove "
            "with --ai, --exif, or --all",
            file=sys.stderr,
        )
        sys.exit(1)

    strip_function = select_strip_function(args)

    try:
        output_path = strip_function(
            args.image,
            force=args.force,
        )

    except FileExistsError as error:
        destination = extract_existing_path(error)

        if not confirm_overwrite(destination):
            print("Operation cancelled.")
            return

        try:
            output_path = strip_function(
                args.image,
                output_filename=str(destination),
                force=True,
            )

        except PermissionError:
            print_filesystem_access_denied(str(destination))

    except FileNotFoundError:
        print_file_not_found(args.image)

    except PermissionError:
        print_filesystem_access_denied(args.image)

    except UnidentifiedImageError:
        print_unsupported_image(args.image)

    except ValueError as error:
        print(
            f"img-data: {args.image}: {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    print_strip_report(
        output_path,
        args,
    )


def select_strip_function(args):
    """
    Select the stripping implementation requested by the user.
    """

    if args.ai:
        return strip_ai_metadata

    if args.exif:
        return strip_exif_metadata

    return strip_all_metadata


def extract_existing_path(error: FileExistsError) -> Path:
    """
    Recover the existing destination path from FileExistsError.
    """

    if error.args:
        return Path(error.args[0])

    raise error


def confirm_overwrite(path: Path) -> bool:
    """
    Ask whether an existing output file should be overwritten.

    Yes is the default. Pressing Enter is therefore equivalent to answering
    ``yes``. Unrecognized responses are rejected and the question is repeated.
    """

    print(f"{path} already exists.")

    while True:
        response = input("Overwrite it? (Y/n): ").strip().lower()

        if response in {
            "",
            "y",
            "yes",
        }:
            return True

        if response in {
            "n",
            "no",
        }:
            return False

        print("Please answer 'y' or 'n'.")


def print_strip_report(
    output_path: Path,
    args,
) -> None:
    """
    Print a concise report describing the completed strip operation.
    """

    print()
    print("Removed:")

    if args.ai:
        print("  AI metadata")

    elif args.exif:
        print_privacy_removal_report()

    elif args.all:
        print("  AI metadata")
        print_privacy_removal_report()

    print()
    print("Preserved:")

    if args.exif or args.all:
        print("  Technical image metadata")
    else:
        print("  Other metadata where supported")

    print("  Image dimensions and mode")
    print("  Image content")

    print()
    print("Output:")
    print(f"  {output_path}")


def print_privacy_removal_report() -> None:
    """
    Print the privacy-sensitive metadata categories that were removed.
    """

    print("  Personal metadata")
    print("  Location metadata")
    print("  Device-identifying metadata")
    print("  Comments and editing information")


def print_file_not_found(filename: str) -> None:
    """
    Report a missing source file and exit.
    """

    print(
        f"img-data: {filename}: No such file or directory",
        file=sys.stderr,
    )
    sys.exit(1)


def print_filesystem_access_denied(filename: str) -> None:
    """
    Report that the filesystem denied access and exit.
    """

    print(
        f"img-data: {filename}: access denied by the filesystem",
        file=sys.stderr,
    )
    sys.exit(1)


def print_unsupported_image(filename: str) -> None:
    """
    Report an unsupported image file and exit.
    """

    print(
        f"img-data: {filename}: not a supported image file",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
