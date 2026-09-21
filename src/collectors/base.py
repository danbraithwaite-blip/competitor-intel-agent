"""Base collector module for fetching and processing web resources."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("collector")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseCollector(ABC):
    """Abstract base class for data collectors."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Fetch a URL with standard retry and user-agent headers."""
        req_headers = {**DEFAULT_HEADERS, **(headers or {})}
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=req_headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response

    @abstractmethod
    def collect(self, competitor_id: str, config: Any) -> Any:
        """Execute the collection routine."""
        pass
