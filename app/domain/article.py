from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    """Represents one OptiSigns Help Center article."""

    id: int
    title: str
    body_html: str
    html_url: str
    updated_at: str
