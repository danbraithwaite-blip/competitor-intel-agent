"""Unit tests for strategic analyzer and Gemini client fallback."""
import tempfile
from pathlib import Path
from src.analyzer.models import PricingAnalysisResult, ProductUpdateAnalysisResult
from src.analyzer.gemini_client import GeminiClient
from src.analyzer.engine import IntelligenceEngine
from src.storage.db import Database


def test_models_validation():
    p_data = {
        "category": "Price Increase",
        "impact_level": "HIGH",
        "summary": "Pro plan increased from $20 to $30.",
        "key_changes": ["Pro tier +50%"],
        "strategic_intent": "Drive higher ARPU.",
        "counter_strategy": "Run a switch campaign highlighting grandfathered rates.",
    }
    model = PricingAnalysisResult(**p_data)
    assert model.category == "Price Increase"
    assert model.impact_level == "HIGH"

    prod_data = {
        "category": "Major Feature Release",
        "impact_level": "MEDIUM",
        "summary": "Launched AI code completion assistant.",
        "highlighted_capabilities": ["Autocomplete", "Refactoring"],
        "competitive_implication": "Closes feature parity gap with our tooling.",
        "counter_strategy": "Accelerate our custom model support.",
    }
    prod_model = ProductUpdateAnalysisResult(**prod_data)
    assert prod_model.category == "Major Feature Release"


def test_intelligence_engine_offline_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        client = GeminiClient(api_key=None)  # Offline mode test

        # Record a mock pricing event
        db.record_event(
            competitor_id="linear",
            event_type="pricing_change",
            title="Pricing update detected (4 lines changed)",
            raw_data={
                "url": "https://linear.app/pricing",
                "changed_lines_count": 4,
                "diff": "- $10 per user\n+ $14 per user",
            },
        )

        # Record a mock product update event
        db.record_event(
            competitor_id="linear",
            event_type="product_update",
            title="Linear Asks: Real-time request workflows",
            raw_data={
                "title": "Linear Asks: Real-time request workflows",
                "link": "https://linear.app/changelog/asks",
                "summary": "Today we are launching Linear Asks to streamline internal requests directly from Slack.",
            },
        )

        assert len(db.get_unanalyzed_events()) == 2

        engine = IntelligenceEngine(db=db, client=client)
        analyzed_count = engine.process_unanalyzed_events()

        assert analyzed_count == 2
        assert len(db.get_unanalyzed_events()) == 0

        analyses = db.get_recent_analyses()
        assert len(analyses) == 2
        assert all(a["summary"] for a in analyses)
        assert all(a["counter_strategy"] for a in analyses)


def test_claude_client_offline_and_parsing():
    from src.analyzer.claude_client import ClaudeClient

    client = ClaudeClient(api_key=None)
    assert not client.is_configured

    # Test heuristic fallback for pricing
    res_pricing = client.generate_json(
        prompt="Analyze pricing diff: - $10 + $20",
        system_instruction="Analyze pricing change",
    )
    assert "summary" in res_pricing
    assert "counter_strategy" in res_pricing

    # Test JSON extraction with markdown code fences
    fence_raw = "```json\n{\"category\": \"Price Increase\", \"impact_level\": \"HIGH\"}\n```"
    parsed = client._extract_json(fence_raw)
    assert parsed["category"] == "Price Increase"
    assert parsed["impact_level"] == "HIGH"
