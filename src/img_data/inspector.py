"""
inspector.py

Functions for inspecting image metadata.

This module reads an image and returns a structured description of its
metadata. The parser is intentionally written as readable Python rather
than regular-expression magic so future contributors can easily extend it.
"""

from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Parser configuration
# ---------------------------------------------------------------------------

CORE_SETTING_NAMES = {
    "Steps",
    "Sampler",
    "Schedule type",
    "Scheduler",
    "CFG scale",
    "Seed",
    "Size",
    "Model",
    "Model hash",
    "Version",
    "Hashes",
    "Clip skip",
    "VAE",
    "VAE hash",
    "Denoising strength",
    "Hires upscale",
    "Hires upscaler",
    "Hires steps",
    "RNG",
    "Variation seed",
    "Variation seed strength",
    "Seed resize from",
    "Refiner",
    "Refiner switch at",
}

KNOWN_PLUGIN_PREFIXES = (
    "ADetailer",
    "ControlNet",
    "IP-Adapter",
    "IPAdapter",
    "Regional Prompter",
    "Dynamic Thresholding",
    "Dynamic thresholding",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect_image(filename: str) -> dict:
    """
    Read an image and return structured metadata.

    Parameters
    ----------
    filename : str
        Path to the image file.

    Returns
    -------
    dict
        Structured image, AI, PNG, and EXIF metadata.
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
# AI metadata parser
# ---------------------------------------------------------------------------


def parse_ai_metadata(text: str | None) -> dict | None:
    """
    Parse Forge or Automatic1111-style AI metadata.

    The returned dictionary always has the same schema whenever AI metadata
    exists. Unrecognized fields are preserved in the ``other`` dictionary.

    Parameters
    ----------
    text : str | None
        Raw AI metadata text.

    Returns
    -------
    dict | None
        Structured AI metadata, or None when no AI metadata is present.
    """

    if not text:
        return None

    prompt, negative_prompt, settings_text = split_ai_sections(text)
    tokens = tokenize_settings(settings_text)

    settings: dict[str, str] = {}
    plugins: dict[str, dict[str, str]] = {}
    other: dict[str, str] = {}

    for key, value in tokens:
        plugin_match = split_plugin_key(key)

        if plugin_match is not None:
            plugin_name, plugin_field = plugin_match
            add_plugin_value(
                plugins,
                plugin_name,
                plugin_field,
                value,
            )
        elif key in CORE_SETTING_NAMES:
            settings[key] = value
        else:
            other[key] = value

    return {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "settings": settings,
        "plugins": plugins,
        "other": other,
        "raw": text,
    }


def split_ai_sections(text: str) -> tuple[str, str, str]:
    """
    Separate prompt, negative prompt, and generation settings.

    Multiline prompts and negative prompts are preserved. The settings
    section begins with the first line whose stripped text starts with
    ``Steps:``.

    Parameters
    ----------
    text : str
        Raw AI metadata text.

    Returns
    -------
    tuple[str, str, str]
        Prompt, negative prompt, and settings text.
    """

    prompt_lines: list[str] = []
    negative_prompt_lines: list[str] = []
    settings_lines: list[str] = []

    state = "prompt"

    for line in text.splitlines():
        stripped_line = line.strip()

        if stripped_line.startswith("Negative prompt:"):
            first_negative_line = stripped_line.removeprefix("Negative prompt:").strip()

            if first_negative_line:
                negative_prompt_lines.append(first_negative_line)

            state = "negative_prompt"
            continue

        if stripped_line.startswith("Steps:"):
            settings_lines.append(stripped_line)
            state = "settings"
            continue

        if state == "prompt":
            prompt_lines.append(line)

        elif state == "negative_prompt":
            negative_prompt_lines.append(line)

        else:
            settings_lines.append(line)

    prompt = "\n".join(prompt_lines).strip()
    negative_prompt = "\n".join(negative_prompt_lines).strip()
    settings_text = "\n".join(settings_lines).strip()

    return prompt, negative_prompt, settings_text


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def tokenize_settings(text: str) -> list[tuple[str, str]]:
    """
    Convert generation settings into ordered key/value pairs.

    Separating commas are recognized only when they occur outside quoted
    strings and outside nested braces, brackets, or parentheses. This keeps
    values such as quoted prompts and embedded JSON intact.

    Example
    -------
    ``Steps: 20, Sampler: Euler, Hashes: {"model": "abc123"}``

    becomes:

    ``[("Steps", "20"), ("Sampler", "Euler"),
    ("Hashes", '{"model": "abc123"}')]``
    """

    if not text:
        return []

    items: list[str] = []
    current: list[str] = []

    quote_character: str | None = None
    escaped = False

    brace_depth = 0
    bracket_depth = 0
    parenthesis_depth = 0

    for character in text:
        if escaped:
            current.append(character)
            escaped = False
            continue

        if character == "\\" and quote_character is not None:
            current.append(character)
            escaped = True
            continue

        if character in ('"', "'"):
            current.append(character)

            if quote_character is None:
                quote_character = character
            elif quote_character == character:
                quote_character = None

            continue

        if quote_character is not None:
            current.append(character)
            continue

        if character == "{":
            brace_depth += 1
            current.append(character)
            continue

        if character == "}":
            brace_depth = max(0, brace_depth - 1)
            current.append(character)
            continue

        if character == "[":
            bracket_depth += 1
            current.append(character)
            continue

        if character == "]":
            bracket_depth = max(0, bracket_depth - 1)
            current.append(character)
            continue

        if character == "(":
            parenthesis_depth += 1
            current.append(character)
            continue

        if character == ")":
            parenthesis_depth = max(0, parenthesis_depth - 1)
            current.append(character)
            continue

        is_top_level_comma = (
            character == ","
            and brace_depth == 0
            and bracket_depth == 0
            and parenthesis_depth == 0
        )

        if is_top_level_comma:
            append_token_item(items, current)
            current = []
            continue

        current.append(character)

    append_token_item(items, current)

    tokens: list[tuple[str, str]] = []

    for item in items:
        if ":" not in item:
            continue

        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key:
            tokens.append((key, value))

    return tokens


def append_token_item(items: list[str], characters: list[str]) -> None:
    """
    Append one completed tokenizer item when it contains non-whitespace text.
    """

    item = "".join(characters).strip()

    if item:
        items.append(item)


# ---------------------------------------------------------------------------
# Plugin handling
# ---------------------------------------------------------------------------


def split_plugin_key(key: str) -> tuple[str, str] | None:
    """
    Split a known plugin-prefixed key into plugin name and field name.

    Examples
    --------
    ``ADetailer model`` becomes ``("ADetailer", "model")``.

    ``CFG scale`` is not treated as a plugin because ``CFG`` is not listed
    as a known plugin prefix.
    """

    for plugin_name in KNOWN_PLUGIN_PREFIXES:
        prefix = f"{plugin_name} "

        if key.startswith(prefix):
            plugin_field = key[len(prefix) :].strip()

            if plugin_field:
                return plugin_name, plugin_field

    return None


def add_plugin_value(
    plugins: dict[str, dict[str, str]],
    plugin_name: str,
    key: str,
    value: str,
) -> None:
    """
    Add one parsed field to a plugin's metadata dictionary.
    """

    plugins.setdefault(plugin_name, {})
    plugins[plugin_name][key] = value
