"""Slack integration for posting executive competitor intelligence briefings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("slack_publisher")


class SlackPublisher:
    def __init__(self, webhook_url: Optional[str] = None, timeout: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.strip() and self.webhook_url.startswith("https://hooks.slack.com/"))

    def send_test_message(self) -> bool:
        """Send a test message to verify Slack webhook configuration."""
        if not self.is_configured:
            logger.error("Slack webhook URL is not configured or invalid.")
            return False

        payload = {
            "text": "⚡ Competitor Intelligence Agent: Slack connection verified successfully!",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚡ Competitor Intelligence Agent",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Your Slack webhook is connected and ready to receive competitive intelligence briefings!",
                    },
                },
            ],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.webhook_url, json=payload)
                res.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack test message: {e}")
            return False

    def send_briefing(self, title: str, analyses: List[Dict[str, Any]]) -> bool:
        """Format analyses into Slack Block Kit payload and send to channel."""
        if not self.is_configured:
            logger.warning("Slack webhook URL is not configured in .env. Skipping Slack broadcast.")
            return False

        pricing_events = [a for a in analyses if a["event_type"] == "pricing_change"]
        product_events = [a for a in analyses if a["event_type"] == "product_update"]
        high_threat_count = sum(1 for a in analyses if a["impact_level"] == "HIGH")

        # Slack Block Kit blocks (capped to 50 blocks max per message)
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚡ {title[:140]}",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"📊 *{len(analyses)} Events* | "
                            f"💰 *{len(pricing_events)} Pricing Shifts* | "
                            f"🚀 *{len(product_events)} Releases* | "
                            f"🚨 *{high_threat_count} High Threat*"
                        ),
                    }
                ],
            },
            {"type": "divider"},
        ]

        # 1. Pricing Movements
        if pricing_events:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*💰 PRICING & PACKAGING MOVEMENTS*",
                    },
                }
            )

            for p in pricing_events[:5]:  # limit to top 5 for readability
                impact_badge = (
                    "🚨 `HIGH IMPACT`"
                    if p["impact_level"] == "HIGH"
                    else "⚠️ `MEDIUM IMPACT`"
                    if p["impact_level"] == "MEDIUM"
                    else "🟢 `LOW IMPACT`"
                )
                comp = p["competitor_id"].upper()
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*{comp}* — {p['category']} | {impact_badge}\n"
                                f"• *Summary:* {p['summary']}\n"
                                f"• *Strategic Intent:* _{p['strategic_intent']}_\n"
                                f"• *Counter-Strategy:* `{p['counter_strategy']}`"
                            ),
                        },
                    }
                )
            blocks.append({"type": "divider"})

        # 2. Product Updates
        if product_events:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🚀 PRODUCT RELEASES & CHANGELOGS*",
                    },
                }
            )

            for pr in product_events[:8]:  # limit to top 8
                impact_badge = (
                    "🚨 `HIGH THREAT`"
                    if pr["impact_level"] == "HIGH"
                    else "⚠️ `MEDIUM THREAT`"
                    if pr["impact_level"] == "MEDIUM"
                    else "🟢 `LOW THREAT`"
                )
                comp = pr["competitor_id"].upper()
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*{comp}* — *{pr['event_title']}* | {impact_badge}\n"
                                f"• *Category:* {pr['category']}\n"
                                f"• *Summary:* {pr['summary']}\n"
                                f"• *Implication:* _{pr['strategic_intent']}_\n"
                                f"• *Action:* `{pr['counter_strategy']}`"
                            ),
                        },
                    }
                )

        payload = {
            "text": f"⚡ {title}: {len(analyses)} new competitive events analyzed.",
            "blocks": blocks[:48],  # safe Slack block limit
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.webhook_url, json=payload)
                res.raise_for_status()
                logger.info("Successfully delivered briefing to Slack channel.")
                return True
        except Exception as e:
            logger.error(f"Failed to post briefing to Slack: {e}")
            return False
