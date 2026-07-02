from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SyncResult:
    """Represents the result of comparing current markdown against saved state."""

    added: list[dict[str, Any]]
    updated: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    removed: list[dict[str, Any]]
