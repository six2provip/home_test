from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.config.settings import Settings
from app.utils.logger import setup_logger
from app.infrastructure.converter.markdown_converter import MarkdownConverter
from app.infrastructure.openai.vector_store_service import VectorStoreService
from app.infrastructure.storage.log_repository import LogRepository
from app.infrastructure.storage.markdown_repository import MarkdownRepository
from app.infrastructure.storage.state_repository import StateRepository
from app.infrastructure.optisigns.article_api import ArticleAPI
from app.infrastructure.optisigns.client import OptiSignsClient
from app.services.scrape_service import ScrapeService
from app.services.sync_service import SyncService
from app.services.upload_service import UploadService


def main() -> int:
    logger = setup_logger()

    try:
        settings = Settings()
        logger.info("Loaded settings")

        markdown_repository = MarkdownRepository(settings.MARKDOWN_DIR)
        state_repository = StateRepository(settings.STATE_FILE)
        log_repository = LogRepository(settings.LOG_FILE)

        optisigns_client = OptiSignsClient(settings)
        article_api = ArticleAPI(optisigns_client)
        markdown_converter = MarkdownConverter()
        scrape_service = ScrapeService(
            article_api=article_api,
            markdown_converter=markdown_converter,
            markdown_repository=markdown_repository,
        )
        sync_service = SyncService(state_repository=state_repository)
        vector_store_service = VectorStoreService(api_key=settings.OPENAI_API_KEY)
        upload_service = UploadService(
            vector_store_service=vector_store_service,
            vector_store_id=settings.OPENAI_VECTOR_STORE_ID,
        )

        documents = scrape_service.scrape()
        logger.info("Scraped %d articles", len(documents))

        sync_result = sync_service.compare(documents)
        logger.info(
            "Delta summary: added=%d updated=%d skipped=%d removed=%d",
            len(sync_result.added),
            len(sync_result.updated),
            len(sync_result.skipped),
            len(sync_result.removed),
        )

        existing_state = state_repository.load()

        # Extract old file_ids for articles that will be updated
        old_file_ids: dict[int, str] = {}
        for change in sync_result.updated:
            aid = str(change["article_id"])
            if aid in existing_state and "file_id" in existing_state[aid]:
                old_file_ids[change["article_id"]] = existing_state[aid]["file_id"]

        if old_file_ids:
            logger.info(
                "Found %d old file(s) to remove from vector store",
                len(old_file_ids),
            )

        upload_summary = upload_service.upload(
            sync_result,
            markdown_dir=settings.MARKDOWN_DIR,
            old_file_ids=old_file_ids,
        )
        logger.info("Upload summary: %s", upload_summary)

        # ── Handle removed articles (after upload succeeds) ─────────────
        for entry in sync_result.removed:
            article_id = entry["article_id"]
            file_id = entry["file_id"]

            # Delete from OpenAI vector store + file object
            if file_id:
                try:
                    vector_store_service.remove_file_from_store(
                        vector_store_id=settings.OPENAI_VECTOR_STORE_ID,
                        file_id=file_id,
                    )
                    logger.info(
                        "Deleted removed article %s from OpenAI (file_id=%s)",
                        article_id,
                        file_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to delete file %s for removed article %s: %s",
                        file_id,
                        article_id,
                        exc,
                    )

            # Delete markdown file from disk
            md_path = settings.MARKDOWN_DIR / f"{article_id}.md"
            if md_path.exists():
                md_path.unlink()
                logger.info("Deleted markdown file for removed article %s", article_id)

            # Remove from state (pop after upload succeeded)
            existing_state.pop(str(article_id), None)

        # Merge new upload results into existing state (preserves skipped articles)
        # and track the new file_ids for future cleanup
        successful_ids = upload_summary.get("successful_article_ids", [])
        new_file_ids = upload_summary.get("file_ids", {})
        state = existing_state
        state.update({
            str(change["article_id"]): {
                "updated_at": "",
                "hash": change["hash"],
                **({"file_id": new_file_ids[change["article_id"]]}
                   if change["article_id"] in new_file_ids else {}),
            }
            for change in [*sync_result.added, *sync_result.updated]
            if change["article_id"] in successful_ids
        })
        state_repository.save(state)
        logger.info("Saved sync state for %d articles", len(state))

        log_repository.append(
            {
                "status": "success",
                "added": len(sync_result.added),
                "updated": len(sync_result.updated),
                "skipped": len(sync_result.skipped),
                "removed": len(sync_result.removed),
                "upload": upload_summary,
            }
        )
        logger.info("Wrote logs")
    except Exception as exc:  # pragma: no cover - defensive entrypoint
        logger.exception("Synchronization failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
