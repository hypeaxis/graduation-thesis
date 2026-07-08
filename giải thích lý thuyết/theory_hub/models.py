from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SectionMeta:
    key: str
    label: str
    theme: str
    description: str


@dataclass(frozen=True)
class Theory:
    order: int
    slug: str
    topic_dir: Path
    md_path: Path
    markdown: str
    title: str
    summary: str
    section: SectionMeta
    infographic_html: Path | None
    infographic_png: Path | None


@dataclass(frozen=True)
class LinkMeta:
    page: str
    title: str