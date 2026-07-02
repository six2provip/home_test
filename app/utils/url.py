from __future__ import annotations

from urllib.parse import urlparse


def extract_relative_path(url: str | None) -> str | None:
    """Extract the relative path (with query string) from a full URL.

    Returns ``None`` when *url* is ``None``.
    """
    if url is None:
        return None
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path
