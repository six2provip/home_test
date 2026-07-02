from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownDocument:
    """Structured markdown output for an OptiSigns article."""

    title: str
    content: str
    article_url: str
    article_id: int
    updated_at: str

    def render(self) -> str:
        return (
            f"# {self.title}\n\n"
            f"{self.content}\n\n"
            "---\n\n"
            f"Article URL:\n{self.article_url}\n\n"
            f"Article ID:\n{self.article_id}\n\n"
            f"Last Updated:\n{self.updated_at}\n"
        )
