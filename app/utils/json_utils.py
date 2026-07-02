from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read and parse JSON from *path*.

    Returns *default* if the file does not exist or contains invalid JSON.
    """
    file_path = Path(path)
    if not file_path.exists():
        return default
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return default


def write_json(
    path: str | Path,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Write *data* as JSON to *path*, creating parent directories as needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=indent, ensure_ascii=ensure_ascii)
        handle.write("\n")


def append_jsonl(path: str | Path, entry: dict[str, Any]) -> None:
    """Append *entry* as a single JSON line to *path* (JSONL format).

    Creates parent directories as needed.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
