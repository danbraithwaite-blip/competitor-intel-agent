"""SQLite Storage and persistence layer for competitor intelligence."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Table for page snapshots (pricing)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                clean_text TEXT NOT NULL,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Table for detected events (diffs and changelog items)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                raw_data TEXT NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_analyzed INTEGER DEFAULT 0
            )
            """)

            # Table for LLM strategic analyses
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                competitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                category TEXT NOT NULL,
                impact_level TEXT NOT NULL,
                summary TEXT NOT NULL,
                strategic_intent TEXT,
                counter_strategy TEXT,
                raw_llm_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES detected_events (id)
            )
            """)

            # Table for executive briefings
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_markdown TEXT NOT NULL,
                content_html TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Indexes for fast lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_comp ON page_snapshots(competitor_id, target_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_comp ON detected_events(competitor_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_analyzed ON detected_events(is_analyzed);")
            conn.commit()

    # --- Page Snapshot methods ---

    def get_latest_snapshot(self, competitor_id: str, target_type: str = "pricing") -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, competitor_id, target_type, url, content_hash, clean_text, captured_at
                FROM page_snapshots
                WHERE competitor_id = ? AND target_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (competitor_id, target_type),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_snapshot(self, competitor_id: str, target_type: str, url: str, content_hash: str, clean_text: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO page_snapshots (competitor_id, target_type, url, content_hash, clean_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (competitor_id, target_type, url, content_hash, clean_text),
            )
            conn.commit()
            return cursor.lastrowid

    # --- Event methods ---

    def record_event(self, competitor_id: str, event_type: str, title: str, raw_data: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO detected_events (competitor_id, event_type, title, raw_data, is_analyzed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (competitor_id, event_type, title, json.dumps(raw_data)),
            )
            conn.commit()
            return cursor.lastrowid

    def event_exists(self, competitor_id: str, event_type: str, title: str) -> bool:
        """Check if an event with this title was already recorded to avoid duplicates."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM detected_events
                WHERE competitor_id = ? AND event_type = ? AND title = ?
                LIMIT 1
                """,
                (competitor_id, event_type, title),
            )
            return cursor.fetchone() is not None

    def get_unanalyzed_events(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, competitor_id, event_type, title, raw_data, detected_at
                FROM detected_events
                WHERE is_analyzed = 0
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["raw_data"] = json.loads(d["raw_data"])
                results.append(d)
            return results

    def mark_event_analyzed(self, event_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE detected_events SET is_analyzed = 1 WHERE id = ?", (event_id,))
            conn.commit()

    # --- Analysis methods ---

    def save_analysis(
        self,
        event_id: int,
        competitor_id: str,
        event_type: str,
        category: str,
        impact_level: str,
        summary: str,
        strategic_intent: str,
        counter_strategy: str,
        raw_llm_json: str,
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO analysis_results (
                    event_id, competitor_id, event_type, category,
                    impact_level, summary, strategic_intent,
                    counter_strategy, raw_llm_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    competitor_id,
                    event_type,
                    category,
                    impact_level,
                    summary,
                    strategic_intent,
                    counter_strategy,
                    raw_llm_json,
                ),
            )
            cursor.execute("UPDATE detected_events SET is_analyzed = 1 WHERE id = ?", (event_id,))
            conn.commit()
            return cursor.lastrowid

    def get_recent_analyses(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.id, a.event_id, a.competitor_id, a.event_type, a.category,
                       a.impact_level, a.summary, a.strategic_intent, a.counter_strategy,
                       a.raw_llm_json, a.created_at, e.title as event_title
                FROM analysis_results a
                JOIN detected_events e ON a.event_id = e.id
                ORDER BY a.id DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Briefing methods ---

    def save_briefing(self, title: str, markdown: str, html: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO briefings (title, content_markdown, content_html)
                VALUES (?, ?, ?)
                """,
                (title, markdown, html),
            )
            conn.commit()
            return cursor.lastrowid

    def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
