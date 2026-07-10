from __future__ import annotations

import html

from .config import THEME_ACCENTS
from .models import Theory


class HtmlTemplates:
    def page_shell(self, title: str, body: str) -> str:
        return f"""<!doctype html>
<html lang=\"vi\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="assets/base.css">
  <link rel="stylesheet" href="assets/layout.css">
  <link rel="stylesheet" href="assets/navigation.css">
  <link rel="stylesheet" href="assets/cards.css">
  <link rel="stylesheet" href="assets/detail.css">
  <link rel="stylesheet" href="assets/theme.css">
</head>
<body>
  {body}
</body>
</html>
"""

    def render_index(self, theories: list[Theory]) -> str:
        sections: dict[str, list[Theory]] = {}
        for theory in theories:
            sections.setdefault(theory.section.key, []).append(theory)

        nav_links: list[str] = []
        section_blocks: list[str] = []
        for section_key, items in sections.items():
            section = items[0].section
            nav_links.append(f'<a class="nav-link" href="#{section_key}">{section.label} <span class="muted">({len(items)})</span></a>')
            cards = []
            for theory in items:
                search_text = f"{theory.title} {theory.summary} {theory.section.label}".lower()
                cards.append(
                    f"""
                <a class=\"card\" data-theory-card data-search=\"{html.escape(search_text)}\" href=\"{html.escape(theory.slug)}.html\">
                  <span class=\"badge\">#{theory.order} · {html.escape(theory.section.label)}</span>
                  <h3>{html.escape(theory.title)}</h3>
                  <p>{html.escape(theory.summary)}</p>
                </a>
                """
                )
            section_blocks.append(
                f"""
            <section class=\"section accent-{section.theme}\" id=\"{section_key}\">
              <div class=\"section-header\">
                <div>
                  <h2>{html.escape(section.label)}</h2>
                  <p>{html.escape(section.description)}</p>
                </div>
                <div class=\"badge\">{len(items)} bài</div>
              </div>
              <div class=\"cards\">{''.join(cards)}</div>
            </section>
            """
            )

        body = f"""
    <div class=\"shell\">
      <header class=\"hero\">
        <div class=\"eyebrow\">Trung tâm lý thuyết · Đồ án tốt nghiệp</div>
        <h1>Trang tổng hợp lý thuyết để đọc lại nhanh</h1>
        <p>Mỗi bài lý thuyết trong thư mục này được đưa về một nơi duy nhất: chia theo 7 phần, tìm nhanh bằng từ khóa, và mở ra trang chi tiết 2 cột để xem cùng lúc phần văn bản giải thích và infographic.</p>
        <div class=\"stats\">
          <div class=\"stat\"><strong>{len(theories)}</strong><span class=\"muted\">lý thuyết đã tổng hợp</span></div>
          <div class=\"stat\"><strong>{len(sections)}</strong><span class=\"muted\">cụm nội dung lớn</span></div>
          <div class=\"stat\"><strong>2 cột</strong><span class=\"muted\">đọc văn bản song song infographic</span></div>
        </div>
      </header>
      <main class=\"grid index-layout\">
        <aside class=\"panel sidebar\">
          <h2>Điều hướng nhanh</h2>
          <p>Dùng ô tìm kiếm để lọc theo tên lý thuyết, cụm nội dung hoặc từ khóa mô tả.</p>
          <input id=\"searchBox\" class=\"search\" type=\"search\" placeholder=\"Tìm: focal loss, model surgery, Snort...\">
          <div class=\"nav-list\">{''.join(nav_links)}</div>
          <div class=\"footer-note\">Mở file này trực tiếp trong trình duyệt: <strong>_theory_hub/index.html</strong></div>
        </aside>
        <section class=\"panel content\">{''.join(section_blocks)}</section>
      </main>
    </div>
    <script src="assets/hub.js" defer></script>
    """
        return self.page_shell("Trung tâm lý thuyết", body)

    def render_detail(
        self,
        theory: Theory,
        rendered_markdown: str,
        source_md: str,
        visual_html: str,
        infographic_html_href: str | None,
        infographic_png_href: str | None,
    ) -> str:
        body = f"""
    <div class=\"shell accent-{theory.section.theme}\">
      <header class=\"hero\">
        <div class=\"eyebrow\">{html.escape(theory.section.label)} · Bài #{theory.order}</div>
        <h1>{html.escape(theory.title)}</h1>
        <p>{html.escape(theory.summary)}</p>
      </header>
      <main class=\"grid detail-layout\">
        <article class=\"panel detail-copy\">{rendered_markdown}</article>
        <aside class=\"panel detail-visual\">
          <div class=\"visual-frame\">{visual_html}</div>
          <p class=\"footer-note\">Nếu bạn cần in hoặc chèn vào slide, có thể mở trực tiếp file infographic.png hoặc infographic.html từ đây.</p>
        </aside>
      </main>
    </div>
    """
        return self.page_shell(theory.title, body)