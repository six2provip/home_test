from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils.json_utils import append_jsonl


class LogRepository:
    """Persist synchronization log entries to a JSON-lines file."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def append(self, entry: dict[str, Any]) -> None:
        append_jsonl(self._file_path, entry)
