from __future__ import annotations

from pathlib import Path


def ensure_parent(path: str | Path) -> Path:
    """Create parent directories for *path* if they don't exist and return the Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str | Path, encoding: str = "utf-8") -> str:
    """Read and return the contents of a text file."""
    return Path(path).read_text(encoding=encoding)


def write_text(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    """Write *content* to *path*, creating parent directories as needed."""
    p = ensure_parent(path)
    p.write_text(content, encoding=encoding)
    return p
