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


class Settings(BaseModel):
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"))
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
