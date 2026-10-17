"""Turning user-typed text into safe, structured pieces for templates.

Nothing here returns HTML: templates loop over the structures, and Jinja's
autoescaping does the rest (never `|safe`).
"""

from urllib.parse import urlsplit

DESCRIPTION_TEMPLATE = "## Set up\n\n\n## How to run\n\n\n## Progressions\n\n"


def render_description(text: str) -> list[dict]:
    """Split a description into headings, paragraphs and bullet lists (D8).

    `## Heading` lines become headings, `- item` lines become bullets, and
    other runs of lines become paragraphs. Headings with nothing under them
    are dropped, so an untouched "## Progressions" doesn't show on the card.
    """
    blocks: list[dict] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            if blocks and blocks[-1]["kind"] == "p":
                blocks.append({"kind": "gap"})
            continue
        if line.startswith("## "):
            blocks.append({"kind": "h", "text": line[3:].strip()})
        elif line.startswith(("- ", "* ")):
            if blocks and blocks[-1]["kind"] == "ul":
                blocks[-1]["items"].append(line[2:].strip())
            else:
                blocks.append({"kind": "ul", "items": [line[2:].strip()]})
        elif blocks and blocks[-1]["kind"] == "p":
            blocks[-1]["lines"].append(line)
        else:
            blocks.append({"kind": "p", "lines": [line]})
    blocks = [b for b in blocks if b["kind"] != "gap"]
    return [
        b for i, b in enumerate(blocks)
        if not (b["kind"] == "h" and (i + 1 == len(blocks) or blocks[i + 1]["kind"] == "h"))
    ]


def valid_video_url(url: str) -> bool:
    if not url:
        return True
    parts = urlsplit(url.strip())
    return parts.scheme.lower() in {"http", "https"} and bool(parts.netloc)


def normalise_tags(raw: str) -> str:
    seen: list[str] = []
    for tag in raw.split(","):
        tag = " ".join(tag.strip().lower().split())
        if tag and tag not in seen:
            seen.append(tag)
    return ",".join(seen)


def split_tags(tags: str) -> list[str]:
    return [t for t in tags.split(",") if t]
