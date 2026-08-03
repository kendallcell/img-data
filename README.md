## img-data

img-data is a command-line utility for inspecting and scrubbing AI and EXIF
metadata from image files without modifying the image pixels. img-data is
designed to follow usage patterns of good \*nix command-line tools

## Project Goals

Various ai tools create meta-data that preserves the settings, prompts, plugin
settings, etc. that were used to generate the image. This metadata immediately
tags the image as AI generated or AI manipulated. Additionally EXIF data often
includes personal information that the owner may not want to include when
sharing the image file. If you need a tool that can be used at the command line
or programmatically, img-data is a good choice.

img-data: displays usage information for the tool

img-data inspect filename.png: displays image metadata in a clear concise
manner, rather than a blob data-dump of the ai meta-data.

img-data strip < options > filename.png: strips metadata from the image, leaving
the image itself intact. In the vernacular of document metadata stripping,
img-data strip is a metadata "scrubber"

img-data strip has options for stripping just ai meta-data or just EXIF
meta-data or both.

## Acknowledgements

img-data was conceived and is maintained by Kendall Dugger.

Development of the project has been carried out with extensive design,
implementation guidance, code reviews, and programming assistance from OpenAI's
ChatGPT (GPT-5.5).

The project was intentionally developed using a test-driven,
implementation-focused workflow with continuous integration, automated
formatting, and incremental feature development, using GitHub Actions.

## Core Project Principles are:

- Implementation focused
- Tests before commits
- CI must stay green
- No feature creep
- Code should be pleasant to read
- Never intentionally modify image pixels
- Preserve unknown metadata when inspecting
- Remove metadata without corrupting the image

## Design Philosophy

img-data follows the Unix philosophy:

- Do one job well.
- Produce readable output.
- Be scriptable.
- Never surprise the user.

## Why Python for this project?

Python is definitely NOT as powerful for text processing as perl or a proper
lexical parser. But nobody enjoys working with those other systems. You write
the naughty-bits once with python, and that can be more difficult, but once
those parts are done, the whole rest of the program is infinitely more
read-able, easier to maintain, people look at your code and think it looks
pretty and enjoyable to browse.

> "Your perl regex expressions look lovely!"
>
> - said nobody ever.
