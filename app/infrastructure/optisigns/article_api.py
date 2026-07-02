from app.domain.article import Article
from app.infrastructure.optisigns.client import OptiSignsClient
from app.utils.url import extract_relative_path


class ArticleAPI:
    """Retrieves all articles from the OptiSigns Help Center."""

    ARTICLES_PATH = "/api/v2/help_center/en-us/articles.json"

    def __init__(self, client: OptiSignsClient) -> None:
        self._client = client

    def get_all(self) -> list[Article]:
        """Fetch every article, following pagination until exhausted."""
        articles: list[Article] = []
        path: str | None = self.ARTICLES_PATH

        while path is not None:
            data = self._client.get(path)
            for raw in data["articles"]:
                articles.append(
                    Article(
                        id=raw["id"],
                        title=raw["title"],
                        body_html=raw["body"],
                        html_url=raw["html_url"],
                        updated_at=raw["updated_at"],
                    )
                )
            path = extract_relative_path(data.get("next_page"))

        return articles
