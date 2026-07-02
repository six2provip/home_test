from __future__ import annotations

from pathlib import Path

from app.domain.markdown import MarkdownDocument


class MarkdownRepository:
    """Persist markdown documents to disk."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)

    def save(self, document: MarkdownDocument, *, article_id: int) -> Path:
        file_path = self._build_path(article_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(document.render(), encoding="utf-8")
        return file_path

    def _build_path(self, article_id: int) -> Path:
        return self._base_dir / f"{article_id}.md"
