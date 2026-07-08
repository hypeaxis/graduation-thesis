from __future__ import annotations

import os
import re
from pathlib import Path


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_text(text: str) -> str:
    cleaned = re.sub(r"`([^`]+)`", r"\1", text)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"\[\[([^\]]+)\]\]", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Ly thuyet"


def first_summary(markdown: str) -> str:
    lines = markdown.splitlines()
    seen_title = False
    buffer: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                break
            continue
        if stripped.startswith("# "):
            seen_title = True
            continue
        if not seen_title:
            continue
        if stripped.startswith(("## ", ">", "- ", "|", "```")):
            continue
        buffer.append(stripped)
        if len(" ".join(buffer)) > 180:
            break
    text = clean_text(" ".join(buffer))
    return text[:180].rstrip() + ("..." if len(text) > 180 else "")


def make_rel(target: Path, start: Path) -> str:
    return Path(os.path.relpath(str(target), str(start))).as_posix()