"""Unit tests for SQLite storage layer."""
import tempfile
from pathlib import Path
from src.storage.db import Database


def test_database_snapshots_and_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_intel.db"
        db = Database(db_path)

        # 1. Test Snapshot
        db.save_snapshot(
            competitor_id="comp1",
            target_type="pricing",
            url="https://example.com/pricing",
            content_hash="abc123hash",
            clean_text="Starter: $10\nPro: $25\nEnterprise: Contact Us",
        )
        latest = db.get_latest_snapshot("comp1", "pricing")
        assert latest is not None
        assert latest["content_hash"] == "abc123hash"
        assert "Starter: $10" in latest["clean_text"]

        # 2. Test Event Recording & Deduplication
        assert not db.event_exists("comp1", "product_update", "Release 2.0")
        event_id = db.record_event(
            competitor_id="comp1",
            event_type="product_update",
            title="Release 2.0",
            raw_data={"summary": "New UI and faster speed"},
        )
        assert event_id == 1
        assert db.event_exists("comp1", "product_update", "Release 2.0")

        # 3. Test Unanalyzed Events
        unanalyzed = db.get_unanalyzed_events()
        assert len(unanalyzed) == 1
        assert unanalyzed[0]["id"] == event_id

        # 4. Test Save Analysis
        db.save_analysis(
            event_id=event_id,
            competitor_id="comp1",
            event_type="product_update",
            category="Major Feature Release",
            impact_level="HIGH",
            summary="Competitor rolled out v2.0 overhaul.",
            strategic_intent="Accelerate market adoption.",
            counter_strategy="Highlight our workflow advantages.",
            raw_llm_json="{}",
        )

        # Verify event is now marked analyzed
        unanalyzed_after = db.get_unanalyzed_events()
        assert len(unanalyzed_after) == 0

        # Verify recent analyses query
        analyses = db.get_recent_analyses()
        assert len(analyses) == 1
        assert analyses[0]["impact_level"] == "HIGH"
        assert analyses[0]["event_title"] == "Release 2.0"
