## img-data v1.0

img-data is a command-line utility for inspecting, understanding, and optionally
removing (scrubbing) image metadata while leaving image content untouched. It is
exceptionally good at presenting AI image generation data, EXIF data and other
embedded data (Container metadata, XMP, ICC).

img-data is designed to follow usage patterns of good \*nix command-line tools.

When stripping metadata from JPEG files, the compressed JPEG image stream is
preserved rather than being re-encoded. This avoids the image recompression that
would occur if the file were simply re-saved through Pillow.

When stripping EXIF metadata, personal identifying information, geolocation,
comments, device-identifying information, and editing history are removed while
technical image metadata is preserved whenever possible.

## Supported Metadata

```text
AI metadata
    Forge
    AUTOMATIC1111
    Stable Diffusion
    ComfyUI (planned)

EXIF metadata
    JPEG
    PNG EXIF

Container metadata
    PNG chunks
    JPEG APP segments
```

## Project Goals

Various AI tools create metadata that preserves the settings, prompts, plugin
settings, etc. that were used to generate the image. This metadata immediately
tags the image as AI generated or AI manipulated. Additionally EXIF data often
includes personal information that the owner may not want to include when
sharing the image file. If you need a tool that can be used at the command line
or programmatically, img-data is a good choice.

Running:

```text
img-data
```

or:

```text
img-data --help
```

displays usage information for the tool.

### Inspecting Images

```text
img-data inspect photo.png
```

Displays image information and available AI, container, and EXIF metadata in a
clear, organized format rather than as a raw metadata dump.

```text
img-data inspect --json photo.png
```

Outputs the same inspection data as compact JSON for scripts and other programs.

### Stripping Metadata

By default, stripping creates a **new file beside the original**. The original
image is left unchanged.

```text
img-data strip --ai photo.png
```

Removes AI generation metadata.

The original:

```text
photo.png
```

remains unchanged, and a new file is created:

```text
photo-AI-Stripped.png
```

```text
img-data strip --exif photo.jpg
```

Removes privacy-sensitive EXIF and related metadata while preserving useful
technical metadata whenever possible.

The original:

```text
photo.jpg
```

remains unchanged, and a new file is created:

```text
photo-EXIF-Stripped.jpg
```

```text
img-data strip --all photo.jpeg
```

Removes both AI metadata and privacy-sensitive metadata.

The original:

```text
photo.jpeg
```

remains unchanged, and a new file is created:

```text
photo-All-Stripped.jpeg
```

The original filename extension is preserved in newly created output files. A
`.jpg` source creates a `.jpg` output and a `.jpeg` source creates a `.jpeg`
output.

If the generated `*-Stripped` file already exists, img-data asks before
replacing it:

```text
Overwrite it? (Y/n)
```

Pressing Enter or answering `y` replaces the existing output file. Answering `n`
cancels the operation.

### `--force`

```text
img-data strip --all --force photo.png
```

Suppresses overwrite confirmation prompts.

Without `--overwrite`, `--force` means that an existing `*-Stripped` output file
is replaced without asking. The original image is still unchanged.

This option is useful for scripts and batch processing.

### `--overwrite`

```text
img-data strip --all --overwrite photo.png
```

Changes the normal output behavior.

No new `*-Stripped` file is created. Instead, the **original image is replaced**
with the stripped image after confirmation.

Metadata removed from the original file is permanently lost and cannot be
recovered from that file.

For non-interactive use:

```text
img-data strip --all --overwrite --force photo.png
```

replaces the original image without asking for confirmation.

## AI and EXIF Privacy Scrubbing

The goal of `img-data strip --ai` is the removal of ALL recognized AI metadata.

The goal of `img-data strip --exif` is privacy rather than forensic
preservation.

Metadata that may identify a person, device, location, editing workflow, or
contains human-entered comments is removed.

Technical image metadata that describes how the image was captured (such as
exposure settings, orientation, color space, and resolution) is preserved
whenever possible.

