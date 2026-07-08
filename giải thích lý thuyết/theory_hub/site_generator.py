from __future__ import annotations

from pathlib import Path

from .asset_publisher import AssetPublisher
from .config import OUTPUT_DIR
from .markdown_renderer import MarkdownRenderer
from .models import LinkMeta, Theory
from .repository import TheoryRepository
from .templates import HtmlTemplates
from .utils import make_rel


class SiteGenerator:
    def __init__(
        self,
        repository: TheoryRepository | None = None,
        templates: HtmlTemplates | None = None,
        asset_publisher: AssetPublisher | None = None,
    ) -> None:
        self._repository = repository or TheoryRepository()
        self._templates = templates or HtmlTemplates()
        self._asset_publisher = asset_publisher or AssetPublisher()

    def build(self) -> list[Theory]:
        theories = self._repository.collect()
        if not theories:
            raise SystemExit("Không tìm thấy bài lý thuyết nào để tổng hợp.")

        OUTPUT_DIR.mkdir(exist_ok=True)
        self._asset_publisher.publish(OUTPUT_DIR)
        slug_to_meta, md_to_page = self._build_link_maps(theories)
        renderer = MarkdownRenderer(slug_to_meta, md_to_page)

        (OUTPUT_DIR / "index.html").write_text(self._templates.render_index(theories), encoding="utf-8")

        for theory in theories:
            rendered_markdown = renderer.render(theory.markdown, theory.md_path)
            visual_html = self._build_visual_html(theory)
            source_md = make_rel(theory.md_path, OUTPUT_DIR)
            infographic_html_href = make_rel(theory.infographic_html, OUTPUT_DIR) if theory.infographic_html else None
            infographic_png_href = make_rel(theory.infographic_png, OUTPUT_DIR) if theory.infographic_png else None
            page = self._templates.render_detail(
                theory,
                rendered_markdown,
                source_md,
                visual_html,
                infographic_html_href,
                infographic_png_href,
            )
            (OUTPUT_DIR / f"{theory.slug}.html").write_text(page, encoding="utf-8")

        return theories

    def _build_link_maps(self, theories: list[Theory]) -> tuple[dict[str, LinkMeta], dict[Path, str]]:
        slug_to_meta: dict[str, LinkMeta] = {}
        md_to_page: dict[Path, str] = {}
        for theory in theories:
            page_name = f"{theory.slug}.html"
            slug_to_meta[theory.slug] = LinkMeta(page=page_name, title=theory.title)
            md_to_page[theory.md_path] = page_name
        return slug_to_meta, md_to_page

    def _build_visual_html(self, theory: Theory) -> str:
        if theory.infographic_png:
            return (
                f'<img class="visual-image" alt="{theory.title}" '
                f'src="{make_rel(theory.infographic_png, OUTPUT_DIR)}">'
            )
        if theory.infographic_html:
            return (
                f'<iframe title="{theory.title}" '
                f'src="{make_rel(theory.infographic_html, OUTPUT_DIR)}" loading="lazy"></iframe>'
            )
        return ""