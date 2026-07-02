from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils.json_utils import read_json, write_json


class StateRepository:
    """Persist sync state for processed articles."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def load(self) -> dict[str, Any]:
        result = read_json(self._file_path, default={})
        return result if isinstance(result, dict) else {}

    def save(self, state: dict[str, Any]) -> None:
        write_json(self._file_path, state)
