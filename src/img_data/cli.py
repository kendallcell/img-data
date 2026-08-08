"""
cli.py

Command-line interface for img-data.

This module parses command-line arguments, handles command-level errors,
and dispatches work to the appropriate inspection, stripping, and
presentation modules.
"""

import argparse
import os
import sys
import tempfile
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
        description=(
            "Inspect, analyze, and remove image metadata "
            "without altering image content."
        ),
        epilog=(
            "INSPECTION\n"
            "\n"
            "  img-data inspect IMAGE\n"
            "      Display image information and available AI, container,\n"
            "      and EXIF metadata in a readable format.\n"
            "\n"
            "  img-data inspect --json IMAGE\n"
            "      Output inspection results as compact JSON for scripts\n"
            "      and other programs.\n"
            "\n"
            "METADATA STRIPPING\n"
            "\n"
            "  By default, stripping creates a NEW file beside the original.\n"
            "  The original image remains unchanged.\n"
            "\n"
            "  --ai\n"
            "      Remove AI generation metadata.\n"
            "\n"
            "      photo.png remains unchanged.\n"
            "      A new file named photo-AI-Stripped.png is created.\n"
            "\n"
            "  --exif\n"
            "      Remove privacy-sensitive EXIF and related metadata while\n"
            "      preserving useful technical image metadata.\n"
            "\n"
            "      photo.jpg remains unchanged.\n"
            "      A new file named photo-EXIF-Stripped.jpg is created.\n"
            "\n"
            "  --all\n"
            "      Remove both AI metadata and privacy-sensitive metadata.\n"
            "\n"
            "      photo.jpeg remains unchanged.\n"
            "      A new file named photo-All-Stripped.jpeg is created.\n"
            "\n"
            "  The original filename extension is preserved in the new file.\n"
            "  A .jpg source creates a .jpg output; a .jpeg source creates\n"
            "  a .jpeg output.\n"
            "\n"
            "OVERWRITE BEHAVIOR\n"
            "\n"
            "  If a generated *-Stripped file already exists, img-data asks:\n"
            "\n"
            "      Overwrite it? (Y/n)\n"
            "\n"
            "  Press Enter or answer y to replace the existing output file.\n"
            "  Answer n to cancel the operation. The original image is never\n"
            "  modified by this default behavior.\n"
            "\n"
            "  -f, --force\n"
            "      Suppress overwrite confirmation prompts.\n"
            "\n"
            "      Without --overwrite, --force means that an existing\n"
            "      *-Stripped output file is replaced without asking.\n"
            "      The ORIGINAL image remains unchanged.\n"
            "\n"
            "  --overwrite\n"
            "      Do NOT create a new *-Stripped file.\n"
            "\n"
            "      Instead, the ORIGINAL image is replaced by the stripped\n"
            "      image. img-data asks for confirmation before doing this.\n"
            "\n"
            "      Metadata removed from the original file is permanently\n"
            "      lost and cannot be recovered from that file.\n"
            "\n"
            "  --overwrite --force\n"
            "      Replace the ORIGINAL image without asking for confirmation.\n"
            "      This is intended for scripts and batch processing where\n"
            "      interactive prompts are undesirable.\n"
            "\n"
            "EXAMPLES\n"
            "\n"
            "  img-data inspect photo.png\n"
            "  img-data inspect --json photo.png\n"
            "  img-data strip --ai photo.png\n"
            "  img-data strip --exif portrait.jpg\n"
            "  img-data strip --all artwork.png\n"
            "  img-data strip --all --force artwork.png\n"
            "  img-data strip --all --overwrite artwork.png\n"
            "  img-data strip --all --overwrite --force artwork.png\n"
            "\n"
            "For detailed help about a command:\n"
            "  img-data inspect --help\n"
            "  img-data strip --help"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="{inspect,strip}",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Display image metadata in a readable format.",
        description=(
            "Inspect image metadata and present it in a clear, " "organized format."
        ),
        epilog=(
            "Examples:\n"
            "  img-data inspect photo.png\n"
            "  img-data inspect --json photo.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    inspect_parser.add_argument(
        "image",
        metavar="IMAGE",
        help="Image file to inspect.",
    )

    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="Output compact JSON suitable for scripts and automation.",
    )

    strip_parser = subparsers.add_parser(
        "strip",
        help="Remove selected metadata while preserving image content.",
        description=(
            "Remove selected metadata while preserving image content.\n"
            "\n"
            "DEFAULT BEHAVIOR\n"
            "\n"
            "  A new image is created beside the original.\n"
            "  The original image is not modified.\n"
            "\n"
            "  --ai\n"
            "      photo.png -> photo-AI-Stripped.png\n"
            "\n"
            "  --exif\n"
            "      photo.png -> photo-EXIF-Stripped.png\n"
            "\n"
            "  --all\n"
            "      photo.png -> photo-All-Stripped.png\n"
            "\n"
            "The original filename extension is preserved in the new output\n"
            "file. For example, photo.jpg remains unchanged and a new file\n"
            "named photo-AI-Stripped.jpg is created.\n"
            "\n"
            "If the generated output file already exists, img-data asks for\n"
            "confirmation before replacing it.\n"
            "\n"
            "OVERWRITE OPTIONS\n"
            "\n"
            "  -f, --force\n"
            "      Suppress confirmation prompts. Without --overwrite, an\n"
            "      existing *-Stripped output file is replaced without asking.\n"
            "      The original image remains unchanged.\n"
            "\n"
            "  --overwrite\n"
            "      Bypass creation of a new *-Stripped file and replace the\n"
            "      ORIGINAL image with the stripped image instead.\n"
            "      Confirmation is requested before the original is replaced.\n"
            "      Removed metadata cannot be recovered from that file.\n"
            "\n"
            "  --overwrite --force\n"
            "      Replace the ORIGINAL image without asking for confirmation.\n"
            "      Useful for scripts and batch processing."
        ),
        epilog=(
            "Examples:\n"
            "\n"
            "  img-data strip --ai photo.png\n"
            "      Creates photo-AI-Stripped.png.\n"
            "      The original photo.png is unchanged.\n"
            "\n"
            "  img-data strip --exif portrait.jpg\n"
            "      Creates portrait-EXIF-Stripped.jpg.\n"
            "      The original portrait.jpg is unchanged.\n"
            "\n"
            "  img-data strip --all artwork.png\n"
            "      Creates artwork-All-Stripped.png.\n"
            "      The original artwork.png is unchanged.\n"
            "\n"
            "  img-data strip --all --force artwork.png\n"
            "      If artwork-All-Stripped.png already exists, it is replaced\n"
            "      without asking. The original artwork.png is unchanged.\n"
            "\n"
            "  img-data strip --all --overwrite artwork.png\n"
            "      No new file is created. The original artwork.png is replaced\n"
            "      with the stripped image after confirmation. Removed metadata\n"
            "      cannot be recovered from that file.\n"
            "\n"
            "  img-data strip --all --overwrite --force artwork.png\n"
            "      No new file is created. The original artwork.png is replaced\n"
            "      without asking for confirmation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    strip_parser.add_argument(
        "image",
        metavar="IMAGE",
        help="Image file to strip.",
    )

    strip_options = strip_parser.add_mutually_exclusive_group()

    strip_options.add_argument(
        "--ai",
        action="store_true",
        help="Remove AI generation metadata only.",
    )

    strip_options.add_argument(
        "--exif",
        action="store_true",
        help=(
            "Remove privacy-sensitive EXIF and related metadata "
            "while preserving technical metadata."
        ),
    )

    strip_options.add_argument(
        "--all",
        action="store_true",
        help="Remove both AI metadata and privacy-sensitive metadata.",
    )

    strip_parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Replace the original image instead of creating a new "
            "*-Stripped file. Removed metadata cannot be recovered."
        ),
    )

    strip_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=(
            "Suppress overwrite confirmation prompts. "
            "Useful for scripts and batch processing."
        ),
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

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

    if args.overwrite:
        run_overwrite_strip(
            args,
            strip_function,
        )
        return

    run_new_file_strip(
        args,
        strip_function,
    )


