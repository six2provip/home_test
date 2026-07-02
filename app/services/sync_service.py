from __future__ import annotations

from typing import Any

from app.domain.markdown import MarkdownDocument
from app.domain.sync_result import SyncResult
from app.infrastructure.storage.state_repository import StateRepository
from app.utils.hash import compute_hash


class SyncService:
    """Compare current markdown documents against saved state and report delta."""

    def __init__(self, state_repository: StateRepository) -> None:
        self._state_repository = state_repository

    def compare(self, documents: list[MarkdownDocument]) -> SyncResult:
        state = self._state_repository.load()
        added: list[dict[str, Any]] = []
        updated: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        scraped_ids: set[str] = set()

        for document in documents:
            article_id = str(document.article_id)
            scraped_ids.add(article_id)
            previous_state = state.get(article_id)
            current_hash = self._hash_document(document)

            if previous_state is None:
                added.append({"article_id": document.article_id, "hash": current_hash})
                continue

            previous_hash = previous_state.get("hash")
            if previous_hash != current_hash:
                updated.append({"article_id": document.article_id, "hash": current_hash})
            else:
                skipped.append({"article_id": document.article_id, "hash": current_hash})

        # Detect removed: articles in state but not in scraped data
        removed: list[dict[str, Any]] = []
        for aid, entry in state.items():
            if aid not in scraped_ids:
                removed.append({
                    "article_id": int(aid),
                    "file_id": entry.get("file_id", ""),
                })

        return SyncResult(
            added=added,
            updated=updated,
            skipped=skipped,
            removed=removed,
        )

    @staticmethod
    def _hash_document(document: MarkdownDocument) -> str:
        return compute_hash(document.render())
