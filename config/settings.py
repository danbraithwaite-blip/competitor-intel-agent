"""Application settings and competitor configuration loader."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import yaml
from dotenv import load_dotenv

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure data and reports directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file from project root
load_dotenv(BASE_DIR / ".env")


class PricingConfig(BaseModel):
    url: str
    selector: Optional[str] = "main"


class ChangelogConfig(BaseModel):
    type: str = "feed"  # "feed" or "web_page"
    url: str
    selector: Optional[str] = None


class CompetitorConfig(BaseModel):
    id: str
    name: str
    website: str
    description: Optional[str] = ""
    pricing: Optional[PricingConfig] = None
    changelog: Optional[ChangelogConfig] = None


class CompanyProfile(BaseModel):
    name: str = "Veremark"
    description: str = "Global pre-employment screening, credential verification, and background checking platform."
    core_offerings: List[str] = Field(default_factory=lambda: [
        "Identity verification (IDV) and biometric checks",
        "Global criminal record checks and sanctions screening",
        "Employment history and education verification",
        "Automated digital reference checking (Autocheck)",
        "Continuous workforce monitoring and compliance",
        "ATS and HRIS integrations (Greenhouse, Workday, Lever, BambooHR, etc.)"
    ])
    strategic_focus_areas: List[str] = Field(default_factory=lambda: [
        "Pricing per check, package bundling, subscription vs pay-as-you-go",
        "Turnaround times and international SLA guarantees",
        "New ATS/HRIS integration announcements",
        "Regulatory compliance changes (GDPR, FCRA, UK DBS)",
        "AI-driven screening features and candidate experience workflows"
    ])


class Settings(BaseModel):
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"))
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "claude"))
    min_diff_lines: int = Field(default_factory=lambda: int(os.getenv("MIN_DIFF_LINES", "2")))
    slack_webhook_url: Optional[str] = Field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL"))
    discord_webhook_url: Optional[str] = Field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL"))
    db_path: Path = DATA_DIR / "intel.db"
    config_file: Path = CONFIG_DIR / "competitors.yaml"
    reports_dir: Path = REPORTS_DIR


settings = Settings()


def load_company_profile(config_path: Optional[Path] = None) -> CompanyProfile:
    """Load the target company profile and focus areas from YAML."""
    path = config_path or settings.config_file
    if not path.exists():
        return CompanyProfile()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "company" not in data:
        return CompanyProfile()

    return CompanyProfile(**data["company"])


def load_competitors(config_path: Optional[Path] = None) -> List[CompetitorConfig]:
    """Load and validate the list of competitors from YAML."""
    path = config_path or settings.config_file
    if not path.exists():
        raise FileNotFoundError(f"Competitor configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "competitors" not in data:
        return []

    return [CompetitorConfig(**comp) for comp in data["competitors"]]
