from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


class VectorStoreService:
    """Upload markdown files to an OpenAI vector store."""

    def __init__(self, api_key: str | None = None, *, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def remove_file_from_store(self, *, vector_store_id: str, file_id: str) -> None:
        """Remove a file from a vector store and delete the underlying file object.

        This fully cleans up both the vector store association and the
        underlying file object to avoid accumulating storage usage.
        """
        # Remove the file association from the vector store
        self._client.vector_stores.files.delete(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        # Delete the underlying file object to free storage quota
        self._client.files.delete(
            file_id=file_id,
        )

    def create_batch(
        self,
        *,
        vector_store_id: str,
        file_paths: list[str | Path],
    ) -> dict[str, Any]:
        """Upload files and create a vector store batch without polling.

        Returns batch metadata including the batch_id for later polling.
        """
        uploaded_file_ids: list[str] = []
        for file_path in file_paths:
            with Path(file_path).open("rb") as handle:
                uploaded = self._client.files.create(file=handle, purpose="assistants")
                uploaded_file_ids.append(uploaded.id)

        batch = self._client.vector_stores.file_batches.create(
            vector_store_id=vector_store_id,
            file_ids=uploaded_file_ids,
        )

        return {
            "batch_id": batch.id,
            "file_ids": uploaded_file_ids,
        }

    def poll_batch(
        self,
        *,
        vector_store_id: str,
        batch_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """Poll a single batch until it completes, fails, or times out.

        The batch must have been created earlier via create_batch().
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self._client.vector_stores.file_batches.retrieve(
                vector_store_id=vector_store_id,
                batch_id=batch_id,
            )
            if status.status in {"completed", "failed", "cancelled"}:
                return {
                    "batch_id": batch_id,
                    "status": status.status,
                    "file_counts": {
                        "in_progress": status.file_counts.in_progress,
                        "completed": status.file_counts.completed,
                        "failed": status.file_counts.failed,
                        "cancelled": status.file_counts.cancelled,
                        "total": status.file_counts.total,
                    },
                }
            time.sleep(poll_interval)

        return {
            "batch_id": batch_id,
            "status": "timeout",
            "file_counts": None,
        }
