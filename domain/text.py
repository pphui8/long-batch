from __future__ import annotations

import re


_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")


def slugify_title(title: str) -> str:
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", title).strip(" .")
    cleaned = _WHITESPACE.sub(" ", cleaned)
    return cleaned[:120] or "untitled"


def normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    compacted: list[str] = []
    blank_seen = False
    for line in lines:
        if line.strip():
            compacted.append(line)
            blank_seen = False
        elif not blank_seen:
            compacted.append("")
            blank_seen = True
    return "\n".join(compacted).strip() + "\n"
