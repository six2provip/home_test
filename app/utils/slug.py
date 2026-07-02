from __future__ import annotations

import re
import unicodedata

_PATTERN = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_WHITESPACE = re.compile(r"[-\s]+")


def to_slug(text: str, *, lower: bool = True) -> str:
    """Convert *text* into a URL-safe slug.

    Normalises Unicode, strips non-alphanumeric characters (except hyphens
    and spaces), collapses whitespace/hyphens into a single hyphen, and
    optionally lowercases the result.

    Examples:
        >>> to_slug("Hello World!")
        'hello-world'
        >>> to_slug("What's New in v2.0", lower=False)
        'Whats-New-in-v20'
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = _PATTERN.sub("", text).strip()
    text = _WHITESPACE.sub("-", text)
    return text.lower() if lower else text
