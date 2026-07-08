from __future__ import annotations

import html
import re
from pathlib import Path

from .config import OUTPUT_DIR
from .models import LinkMeta
from .utils import make_rel, slugify


class MarkdownRenderer:
    def __init__(self, slug_to_meta: dict[str, LinkMeta], md_to_page: dict[Path, str]) -> None:
        self._slug_to_meta = slug_to_meta
        self._md_to_page = md_to_page

    def render(self, markdown: str, current_md: Path) -> str:
        html_parts: list[str] = []
        paragraph: list[str] = []
        list_items: list[str] = []
        quote_lines: list[str] = []
        table_lines: list[str] = []
        in_code = False
        code_lines: list[str] = []
        seen_title_heading = False

        def flush_paragraph() -> None:
            if paragraph:
                joined = " ".join(item.strip() for item in paragraph)
                html_parts.append(f"<p>{self._render_inline(joined, current_md)}</p>")
                paragraph.clear()

        def flush_list() -> None:
            if list_items:
                items = "".join(f"<li>{self._render_inline(item, current_md)}</li>" for item in list_items)
                html_parts.append(f"<ul>{items}</ul>")
                list_items.clear()

        def flush_quote() -> None:
            if quote_lines:
                joined = " ".join(line.strip() for line in quote_lines)
                html_parts.append(f"<blockquote>{self._render_inline(joined, current_md)}</blockquote>")
                quote_lines.clear()

        def flush_table() -> None:
            if table_lines:
                html_parts.append(self._render_table(table_lines, current_md))
                table_lines.clear()

        def flush_code() -> None:
            if code_lines:
                code = html.escape("\n".join(code_lines))
                html_parts.append(f"<pre><code>{code}</code></pre>")
                code_lines.clear()

        for raw_line in markdown.splitlines():
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            if stripped.startswith("```"):
                flush_paragraph()
                flush_list()
                flush_quote()
                flush_table()
                if in_code:
                    flush_code()
                    in_code = False
                else:
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            if stripped.startswith("|") and stripped.endswith("|"):
                flush_paragraph()
                flush_list()
                flush_quote()
                table_lines.append(stripped)
                continue
            flush_table()

            if not stripped:
                flush_paragraph()
                flush_list()
                flush_quote()
                continue

            if stripped == "---":
                flush_paragraph()
                flush_list()
                flush_quote()
                html_parts.append("<hr>")
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_match:
                flush_paragraph()
                flush_list()
                flush_quote()
                if len(heading_match.group(1)) == 1 and not seen_title_heading:
                    seen_title_heading = True
                    continue
                level = min(len(heading_match.group(1)) + 1, 6)
                text = self._render_inline(heading_match.group(2), current_md)
                anchor = slugify(re.sub(r"<[^>]+>", "", heading_match.group(2)))
                html_parts.append(f"<h{level} id=\"{anchor}\">{text}</h{level}>")
                continue

            if stripped.startswith("- "):
                flush_paragraph()
                flush_quote()
                list_items.append(stripped[2:].strip())
                continue

            if stripped.startswith(">"):
                flush_paragraph()
                flush_list()
                quote_lines.append(stripped[1:].strip())
                continue

            paragraph.append(stripped)

        flush_paragraph()
        flush_list()
        flush_quote()
        flush_table()
        flush_code()
        return "\n".join(html_parts)

    def _render_inline(self, text: str, current_md: Path) -> str:
        code_tokens: dict[str, str] = {}

        def stash_code(match: re.Match[str]) -> str:
            token = f"__CODE_{len(code_tokens)}__"
            code_tokens[token] = f"<code>{html.escape(match.group(1))}</code>"
            return token

        staged = re.sub(r"`([^`]+)`", stash_code, text)
        escaped = html.escape(staged)

        def replace_wiki(match: re.Match[str]) -> str:
            slug = slugify(match.group(1).strip())
            meta = self._slug_to_meta.get(slug)
            if not meta:
                return html.escape(match.group(0))
            return f'<a href="{meta.page}">{html.escape(meta.title)}</a>'

        def replace_md_link(match: re.Match[str]) -> str:
            label = match.group(1)
            raw_target = match.group(2)
            if raw_target.startswith(("http://", "https://", "mailto:")):
                return f'<a href="{html.escape(raw_target)}">{html.escape(label)}</a>'
            normalized = raw_target.replace("\\", "/")
            abs_target = (current_md.parent / normalized).resolve()
            href = self._md_to_page.get(abs_target)
            if href:
                return f'<a href="{href}">{html.escape(label)}</a>'
            if normalized.endswith((".html", ".png", ".md")):
                rel_href = make_rel(abs_target, OUTPUT_DIR)
                return f'<a href="{html.escape(rel_href)}">{html.escape(label)}</a>'
            return f'<span>{html.escape(label)}</span>'

        escaped = re.sub(r"\[\[([^\]]+)\]\]", replace_wiki, escaped)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_md_link, escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

        for token, replacement in code_tokens.items():
            escaped = escaped.replace(token, replacement)
        return escaped

    def _render_table(self, lines: list[str], current_md: Path) -> str:
        rows = []
        for line in lines:
            stripped = line.strip().strip("|")
            rows.append([cell.strip() for cell in stripped.split("|")])
        if len(rows) < 2:
            return ""
        header = rows[0]
        body = rows[2:] if all(set(cell) <= {"-", ":"} for cell in rows[1]) else rows[1:]
        parts = ["<div class=\"table-wrap\"><table>", "<thead><tr>"]
        for cell in header:
            parts.append(f"<th>{self._render_inline(cell, current_md)}</th>")
        parts.append("</tr></thead><tbody>")
        for row in body:
            parts.append("<tr>")
            for cell in row:
                parts.append(f"<td>{self._render_inline(cell, current_md)}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table></div>")
        return "".join(parts)