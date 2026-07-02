from __future__ import annotations

import os


def require_env(name: str) -> str:
    """Return the environment variable *name* or raise a clear ``ValueError``."""
    value = os.environ.get(name)
    if value is None or value == "":
        raise ValueError(
            f"Missing required environment variable: {name}. "
            f"Set it in a .env file or export it in your shell."
        )
    return value
