from __future__ import annotations

import hashlib


def compute_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content* encoded as UTF-8."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
