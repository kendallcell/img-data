"""
inspector.py

Functions for inspecting image metadata.

This module reads an image and returns a structured description of its
metadata. The parser is intentionally written as readable Python rather
than regular-expression magic so future contributors can easily extend it.
"""

from pathlib import Path

from PIL import ExifTags, Image

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

EXIF_IFD_TAG = 0x8769
GPS_IFD_TAG = 0x8825

AI_EXIF_TEXT_FIELDS = (
    "UserComment",
    "ImageDescription",
    "Comment",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect_image(filename: str) -> dict:
    """
    Read an image and return structured metadata.

    AI metadata is detected independently of the image format. It may come
    from a PNG ``parameters`` text chunk or from an EXIF text field such as
    ``UserComment``.

    Parameters
    ----------
    filename : str
        Path to the image file.

    Returns
    -------
    dict
        Structured image, AI, file-container, and EXIF metadata.
    """

    path = Path(filename)

    with Image.open(path) as img:
        container_info = dict(img.info)
        exif = collect_exif_metadata(img)

        raw_ai_text, ai_source = extract_ai_metadata(
            container_info,
            exif,
        )

        ai = parse_ai_metadata(raw_ai_text)

        display_exif = prepare_exif_for_display(
            exif,
            ai_source,
        )

        return {
            "filename": path.name,
            "filesize": path.stat().st_size,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "png_info": container_info,
            "exif": display_exif,
            "ai": ai,
        }


# ---------------------------------------------------------------------------
# Metadata collection
# ---------------------------------------------------------------------------


def collect_exif_metadata(img: Image.Image) -> dict:
    """
    Collect EXIF metadata using human-readable tag names.

    Pillow's top-level EXIF object may contain references to nested EXIF
    Image File Directories (IFDs). Those nested fields are collected as
    well so values such as ``UserComment`` are available to the inspector.

    Parameters
    ----------
    img : PIL.Image.Image
        Open Pillow image.

    Returns
    -------
    dict
        EXIF fields keyed by human-readable tag names.
    """

    exif = img.getexif()

    if not exif:
        return {}

    metadata = {}

    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

        if tag_id in (EXIF_IFD_TAG, GPS_IFD_TAG):
            continue

        metadata[tag_name] = decode_exif_value(
            tag_name,
            value,
        )

    collect_nested_exif_ifd(
        exif,
        EXIF_IFD_TAG,
        metadata,
    )

    collect_gps_ifd(
        exif,
        metadata,
    )

    return metadata


def collect_nested_exif_ifd(
    exif,
    ifd_tag: int,
    metadata: dict,
) -> None:
    """
    Add fields from a nested EXIF IFD to the metadata dictionary.
    """

    try:
        nested_ifd = exif.get_ifd(ifd_tag)
    except (KeyError, TypeError, ValueError):
        return

    if not nested_ifd:
        return

    for tag_id, value in nested_ifd.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

        metadata[tag_name] = decode_exif_value(
            tag_name,
            value,
        )


def collect_gps_ifd(
    exif,
    metadata: dict,
) -> None:
    """
    Collect GPS EXIF fields using readable GPS tag names.
    """

    try:
        gps_ifd = exif.get_ifd(GPS_IFD_TAG)
    except (KeyError, TypeError, ValueError):
        return

    if not gps_ifd:
        return

    gps_metadata = {}

    for tag_id, value in gps_ifd.items():
        tag_name = ExifTags.GPSTAGS.get(
            tag_id,
            str(tag_id),
        )
        gps_metadata[tag_name] = value

    if gps_metadata:
        metadata["GPSInfo"] = gps_metadata


def decode_exif_value(
    tag_name: str,
    value,
):
    """
    Decode EXIF values that require special handling.

    ``UserComment`` uses an EXIF-specific eight-byte encoding prefix and is
    not safely decoded with a normal UTF-8 conversion.
    """

    if tag_name == "UserComment" and isinstance(value, bytes):
        return decode_exif_user_comment(value)

    return value


def decode_exif_user_comment(value: bytes) -> str:
    """
    Decode an EXIF UserComment byte string.

    EXIF UserComment begins with an eight-byte character-code prefix such
    as ``ASCII`` or ``UNICODE``. Unicode comments found in AI-generated
    JPEG files may use either UTF-16 byte order, so the payload is examined
    before choosing a decoder.

    Parameters
    ----------
    value : bytes
        Raw EXIF UserComment value.

    Returns
    -------
    str
        Decoded comment text.
    """

    if not value:
        return ""

    if len(value) < 8:
        return decode_bytes_fallback(value)

    prefix = value[:8]
    payload = value[8:]

    if prefix.startswith(b"ASCII"):
        return payload.rstrip(b"\x00").decode(
            "ascii",
            errors="replace",
        )

    if prefix.startswith(b"UNICODE"):
        return decode_exif_unicode_payload(payload)

    if prefix.startswith(b"JIS"):
        return payload.rstrip(b"\x00").decode(
            "shift_jis",
            errors="replace",
        )

    return decode_bytes_fallback(value)


def decode_exif_unicode_payload(payload: bytes) -> str:
    """
    Decode a UTF-16 EXIF UserComment payload.

    A byte-order mark is honored when present. Otherwise, the placement of
    null bytes is used to distinguish big-endian from little-endian text.
    """

    payload = payload.rstrip(b"\x00")

    if not payload:
        return ""

    if payload.startswith(b"\xfe\xff"):
        return payload.decode(
            "utf-16-be",
            errors="replace",
        ).lstrip("\ufeff")

    if payload.startswith(b"\xff\xfe"):
        return payload.decode(
            "utf-16-le",
            errors="replace",
        ).lstrip("\ufeff")

    sample = payload[: min(len(payload), 64)]

    even_nulls = sample[0::2].count(0)
    odd_nulls = sample[1::2].count(0)

    if even_nulls > odd_nulls:
        encoding = "utf-16-be"
    else:
        encoding = "utf-16-le"

    return payload.decode(
        encoding,
        errors="replace",
    ).lstrip("\ufeff")


def decode_bytes_fallback(value: bytes) -> str:
    """
    Decode an unknown byte string without raising a decoding exception.
    """

    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return value.rstrip(b"\x00").decode(encoding)
        except UnicodeDecodeError:
            continue

    return value.decode(
        "latin-1",
        errors="replace",
    )


# ---------------------------------------------------------------------------
# AI metadata discovery
# ---------------------------------------------------------------------------


def extract_ai_metadata(
    container_info: dict,
    exif: dict,
) -> tuple[str | None, tuple[str, str] | None]:
    """
    Search available metadata containers for AI generation information.

    PNG ``parameters`` metadata is checked first. EXIF text fields are then
    checked for text that resembles Stable Diffusion / Forge generation
    metadata.

    Parameters
    ----------
    container_info : dict
        Pillow image ``info`` dictionary.

    exif : dict
        Human-readable EXIF metadata.

    Returns
    -------
    tuple
        Raw AI metadata text and a source descriptor. Both values are None
        when no AI metadata is found.
    """

    parameters = container_info.get("parameters")

    if isinstance(parameters, str) and looks_like_ai_metadata(parameters):
        return parameters, ("container", "parameters")

    for field_name in AI_EXIF_TEXT_FIELDS:
        value = exif.get(field_name)

        if isinstance(value, str) and looks_like_ai_metadata(value):
            return value, ("exif", field_name)

    return None, None


def looks_like_ai_metadata(text: str) -> bool:
    """
    Return True when text resembles AI generation metadata.

    We intentionally require multiple generation-related markers rather
    than assuming every comment containing the word "Steps" is AI data.
    """

    if not text:
        return False

    required_marker = "Steps:"

    supporting_markers = (
        "Sampler:",
        "Seed:",
        "CFG scale:",
        "Negative prompt:",
        "Model:",
        "Size:",
    )

    if required_marker not in text:
        return False

    return any(marker in text for marker in supporting_markers)


def prepare_exif_for_display(
    exif: dict,
    ai_source: tuple[str, str] | None,
) -> dict:
    """
    Remove AI metadata from the normal EXIF display when already presented
    in the AI section.

    The AI text itself is not lost; ``parse_ai_metadata`` preserves the
    original text in the AI dictionary's ``raw`` field.
    """

    display_exif = dict(exif)

    if ai_source is None:
        return display_exif

    source_type, source_name = ai_source

    if source_type == "exif":
        display_exif.pop(
            source_name,
            None,
        )

    return display_exif


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
            brace_depth = max(
                0,
                brace_depth - 1,
            )
            current.append(character)
            continue

        if character == "[":
            bracket_depth += 1
            current.append(character)
            continue

        if character == "]":
            bracket_depth = max(
                0,
                bracket_depth - 1,
            )
            current.append(character)
            continue

        if character == "(":
            parenthesis_depth += 1
            current.append(character)
            continue

        if character == ")":
            parenthesis_depth = max(
                0,
                parenthesis_depth - 1,
            )
            current.append(character)
            continue

        is_top_level_comma = (
            character == ","
            and brace_depth == 0
            and bracket_depth == 0
            and parenthesis_depth == 0
        )

        if is_top_level_comma:
            append_token_item(
                items,
                current,
            )
            current = []
            continue

        current.append(character)

    append_token_item(
        items,
        current,
    )

    tokens: list[tuple[str, str]] = []

    for item in items:
        if ":" not in item:
            continue

        key, value = item.split(
            ":",
            1,
        )

        key = key.strip()
        value = value.strip()

        if key:
            tokens.append(
                (
                    key,
                    value,
                )
            )

    return tokens


def append_token_item(
    items: list[str],
    characters: list[str],
) -> None:
    """
    Append one completed tokenizer item when it contains non-whitespace text.
    """

    item = "".join(characters).strip()

    if item:
        items.append(item)


# ---------------------------------------------------------------------------
# Plugin handling
# ---------------------------------------------------------------------------


def split_plugin_key(
    key: str,
) -> tuple[str, str] | None:
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
                return (
                    plugin_name,
                    plugin_field,
                )

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

    plugins.setdefault(
        plugin_name,
        {},
    )

    plugins[plugin_name][key] = value
