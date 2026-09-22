"""Intelligence engine orchestrating LLM analysis on detected events."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from src.analyzer.gemini_client import GeminiClient
from src.analyzer.models import PricingAnalysisResult, ProductUpdateAnalysisResult
from config.settings import load_company_profile, CompanyProfile
from src.storage.db import Database

logger = logging.getLogger("analyzer_engine")


def build_pricing_prompt(company: CompanyProfile) -> str:
    offerings_list = "\n".join(f"- {o}" for o in company.core_offerings)
    focus_list = "\n".join(f"- {f}" for f in company.strategic_focus_areas)

    return f"""You are a seasoned VP of Competitive Intelligence and Pricing Strategy advising {company.name}.

ABOUT {company.name.upper()}:
{company.description}

OUR CORE OFFERINGS:
{offerings_list}

OUR KEY STRATEGIC FOCUS AREAS:
{focus_list}

Your job is to analyze raw diffs from competitor pricing pages and extract high-value strategic signals specifically relevant to {company.name}.

Evaluate:
1. What specifically changed in the pricing tiers, price points, billing intervals, screening packages, or feature gating?
2. Ignore minor formatting or cosmetic text differences.
3. Classify into one of: 'Price Increase', 'Price Cut', 'New Tier Added', 'Tier Discontinued', 'Feature Re-gating', 'Packaging & Limits Shift', 'Promotional / Minor Copy'.
4. Assess strategic impact on {company.name}: HIGH (significant price hike, new tier, or gating core screening feature), MEDIUM (notable limit or packaging change), or LOW (minor adjustments).
5. Predict strategic intent (why they did this).
6. Give actionable counter-recommendations specifically for {company.name}'s sales, marketing, and product teams (e.g. sales battlecard talking points, pricing counter-proposals).

Respond strictly in valid JSON format matching this schema:
{{
  "category": "Price Increase" | "Price Cut" | "New Tier Added" | "Tier Discontinued" | "Feature Re-gating" | "Packaging & Limits Shift" | "Promotional / Minor Copy",
  "impact_level": "HIGH" | "MEDIUM" | "LOW",
  "summary": "1-2 sentence executive summary tailored to {company.name}",
  "key_changes": ["change 1", "change 2"],
  "strategic_intent": "explanation of competitor motives",
  "counter_strategy": "recommended action for {company.name}'s team"
}}
"""


def build_product_prompt(company: CompanyProfile) -> str:
    offerings_list = "\n".join(f"- {o}" for o in company.core_offerings)
    focus_list = "\n".join(f"- {f}" for f in company.strategic_focus_areas)

    return f"""You are a seasoned Chief Product Officer and Competitive Strategist advising {company.name}.

ABOUT {company.name.upper()}:
{company.description}

OUR CORE OFFERINGS:
{offerings_list}

OUR KEY STRATEGIC FOCUS AREAS:
{focus_list}

Your job is to analyze competitor changelogs and release notes to assess market threat, capability parity, and competitive implications for {company.name}.

