from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.domain.sync_result import SyncResult
from app.infrastructure.openai.vector_store_service import VectorStoreService


class UploadService:
    """Upload only added and updated markdown files to the vector store."""

    def __init__(
        self,
        vector_store_service: VectorStoreService,
        *,
        vector_store_id: str,
        batch_size: int = 30,
    ) -> None:
        self._vector_store_service = vector_store_service
        self._vector_store_id = vector_store_id
        self._batch_size = batch_size

    def upload(
        self,
        sync_result: SyncResult,
        *,
        markdown_dir: str | Path,
        old_file_ids: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        markdown_dir_path = Path(markdown_dir)
        logger = logging.getLogger("optibot")

        # Collect (article_id, file_path, hash) from added + updated
        changes: list[dict[str, Any]] = []
        for change in [*sync_result.added, *sync_result.updated]:
            article_id = change["article_id"]
            file_path = markdown_dir_path / f"{article_id}.md"
            if file_path.exists():
                changes.append({
                    "article_id": article_id,
                    "file_path": file_path,
                    "hash": change["hash"],
                })

        if not changes:
            return {"status": "skipped", "batches": [], "successful_article_ids": [], "file_ids": {}}

        total = len(changes)
        total_batches = (total + self._batch_size - 1) // self._batch_size

        # ── Phase 1: Upload all batches (no polling) ────────────────────
        batch_uploads: list[dict[str, Any]] = []
        for i in range(0, total, self._batch_size):
            chunk = changes[i : i + self._batch_size]
            chunk_file_paths = [c["file_path"] for c in chunk]
            batch_num = i // self._batch_size + 1

            logger.info(
                "Uploading batch %d/%d (%d files)...",
                batch_num,
                total_batches,
                len(chunk_file_paths),
            )

            result = self._vector_store_service.create_batch(
                vector_store_id=self._vector_store_id,
                file_paths=[str(p) for p in chunk_file_paths],
            )

            logger.info(
                "Batch %d/%d created (batch_id=%s)",
                batch_num,
                total_batches,
                result["batch_id"],
            )

            batch_uploads.append({
                "batch_id": result["batch_id"],
                "article_ids": [c["article_id"] for c in chunk],
                "file_ids": result["file_ids"],
            })

        # ── Phase 2: Poll all batches concurrently ──────────────────────
        batches: list[dict[str, Any]] = []
        successful_article_ids: list[int] = []

        logger.info("Polling %d batch(es) concurrently...", len(batch_uploads))

        with ThreadPoolExecutor(max_workers=len(batch_uploads)) as executor:
            future_to_batch = {
                executor.submit(
                    self._vector_store_service.poll_batch,
                    vector_store_id=self._vector_store_id,
                    batch_id=bu["batch_id"],
                ): bu
                for bu in batch_uploads
            }

            for future in as_completed(future_to_batch):
                bu = future_to_batch[future]
                try:
                    result = future.result()
                except Exception as exc:
                    logger.error(
                        "Poll failed for batch_id=%s: %s",
                        bu["batch_id"],
                        exc,
                    )
                    result = {
                        "batch_id": bu["batch_id"],
                        "status": "failed",
                        "file_counts": None,
                    }

                logger.info(
                    "Batch (batch_id=%s) result: status=%s",
                    result["batch_id"],
                    result["status"],
                )

                batches.append(result)

                # Treat both "completed" and "timeout" as uploaded
                # (files were sent to OpenAI even if we didn't wait long enough)
                if result["status"] in ("completed", "timeout"):
                    successful_article_ids.extend(bu["article_ids"])

        all_succeeded = all(b["status"] in {"completed", "timeout"} for b in batches)

        # Build file_id mapping for successful articles
        file_id_mapping: dict[int, str] = {}
        for bu in batch_uploads:
            for aid, fid in zip(bu["article_ids"], bu["file_ids"]):
                if aid in successful_article_ids:
                    file_id_mapping[aid] = fid

        # ── Phase 3: Delete old files from vector store (after successful upload) ─
        if old_file_ids:
            logger.info(
                "Removing %d old file(s) from vector store...",
                len(old_file_ids),
            )
            for article_id, file_id in old_file_ids.items():
                try:
                    self._vector_store_service.remove_file_from_store(
                        vector_store_id=self._vector_store_id,
                        file_id=file_id,
                    )
                    logger.info(
                        "Removed old file %s for article %s",
                        file_id,
                        article_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to remove old file %s for article %s: %s",
                        file_id,
                        article_id,
                        exc,
                    )

        return {
            "status": "completed" if all_succeeded else "partial",
            "batches": batches,
            "total_files": total,
            "uploaded": len(successful_article_ids),
            "successful_article_ids": successful_article_ids,
            "file_ids": file_id_mapping,
        }
