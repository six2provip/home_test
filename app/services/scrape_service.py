from __future__ import annotations

from app.domain.markdown import MarkdownDocument
from app.infrastructure.converter.markdown_converter import MarkdownConverter
from app.infrastructure.storage.markdown_repository import MarkdownRepository
from app.infrastructure.optisigns.article_api import ArticleAPI


class ScrapeService:
    """Fetch articles, convert them to markdown, and persist each file."""

    def __init__(
        self,
        article_api: ArticleAPI,
        markdown_converter: MarkdownConverter,
        markdown_repository: MarkdownRepository,
    ) -> None:
        self._article_api = article_api
        self._markdown_converter = markdown_converter
        self._markdown_repository = markdown_repository

    def scrape(self) -> list[MarkdownDocument]:
        articles = self._article_api.get_all()
        documents: list[MarkdownDocument] = []

        for article in articles:
            document = self._markdown_converter.convert(article)
            self._markdown_repository.save(document, article_id=article.id)
            documents.append(document)

        return documents
