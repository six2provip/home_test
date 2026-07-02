from __future__ import annotations

from markdownify import markdownify as html_to_markdown

from app.domain.article import Article
from app.domain.markdown import MarkdownDocument
from app.utils.text import normalize_blank_lines


class MarkdownConverter:
    """Convert OptiSigns article HTML into markdown with metadata."""

    def convert(self, article: Article) -> MarkdownDocument:
        body_markdown = normalize_blank_lines(self._convert_html(article.body_html))
        return MarkdownDocument(
            title=article.title.strip(),
            content=body_markdown,
            article_url=article.html_url.strip(),
            article_id=article.id,
            updated_at=article.updated_at.strip(),
        )

    def _convert_html(self, html_body: str) -> str:
        if not html_body:
            return ""
        return html_to_markdown(html_body, heading_style="ATX")
