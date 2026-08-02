"""
utils.py

General utility functions.
"""


def format_bytes(size: int) -> str:
    """
    Convert a byte count into a human-readable string.
    """

    units = ("B", "KB", "MB", "GB", "TB")

    value = float(size)

    for unit in units:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0

    return f"{value:.1f} PB"

