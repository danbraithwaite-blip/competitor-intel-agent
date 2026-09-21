"""Pricing page monitor with noise reduction and structural diffing."""
from __future__ import annotations

import difflib
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from src.collectors.base import BaseCollector
from src.storage.db import Database
from config.settings import PricingConfig

logger = logging.getLogger("pricing_collector")


class PricingCollector(BaseCollector):
    def __init__(self, db: Database, min_diff_lines: int = 2, timeout: float = 15.0):
        super().__init__(timeout=timeout)
        self.db = db
        self.min_diff_lines = min_diff_lines

    def clean_html(self, html_content: str, selector: Optional[str] = None) -> str:
        """Strip boilerplate (scripts, styles, nav, footers, cookie banners) and return clean normalized text."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip noisy elements
        for element in soup.find_all(
            ["script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form"]
        ):
            element.decompose()

        # Remove elements with common noise classes/ids
        noise_pattern = re.compile(r"(cookie|banner|consent|modal|popup|newsletter|advertisement)", re.I)
        for element in soup.find_all(attrs={"class": noise_pattern}):
            element.decompose()
        for element in soup.find_all(attrs={"id": noise_pattern}):
            element.decompose()

        # Target specific container if selector is given
        target = None
        if selector:
            target = soup.select_one(selector)
        if not target:
            target = soup.body or soup

        # Extract text line by line, preserving logical breaks
        lines = []
        for tag in target.find_all(["h1", "h2", "h3", "h4", "p", "li", "span", "div", "td", "th"]):
            # Only consider tags that have direct string children or short text
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 1:
                # Discard dynamic timestamps, copyright notices
                if re.match(r"^©\s*\d{4}", text) or re.search(r"\ball rights reserved\b", text, re.I):
                    continue
                lines.append(text)

        # Deduplicate consecutive identical lines (e.g. repeated buttons or nested divs)
        deduped = []
        for line in lines:
            # normalize internal whitespace
            clean = re.sub(r"\s+", " ", line).strip()
            if clean and (not deduped or deduped[-1] != clean):
                deduped.append(clean)

        return "\n".join(deduped)

    def compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def generate_diff(self, old_text: str, new_text: str) -> str:
        """Generate a unified diff between old and new pricing text."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="previous_pricing",
            tofile="current_pricing",
            lineterm="",
        )
        return "\n".join(diff)

    def count_significant_changes(self, diff_text: str) -> int:
        """Count lines added or removed in diff, excluding metadata lines."""
        count = 0
        for line in diff_text.splitlines():
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                # exclude whitespace-only changes
                if line[1:].strip():
                    count += 1
        return count

    def collect(self, competitor_id: str, pricing_config: PricingConfig) -> Optional[Dict[str, Any]]:
        """Fetch pricing page, compare with latest snapshot, and record event if significant changes detected."""
        logger.info(f"Checking pricing page for [{competitor_id}]: {pricing_config.url}")
        try:
            response = self.fetch_url(pricing_config.url)
            clean_text = self.clean_html(response.text, selector=pricing_config.selector)
            current_hash = self.compute_hash(clean_text)

            latest_snapshot = self.db.get_latest_snapshot(competitor_id, target_type="pricing")

            if not latest_snapshot:
                # Initial snapshot baseline
                self.db.save_snapshot(
                    competitor_id=competitor_id,
                    target_type="pricing",
                    url=pricing_config.url,
                    content_hash=current_hash,
                    clean_text=clean_text,
                )
                logger.info(f"Saved initial pricing baseline for [{competitor_id}].")
                return None

            if latest_snapshot["content_hash"] == current_hash:
                logger.info(f"No pricing changes detected for [{competitor_id}].")
                return None

            # Content hash changed; compute diff
            old_text = latest_snapshot["clean_text"]
            diff_text = self.generate_diff(old_text, clean_text)
            sig_changes = self.count_significant_changes(diff_text)

            logger.info(f"Diff detected for [{competitor_id}]: {sig_changes} modified lines.")

            if sig_changes >= self.min_diff_lines:
                # Save new snapshot
                self.db.save_snapshot(
                    competitor_id=competitor_id,
                    target_type="pricing",
                    url=pricing_config.url,
                    content_hash=current_hash,
                    clean_text=clean_text,
                )

                # Record pricing change event
                title = f"Pricing update detected ({sig_changes} lines changed)"
                event_data = {
                    "url": pricing_config.url,
                    "previous_hash": latest_snapshot["content_hash"],
                    "current_hash": current_hash,
                    "changed_lines_count": sig_changes,
                    "diff": diff_text,
                }
                event_id = self.db.record_event(
                    competitor_id=competitor_id,
                    event_type="pricing_change",
                    title=title,
                    raw_data=event_data,
                )
                logger.info(f"Recorded pricing_change event #{event_id} for [{competitor_id}].")
                return {"event_id": event_id, "competitor_id": competitor_id, "diff": diff_text}
            else:
                logger.info(f"Changes below noise threshold ({sig_changes} < {self.min_diff_lines}). Ignoring.")
                return None

        except Exception as e:
            logger.error(f"Failed to check pricing for [{competitor_id}]: {e}")
            return None