def run_new_file_strip(
    args,
    strip_function,
) -> None:
    """
    Strip metadata into a newly named output file.
    """

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
        print_strip_error(
            args.image,
            error,
        )

    print_strip_report(
        output_path,
        args,
    )


def run_overwrite_strip(
    args,
    strip_function,
) -> None:
    """
    Strip metadata and safely replace the original image.
    """

    source = Path(args.image)

    if not source.exists():
        print_file_not_found(args.image)

    if not args.force:
        if not confirm_original_overwrite(source):
            print("Operation cancelled.")
            return

    try:
        output_path = strip_file_in_place(
            source,
            strip_function,
        )

    except FileNotFoundError:
        print_file_not_found(args.image)

    except PermissionError:
        print_filesystem_access_denied(args.image)

    except UnidentifiedImageError:
        print_unsupported_image(args.image)

    except ValueError as error:
        print_strip_error(
            args.image,
            error,
        )

    print_strip_report(
        output_path,
        args,
    )


def strip_file_in_place(
    source: Path,
    strip_function,
) -> Path:
    """
    Safely replace a source image with its stripped version.

    The stripped image is first written to a temporary file in the same
    directory. Only after stripping succeeds is the temporary file atomically
    moved over the source file.
    """

    temporary_path = create_temporary_output_path(source)

    try:
        strip_function(
            str(source),
            output_filename=str(temporary_path),
            force=True,
        )

        os.replace(
            temporary_path,
            source,
        )

    except Exception:
        remove_temporary_file(temporary_path)
        raise

    return source


def create_temporary_output_path(source: Path) -> Path:
    """
    Create a temporary output path beside the source image.
    """

    with tempfile.NamedTemporaryFile(
        prefix=f".{source.stem}-img-data-",
        suffix=source.suffix,
        dir=source.parent,
        delete=False,
    ) as temporary_file:
        return Path(temporary_file.name)


def remove_temporary_file(path: Path) -> None:
    """
    Remove a temporary stripping file if it still exists.
    """

    try:
        path.unlink()

    except FileNotFoundError:
        pass


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
    Ask whether an existing generated output file should be overwritten.

    Yes is the default. Pressing Enter is equivalent to answering ``yes``.
    """

    print(f"{path} already exists.")

    return ask_yes_no("Overwrite it? (Y/n): ")


def confirm_original_overwrite(path: Path) -> bool:
    """
    Ask whether the original source image should be replaced.

    Yes is the default. Pressing Enter is equivalent to answering ``yes``.
    """

    print(f"{path} is the original image.")

    return ask_yes_no("Replace it with the stripped image? (Y/n): ")


def ask_yes_no(prompt: str) -> bool:
    """
    Ask a yes/no question with yes as the default response.
    """

    while True:
        response = input(prompt).strip().lower()

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

    if args.overwrite:
        print("  Original filename preserved")


def print_privacy_removal_report() -> None:
    """
    Print the privacy-sensitive metadata categories that were removed.
    """

    print("  Personal metadata")
    print("  Location metadata")
    print("  Device-identifying metadata")
    print("  Comments and editing information")


def print_strip_error(
    filename: str,
    error: ValueError,
) -> None:
    """
    Report a stripping error and exit.
    """

    print(
        f"img-data: {filename}: {error}",
        file=sys.stderr,
    )
    sys.exit(1)


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
