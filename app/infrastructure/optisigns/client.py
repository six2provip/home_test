from typing import Any

import requests

from app.config.settings import Settings


class OptiSignsClient:
    """Low-level HTTP client for the OptiSigns Help Center API."""

    def __init__(self, settings: Settings, timeout: int = 30) -> None:
        self._base_url = settings.OPTISIGNS_BASE_URL.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "OptiBot/1.0",
            }
        )

    def get(self, path: str) -> dict[str, Any]:
        """Perform a GET request and return the parsed JSON response."""
        url = f"{self._base_url}{path}"
        response = self._session.get(url, timeout=self._timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise requests.HTTPError(
                f"OptiSigns API returned {response.status_code} for GET {path}: "
                f"{response.text}"
            )
        return response.json()
