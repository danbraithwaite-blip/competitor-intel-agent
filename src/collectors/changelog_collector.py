"""Changelog and product update collector supporting RSS/Atom feeds and HTML pages."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import feedparser

from src.collectors.base import BaseCollector
from src.storage.db import Database
from config.settings import ChangelogConfig

logger = logging.getLogger("changelog_collector")


class ChangelogCollector(BaseCollector):
    def __init__(self, db: Database, timeout: float = 15.0):
        super().__init__(timeout=timeout)
        self.db = db

    def strip_html(self, raw_html: str) -> str:
        """Helper to convert HTML description into readable plaintext."""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    def collect_from_feed(self, competitor_id: str, feed_url: str) -> List[Dict[str, Any]]:
        """Parse RSS or Atom feed and record new changelog / product entries."""
        logger.info(f"Checking changelog feed for [{competitor_id}]: {feed_url}")
        new_events = []

        try:
            # We fetch via httpx client to ensure proper headers and timeout
            response = self.fetch_url(feed_url)
            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parsing error for [{competitor_id}]: {feed.bozo_exception}")

            # Process most recent entries (up to 10)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Check if this update has already been recorded
                if self.db.event_exists(competitor_id=competitor_id, event_type="product_update", title=title):
                    continue

                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))
                summary_raw = entry.get("summary", entry.get("description", ""))
                clean_summary = self.strip_html(summary_raw)

                event_data = {
                    "source_type": "feed",
                    "title": title,
                    "link": link,
                    "published_at": published,
                    "summary": clean_summary[:2000],  # cap to reasonable size
                }

                event_id = self.db.record_event(
                    competitor_id=competitor_id,
                    event_type="product_update",
                    title=title,
                    raw_data=event_data,
                )
                logger.info(f"Recorded new product update event #{event_id} for [{competitor_id}]: '{title}'")
                new_events.append({"event_id": event_id, "competitor_id": competitor_id, "title": title})

        except Exception as e:
            logger.error(f"Failed to fetch changelog feed for [{competitor_id}]: {e}")

        return new_events

    def collect_from_page(
        self, competitor_id: str, page_url: str, selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Scrape product changelog from an HTML page."""
        logger.info(f"Checking changelog webpage for [{competitor_id}]: {page_url}")
        new_events = []

        try:
            response = self.fetch_url(page_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Find release articles or sections
            container = soup.select_one(selector) if selector else soup
            items = container.find_all(["article", "section", "div"], class_=lambda c: c and ("release" in c or "changelog" in c or "post" in c))

            if not items:
                # Fallback to headings
                items = container.find_all(["h2", "h3"])

            for item in items[:10]:
                title_tag = item if item.name in ["h2", "h3"] else item.find(["h2", "h3", "h1"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                if self.db.event_exists(competitor_id=competitor_id, event_type="product_update", title=title):
                    continue

                content = item.get_text(separator="\n", strip=True)
                event_data = {
                    "source_type": "web_page",
                    "title": title,
                    "link": page_url,
                    "summary": content[:2000],
                }

                event_id = self.db.record_event(
                    competitor_id=competitor_id,
                    event_type="product_update",
                    title=title,
                    raw_data=event_data,
                )
                logger.info(f"Recorded new product update event #{event_id} from page for [{competitor_id}]: '{title}'")
                new_events.append({"event_id": event_id, "competitor_id": competitor_id, "title": title})

        except Exception as e:
            logger.error(f"Failed to scrape changelog page for [{competitor_id}]: {e}")

        return new_events

    def collect(self, competitor_id: str, changelog_config: ChangelogConfig) -> List[Dict[str, Any]]:
        if changelog_config.type == "web_page":
            return self.collect_from_page(competitor_id, changelog_config.url, changelog_config.selector)
        return self.collect_from_feed(competitor_id, changelog_config.url)