`img-data strip --all` applies both policies in a single operation.

The image pixels themselves are never intentionally modified.

For PNG files, stripping preserves the decoded pixel data. For JPEG files,
metadata is rewritten without recompressing the JPEG image stream.

## Acknowledgements

img-data was conceived and is maintained by Kendall Dugger.

Development of the project has been carried out with extensive design,
implementation guidance, code reviews, and programming assistance from OpenAI's
ChatGPT (GPT-5.5).

The project was intentionally developed using a test-driven,
implementation-focused workflow with continuous integration, automated
formatting, and incremental feature development, using PyTest and GitHub
Actions.

## Core Project Principles are:

- Implementation focused
- Tests before commits
- CI must stay green
- No feature creep
- Code should be pleasant to read
- Never intentionally modify image pixels
- Preserve unknown metadata when inspecting
- Remove metadata without corrupting or recompressing the image

## Design Philosophy

img-data follows the Unix philosophy:

- Do one job well.
- Produce readable output.
- Be scriptable.
- Never surprise the user.

## Why Python for this project?

Python is definitely NOT as powerful for text processing as perl or a proper
lexical parser. But nobody enjoys working with those other systems. You write
the difficult parsing once with python, and that can be more difficult, but once
those parts are done, the whole rest of the program is infinitely more
read-able, easier to maintain, people look at your code and think it looks
pretty and enjoyable to browse.

> "Your perl regex expressions look lovely!"
>
> - said nobody ever.

## Design Elements and Code Structure

img-data is intentionally organized into small, focused modules. Each module has
a single responsibility and is named after what it does, rather than the data it
contains.

```text
cli.py
        Command-line interface and user interaction

inspector.py
        Coordinates inspection

ai_inspector.py
        Inspects and parses AI metadata

exif_inspector.py
        Inspects and decodes EXIF metadata

container_inspector.py
        Inspects container-level metadata

pretty_presentation.py
        Human-readable inspection output

json_presentation.py
        JSON inspection output

ai_stripper.py
        Removes AI generation metadata

exif_stripper.py
        Removes privacy-sensitive EXIF and related metadata

metadata_stripper.py
        Coordinates combined --all stripping

jpeg_rewriter.py
        Rewrites JPEG metadata without recompressing image data
```

The project directory is organized to keep development tools, test data, and
application code separate.

```text
src/
        Application source code.

ci-scripts/
        Developer convenience scripts used during local development.
        These run formatting, linting, and the automated test suite before
        code is committed.

tests/
        Automated regression and unit tests.

tests/data/
        Primary collection of specimen images used for parser development
        and regression testing.

tests/data/other/
        Additional real-world images from other sources and AI generators.
        These help ensure that img-data remains generator-independent and
        continues to work correctly with metadata found in the wild.
```

A guiding design principle of img-data is to separate **inspection** from
**modification**. Inspection modules read, decode, classify, and present
metadata. Metadata removal is implemented separately. This separation keeps the
code easier to understand, simplifies testing, and allows new inspection
features to be developed without affecting stripping functionality.

## Working with JSON output

The `--json` option is intended for use with scripts and other tools.

Each JSON document is a single line. For human readable JSON, pipe it through a
formatter.

For example, using `jq`:

```text
img-data inspect --json Attorney2.png | jq
```

If jq isn't installed on your system, you can often add it with:

```text
apt install jq
```

## Extending img-data for Additional Output Formats

img-data separates **inspection** from **presentation**.

The inspection modules produce a structured Python dictionary describing the
image. Presentation modules are responsible only for rendering that data for a
particular audience.

Adding a new output format is typically straightforward:

1. Add a new presentation module (for example, `xml_presentation.py` or
   `yaml_presentation.py`).
2. Add a command-line option in `cli.py`.
3. Dispatch the structured inspection data to the new presentation module.

In most cases, the inspection modules do not need to change because all image
metadata is already collected before presentation begins.