Evaluate:
1. What new capabilities, integrations, screening workflows, or compliance features did they launch?
2. Classify into one of: 'Major Feature Release', 'Performance & Infrastructure', 'Integration & Ecosystem', 'UX & Workflow Improvement', 'Enterprise & Security', 'Minor Bug Fix / Polish'.
3. Threat level to {company.name}: HIGH (major new capability that challenges {company.name}'s differentiators), MEDIUM (solid feature or parity catch-up), LOW (routine update or polish).
4. Competitive implication: Does this close a gap with {company.name}, leapfrog our capabilities, or target our core customer base?
5. Counter-strategy: Recommended roadmap or positioning adjustments for {company.name}.

Respond strictly in valid JSON format matching this schema:
{{
  "category": "Major Feature Release" | "Performance & Infrastructure" | "Integration & Ecosystem" | "UX & Workflow Improvement" | "Enterprise & Security" | "Minor Bug Fix / Polish",
  "impact_level": "HIGH" | "MEDIUM" | "LOW",
  "summary": "1-2 sentence executive summary tailored to {company.name}",
  "highlighted_capabilities": ["capability 1", "capability 2"],
  "competitive_implication": "market position impact on {company.name}",
  "counter_strategy": "recommended roadmap or positioning action for {company.name}"
}}
"""


class IntelligenceEngine:
    def __init__(self, db: Database, client: Any, company_profile: Optional[CompanyProfile] = None):
        self.db = db
        self.client = client
        self.company_profile = company_profile or load_company_profile()

    def analyze_pricing_event(self, event: Dict[str, Any]) -> PricingAnalysisResult:
        raw_data = event["raw_data"]
        diff_snippet = raw_data.get("diff", "")[:3500]  # prevent overly large token payloads

        prompt = (
            f"Competitor ID: {event['competitor_id']}\n"
            f"Pricing URL: {raw_data.get('url', 'N/A')}\n"
            f"Lines changed: {raw_data.get('changed_lines_count', 'N/A')}\n\n"
            f"Unified Diff:\n```diff\n{diff_snippet}\n```"
        )

        json_data = self.client.generate_json(
            prompt=prompt,
            system_instruction=build_pricing_prompt(self.company_profile),
        )

        try:
            result = PricingAnalysisResult(**json_data)
        except Exception as e:
            logger.warning(f"Error validating PricingAnalysisResult schema: {e}. Falling back to default.")
            result = PricingAnalysisResult(
                category="Packaging & Limits Shift",
                impact_level="MEDIUM",
                summary=str(json_data.get("summary", "Pricing change detected.")),
                key_changes=json_data.get("key_changes", []),
                strategic_intent=str(json_data.get("strategic_intent", "Monetization refinement.")),
                counter_strategy=str(json_data.get("counter_strategy", "Review sales battlecards.")),
            )

        self.db.save_analysis(
            event_id=event["id"],
            competitor_id=event["competitor_id"],
            event_type="pricing_change",
            category=result.category,
            impact_level=result.impact_level,
            summary=result.summary,
            strategic_intent=result.strategic_intent,
            counter_strategy=result.counter_strategy,
            raw_llm_json=json.dumps(result.model_dump()),
        )
        return result

    def analyze_product_event(self, event: Dict[str, Any]) -> ProductUpdateAnalysisResult:
        raw_data = event["raw_data"]
        title = raw_data.get("title", event["title"])
        summary = raw_data.get("summary", "")[:2500]
        link = raw_data.get("link", "")

        prompt = (
            f"Competitor ID: {event['competitor_id']}\n"
            f"Release Title: {title}\n"
            f"Link: {link}\n\n"
            f"Release Notes Content:\n{summary}"
        )

        json_data = self.client.generate_json(
            prompt=prompt,
            system_instruction=build_product_prompt(self.company_profile),
        )

        try:
            result = ProductUpdateAnalysisResult(**json_data)
        except Exception as e:
            logger.warning(f"Error validating ProductUpdateAnalysisResult schema: {e}. Falling back to default.")
            result = ProductUpdateAnalysisResult(
                category="Major Feature Release",
                impact_level="MEDIUM",
                summary=str(json_data.get("summary", title)),
                highlighted_capabilities=json_data.get("highlighted_capabilities", []),
                competitive_implication=str(json_data.get("competitive_implication", "Feature parity update.")),
                counter_strategy=str(json_data.get("counter_strategy", "Evaluate customer demand.")),
            )

        self.db.save_analysis(
            event_id=event["id"],
            competitor_id=event["competitor_id"],
            event_type="product_update",
            category=result.category,
            impact_level=result.impact_level,
            summary=result.summary,
            strategic_intent=result.competitive_implication,
            counter_strategy=result.counter_strategy,
            raw_llm_json=json.dumps(result.model_dump()),
        )
        return result

    def process_unanalyzed_events(self) -> int:
        """Fetch all unanalyzed events from storage and run strategic intelligence analysis."""
        events = self.db.get_unanalyzed_events()
        if not events:
            logger.info("No unanalyzed events found.")
            return 0

        logger.info(f"Processing {len(events)} unanalyzed competitive events...")
        count = 0
        for event in events:
            try:
                if event["event_type"] == "pricing_change":
                    self.analyze_pricing_event(event)
                elif event["event_type"] == "product_update":
                    self.analyze_product_event(event)
                else:
                    self.db.mark_event_analyzed(event["id"])
                count += 1
            except Exception as e:
                logger.error(f"Failed to analyze event #{event['id']} ({event['event_type']}): {e}")

        logger.info(f"Successfully analyzed {count} events.")
        return count
