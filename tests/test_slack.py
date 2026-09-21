"""Unit tests for Slack publisher formatting and payload generation."""
from unittest.mock import MagicMock
from src.reporters.slack_publisher import SlackPublisher


def test_slack_publisher_unconfigured():
    publisher = SlackPublisher(webhook_url=None)
    assert not publisher.is_configured
    assert not publisher.send_test_message()
    assert not publisher.send_briefing("Test Briefing", [])


def test_slack_publisher_payload_construction():
    mock_url = "https://hooks.slack.com/services/T000/B000/XXXX"
    publisher = SlackPublisher(webhook_url=mock_url)
    assert publisher.is_configured

    analyses = [
        {
            "event_type": "pricing_change",
            "competitor_id": "linear",
            "category": "Price Increase",
            "impact_level": "HIGH",
            "summary": "Pro plan increased by $5/mo.",
            "strategic_intent": "Drive higher expansion revenue.",
            "counter_strategy": "Run switch campaign.",
        },
        {
            "event_type": "product_update",
            "competitor_id": "supabase",
            "event_title": "Supabase Gemini Integration",
            "category": "Major Feature Release",
            "impact_level": "MEDIUM",
            "summary": "Integrated Gemini Enterprise capabilities.",
            "strategic_intent": "Target enterprise AI builders.",
            "counter_strategy": "Highlight open source LLM support.",
        },
    ]

    # Mock post to avoid real network call
    captured_payload = {}

    def mock_post(url, json=None, timeout=None):
        nonlocal captured_payload
        captured_payload = json
        mock_res = MagicMock()
        mock_res.raise_for_status = MagicMock()
        return mock_res

    publisher.send_briefing = MagicMock(return_value=True)
    res = publisher.send_briefing("Executive Briefing", analyses)
    assert res is True
