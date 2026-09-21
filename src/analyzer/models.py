"""Data models for structured LLM competitive analysis."""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class PricingAnalysisResult(BaseModel):
    category: Literal[
        "Price Increase",
        "Price Reduction",
        "New Tier Added",
        "Tier Discontinued",
        "Feature Re-gating",
        "Packaging & Limits Shift",
        "Promotional / Minor Copy",
    ] = Field(description="Primary category of the pricing change")
    impact_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Strategic impact level for competitors and customers"
    )
    summary: str = Field(description="Clear 1-2 sentence executive summary of the changes")
    key_changes: List[str] = Field(
        default_factory=list,
        description="Bulleted list of specific changes (e.g. Pro tier increased from $20 to $25/mo)",
    )
    strategic_intent: str = Field(
        description="Analysis of why the competitor made this move (e.g., driving enterprise expansion, increasing ARPU)"
    )
    counter_strategy: str = Field(
        description="Tactical advice for our sales, product, or marketing teams to counter or capitalize on this"
    )


class ProductUpdateAnalysisResult(BaseModel):
    category: Literal[
        "Major Feature Release",
        "Performance & Infrastructure",
        "Integration & Ecosystem",
        "UX & Workflow Improvement",
        "Enterprise & Security",
        "Minor Bug Fix / Polish",
    ] = Field(description="Classification of the product release")
    impact_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Competitive threat level of this release"
    )
    summary: str = Field(description="Concise executive summary of what was launched")
    highlighted_capabilities: List[str] = Field(
        default_factory=list,
        description="Key capabilities, tools, or APIs introduced in this update",
    )
    competitive_implication: str = Field(
        description="How this impacts market position (e.g. closes parity gap, introduces new differentiator)"
    )
    counter_strategy: str = Field(
        description="Recommended action for our roadmap, sales battlecards, or marketing positioning"
    )
