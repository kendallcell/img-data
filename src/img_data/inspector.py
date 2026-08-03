"""
inspector.py

Functions for inspecting image metadata.

This module reads an image and returns a structured description of its
metadata.  The parser is intentionally written as readable Python rather
than regular-expression magic so future contributors can easily extend it.
"""

from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect_image(filename: str) -> dict:
    """
    Read an image and return structured metadata.
    """

    path = Path(filename)

    with Image.open(path) as img:

        png_info = dict(img.info)
        exif = dict(img.getexif())

        ai = parse_ai_metadata(png_info.get("parameters"))

        return {
            "filename": path.name,
            "filesize": path.stat().st_size,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "png_info": png_info,
            "exif": exif,
            "ai": ai,
        }


# ---------------------------------------------------------------------------
# AI Metadata Parser
# ---------------------------------------------------------------------------


def parse_ai_metadata(text: str | None) -> dict | None:
    """
    Parse Forge / Automatic1111 style PNG metadata.

    Returns None if no AI metadata exists.
    """

    if not text:
        return None

    prompt = ""
    negative_prompt = ""

    settings_text = ""

    lines = text.splitlines()

    state = "prompt"

    for line in lines:

        if line.startswith("Negative prompt:"):
            negative_prompt = line.replace("Negative prompt:", "", 1).strip()
            state = "negative"
            continue

        if line.startswith("Steps:"):
            settings_text = line
            state = "settings"
            continue

        if state == "prompt":
            if prompt:
                prompt += "\n"
            prompt += line

        elif state == "negative":
            if negative_prompt:
                negative_prompt += "\n"
            negative_prompt += line

        elif state == "settings":
            settings_text += "\n" + line

    tokens = tokenize_settings(settings_text)

    settings = {}
    plugins = {}
    unknown = {}

    for key, value in tokens:

        if key.startswith("ADetailer "):
            add_plugin_value(plugins, "ADetailer", key[10:], value)

        elif " " in key:
            first, remainder = key.split(" ", 1)

            if first.isalpha() and remainder:

                add_plugin_value(
                    plugins,
                    first,
                    remainder,
                    value,
                )

            else:
                settings[key] = value

        else:
            settings[key] = value

    return {
        "prompt": prompt.strip(),
        "negative_prompt": negative_prompt.strip(),
        "settings": settings,
        "plugins": plugins,
        "unknown": unknown,
        "raw": text,
    }


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def tokenize_settings(text: str) -> list[tuple[str, str]]:
    """
    Convert

        Steps: 20, Sampler: Euler, CFG scale: 5

    into

        [
            ("Steps", "20"),
            ("Sampler", "Euler"),
            ("CFG scale", "5"),
        ]

    while preserving commas inside quoted strings.
    """

    if not text:
        return []

    parts = []

    current = []

    inside_quotes = False

    i = 0

    while i < len(text):

        ch = text[i]

        if ch == '"':
            inside_quotes = not inside_quotes
            current.append(ch)

        elif ch == "," and not inside_quotes:
            parts.append("".join(current).strip())
            current = []

        else:
            current.append(ch)

        i += 1

    if current:
        parts.append("".join(current).strip())

    tokens = []

    for item in parts:

        if ":" not in item:
            continue

        key, value = item.split(":", 1)

        tokens.append((key.strip(), value.strip()))

    return tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def add_plugin_value(
    plugins: dict,
    plugin_name: str,
    key: str,
    value: str,
):
    """
    Add a parsed plugin value.
    """

    plugins.setdefault(plugin_name, {})

    plugins[plugin_name][key] = value
