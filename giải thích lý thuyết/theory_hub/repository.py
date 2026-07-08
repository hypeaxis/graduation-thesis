from __future__ import annotations

import re
from pathlib import Path

from .config import ROOT, SECTIONS
from .models import Theory
from .utils import first_heading, first_summary, read_text, slugify


class TheoryRepository:
    def __init__(self, root: Path = ROOT) -> None:
        self._root = root

    def collect(self) -> list[Theory]:
        theories: list[Theory] = []
        order_map = self._readme_order()
        for section_dir in sorted(self._root.iterdir(), key=lambda item: item.name):
            if not section_dir.is_dir() or section_dir.name.startswith("_"):
                continue
            section = SECTIONS.get(section_dir.name)
            if not section:
                continue
            for topic_dir in sorted(section_dir.iterdir(), key=lambda item: item.name):
                if not topic_dir.is_dir():
                    continue
                md_files = sorted(topic_dir.glob("*.md"))
                if not md_files:
                    continue
                md_path = md_files[0]
                markdown = read_text(md_path)
                infographic_html = topic_dir / "infographic.html"
                infographic_png = topic_dir / "infographic.png"
                theories.append(
                    Theory(
                        order=order_map.get(md_path.resolve(), 9999),
                        slug=slugify(topic_dir.name),
                        topic_dir=topic_dir,
                        md_path=md_path,
                        markdown=markdown,
                        title=first_heading(markdown),
                        summary=first_summary(markdown),
                        section=section,
                        infographic_html=infographic_html if infographic_html.exists() else None,
                        infographic_png=infographic_png if infographic_png.exists() else None,
                    )
                )
        return sorted(theories, key=lambda item: (item.order, item.title))

    def _readme_order(self) -> dict[Path, int]:
        mapping: dict[Path, int] = {}
        readme_path = self._root / "README.md"
        if not readme_path.exists():
            return mapping
        content = read_text(readme_path)
        order = 1
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+\.md)\)", content):
            mapping[(self._root / match.group(1)).resolve()] = order
            order += 1
        return mapping