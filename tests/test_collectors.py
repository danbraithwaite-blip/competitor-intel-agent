"""Unit tests for pricing and changelog collectors."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from src.collectors.pricing_collector import PricingCollector
from src.collectors.changelog_collector import ChangelogCollector
from src.storage.db import Database
from config.settings import PricingConfig


def test_pricing_collector_cleaning_and_diffing():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        collector = PricingCollector(db=db, min_diff_lines=2)

        sample_html_v1 = """
        <html>
        <head><script>alert("tracker");</script></head>
        <body>
            <nav><a href="/">Home</a></nav>
            <div class="cookie-banner">Accept our cookies</div>
            <main>
                <h1>Our Plans</h1>
                <div class="plan">
                    <h2>Starter</h2>
                    <p>$10 / month</p>
                    <ul><li>5 users</li></ul>
                </div>
                <div class="plan">
                    <h2>Pro</h2>
                    <p>$30 / month</p>
                    <ul><li>Unlimited users</li></ul>
                </div>
            </main>
            <footer>© 2026 Acme Corp. All rights reserved.</footer>
        </body>
        </html>
        """

        clean_v1 = collector.clean_html(sample_html_v1, selector="main")
        assert "Our Plans" in clean_v1
        assert "Starter" in clean_v1
        assert "$10 / month" in clean_v1
        assert "Accept our cookies" not in clean_v1
        assert "alert" not in clean_v1
        assert "All rights reserved" not in clean_v1

        sample_html_v2 = sample_html_v1.replace("$30 / month", "$45 / month")
        clean_v2 = collector.clean_html(sample_html_v2, selector="main")

        diff = collector.generate_diff(clean_v1, clean_v2)
        assert "-$30 / month" in diff
        assert "+$45 / month" in diff

        changes = collector.count_significant_changes(diff)
        assert changes >= 2


def test_pricing_collector_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        collector = PricingCollector(db=db, min_diff_lines=2)

        config = PricingConfig(url="https://mock.example.com/pricing", selector="main")

        # Mock fetch_url
        mock_response_v1 = MagicMock()
        mock_response_v1.text = "<main><h1>Plans</h1><p>Pro: $20</p></main>"

        collector.fetch_url = MagicMock(return_value=mock_response_v1)

        # First run: should save initial baseline, return None
        res1 = collector.collect("comp_test", config)
        assert res1 is None
        snapshot = db.get_latest_snapshot("comp_test", "pricing")
        assert snapshot is not None
        assert "Pro: $20" in snapshot["clean_text"]

        # Second run (no change): should return None
        res2 = collector.collect("comp_test", config)
        assert res2 is None

        # Third run (price increase to $29): should detect diff and record event
        mock_response_v2 = MagicMock()
        mock_response_v2.text = "<main><h1>Plans</h1><p>Pro: $29</p></main>"
        collector.fetch_url = MagicMock(return_value=mock_response_v2)

        res3 = collector.collect("comp_test", config)
        assert res3 is not None
        assert res3["competitor_id"] == "comp_test"

        events = db.get_unanalyzed_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "pricing_change"
