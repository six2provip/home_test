from __future__ import annotations

import re


def normalize_blank_lines(text: str) -> str:
    """Collapse excessive blank lines into at most two consecutive newlines.

    Strips trailing whitespace from each line, removes leading/trailing
    empty lines, and ensures no more than one blank line between content.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    normalized: list[str] = []
    previous_blank = False

    for line in lines:
        if not line.strip():
            if not previous_blank:
                normalized.append("")
                previous_blank = True
        else:
            normalized.append(line)
            previous_blank = False

    content = "\n".join(normalized).strip()
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content
