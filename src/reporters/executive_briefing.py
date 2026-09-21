"""Executive briefing generator in Markdown, HTML, and Rich terminal format."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.storage.db import Database


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --high: #ef4444;
      --medium: #f59e0b;
      --low: #10b981;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      margin: 0;
      padding: 40px 20px;
    }
    .container {
      max-width: 1000px;
      margin: 0 auto;
    }
    header {
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 24px;
      margin-bottom: 32px;
    }
    h1 {
      font-size: 2rem;
      margin: 0 0 8px 0;
      color: #fff;
    }
    .meta {
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-high { background: rgba(239, 68, 68, 0.2); color: var(--high); border: 1px solid var(--high); }
    .badge-medium { background: rgba(245, 158, 11, 0.2); color: var(--medium); border: 1px solid var(--medium); }
    .badge-low { background: rgba(16, 185, 129, 0.2); color: var(--low); border: 1px solid var(--low); }
    
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      text-align: center;
    }
    .stat-value {
      font-size: 2rem;
      font-weight: 700;
      color: var(--accent);
    }
    .stat-label {
      color: var(--text-muted);
      font-size: 0.85rem;
      text-transform: uppercase;
    }

    .section-title {
      font-size: 1.35rem;
      margin: 40px 0 16px 0;
      display: flex;
      align-items: center;
      gap: 8px;
      border-left: 4px solid var(--accent);
      padding-left: 12px;
    }

    .intel-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0;
      color: #fff;
    }
    .competitor-tag {
      font-size: 0.85rem;
      color: var(--accent);
      font-weight: 600;
    }
    .field {
      margin-top: 10px;
      font-size: 0.95rem;
    }
    .field-label {
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 2px;
    }
    .counter-strategy {
      background: rgba(56, 189, 248, 0.08);
      border-left: 3px solid var(--accent);
      padding: 10px 14px;
      margin-top: 12px;
      border-radius: 0 4px 4px 0;
    }
    .empty-state {
      background: var(--card-bg);
      border: 1px dashed var(--card-border);
      padding: 24px;
      text-align: center;
      color: var(--text-muted);
      border-radius: 8px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{{ title }}</h1>
      <div class="meta">Generated: {{ generated_at }} | Analysis Model: Gemini Intelligence Engine</div>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ total_events }}</div>
        <div class="stat-label">Total Events Analyzed</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ pricing_events|length }}</div>
        <div class="stat-label">Pricing Movements</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ product_events|length }}</div>
        <div class="stat-label">Product Releases</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ high_impact_count }}</div>
        <div class="stat-label">High Threat Signals</div>
      </div>
    </div>

    <!-- Pricing Section -->
    <h2 class="section-title">Pricing & Packaging Movements</h2>
    {% if pricing_events %}
      {% for item in pricing_events %}
      <div class="intel-card">
        <div class="card-header">
          <div>
            <span class="competitor-tag">{{ item.competitor_id | upper }}</span>
            <h3 class="card-title">{{ item.category }}</h3>
          </div>
          <span class="badge badge-{{ item.impact_level | lower }}">{{ item.impact_level }} IMPACT</span>
        </div>
        <div class="field">
          <span class="field-label">Executive Summary</span>
          {{ item.summary }}
        </div>
        <div class="field">
          <span class="field-label">Strategic Intent (Why they did this)</span>
          {{ item.strategic_intent }}
        </div>
        <div class="counter-strategy">
          <span class="field-label" style="color: var(--accent);">Recommended Counter-Strategy</span>
          {{ item.counter_strategy }}
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty-state">No pricing or packaging changes detected in this reporting period.</div>
    {% endif %}

    <!-- Product Releases Section -->
    <h2 class="section-title">Product Releases & Changelogs</h2>
    {% if product_events %}
      {% for item in product_events %}
      <div class="intel-card">
        <div class="card-header">
          <div>
            <span class="competitor-tag">{{ item.competitor_id | upper }}</span>
            <h3 class="card-title">{{ item.event_title }}</h3>
          </div>
          <span class="badge badge-{{ item.impact_level | lower }}">{{ item.impact_level }} THREAT</span>
        </div>
        <div class="field">
          <span class="field-label">Release Category</span>
          {{ item.category }}
        </div>
        <div class="field">
          <span class="field-label">Capability Overview</span>
          {{ item.summary }}
        </div>
        <div class="field">
          <span class="field-label">Competitive Implication</span>
          {{ item.strategic_intent }}
        </div>
        <div class="counter-strategy">
          <span class="field-label" style="color: var(--accent);">Recommended Action</span>
          {{ item.counter_strategy }}
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty-state">No product updates recorded in this reporting period.</div>
    {% endif %}
  </div>
</body>
</html>
"""


class BriefingReporter:
    def __init__(self, db: Database, reports_dir: Path):
        self.db = db
        self.reports_dir = reports_dir
        self.console = Console()

    def generate_briefing(self, title: Optional[str] = None) -> Dict[str, Any]:
        """Fetch recent analyses, generate Markdown and HTML briefings, and save to reports/."""
        now = datetime.now()
        report_title = title or f"Competitive Intelligence Briefing — {now.strftime('%b %d, %Y')}"
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        analyses = self.db.get_recent_analyses(limit=50)

        pricing_events = [a for a in analyses if a["event_type"] == "pricing_change"]
        product_events = [a for a in analyses if a["event_type"] == "product_update"]
        high_impact_count = sum(1 for a in analyses if a["impact_level"] == "HIGH")

        # 1. Render Markdown
        md_lines = [
            f"# {report_title}",
            f"*Generated at: {date_str} | Powered by Gemini Intelligence Engine*\n",
            "## Executive Summary",
            f"- **Total Monitored Events:** {len(analyses)}",
            f"- **Pricing Movements:** {len(pricing_events)}",
            f"- **Product Releases:** {len(product_events)}",
            f"- **High Threat Items:** {high_impact_count}\n",
            "---",
            "## 💰 Pricing & Packaging Radar\n",
        ]

        if pricing_events:
            for p in pricing_events:
                md_lines.extend(
                    [
                        f"### [{p['competitor_id'].upper()}] {p['category']} `[{p['impact_level']} IMPACT]`",
                        f"- **Summary:** {p['summary']}",
                        f"- **Strategic Intent:** {p['strategic_intent']}",
                        f"- **Recommended Counter-Move:** {p['counter_strategy']}\n",
                    ]
                )
        else:
            md_lines.append("*No pricing changes detected in this cycle.*\n")

        md_lines.extend(["---", "## 🚀 Product Updates & Changelogs\n"])

        if product_events:
            for pr in product_events:
                md_lines.extend(
                    [
                        f"### [{pr['competitor_id'].upper()}] {pr['event_title']} `[{pr['impact_level']} THREAT]`",
                        f"- **Category:** {pr['category']}",
                        f"- **Summary:** {pr['summary']}",
                        f"- **Competitive Implication:** {pr['strategic_intent']}",
                        f"- **Recommended Action:** {pr['counter_strategy']}\n",
                    ]
                )
        else:
            md_lines.append("*No product updates detected in this cycle.*\n")

        markdown_content = "\n".join(md_lines)

        # 2. Render HTML
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            title=report_title,
            generated_at=date_str,
            total_events=len(analyses),
            pricing_events=pricing_events,
            product_events=product_events,
            high_impact_count=high_impact_count,
        )

        # Save to database
        self.db.save_briefing(title=report_title, markdown=markdown_content, html=html_content)

        # Save to disk
        timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
        md_path = self.reports_dir / f"briefing_{timestamp_slug}.md"
        html_path = self.reports_dir / f"briefing_{timestamp_slug}.html"
        latest_md = self.reports_dir / "latest_briefing.md"
        latest_html = self.reports_dir / "latest_briefing.html"

        md_path.write_text(markdown_content, encoding="utf-8")
        html_path.write_text(html_content, encoding="utf-8")
        latest_md.write_text(markdown_content, encoding="utf-8")
        latest_html.write_text(html_content, encoding="utf-8")

        return {
            "title": report_title,
            "markdown_path": str(md_path),
            "html_path": str(html_path),
            "total_events": len(analyses),
            "pricing_count": len(pricing_events),
            "product_count": len(product_events),
            "high_threat_count": high_impact_count,
        }

    def print_terminal_summary(self, result: Dict[str, Any]):
        """Render a rich dashboard directly in the CLI."""
        analyses = self.db.get_recent_analyses(limit=15)

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]{result['title']}[/bold cyan]\n"
                f"[dim]Generated {result['total_events']} events analyzed | "
                f"HTML: {result['html_path']}[/dim]",
                title="⚡ Competitor Intelligence Digest",
                border_style="cyan",
            )
        )

        table = Table(title="Recent Strategic Intelligence Signals", show_header=True, header_style="bold magenta")
        table.add_column("Competitor", style="bold", width=14)
        table.add_column("Type", width=16)
        table.add_column("Impact", width=10)
        table.add_column("Strategic Summary", style="dim", width=45)

        for a in analyses:
            impact_style = (
                "bold red"
                if a["impact_level"] == "HIGH"
                else "bold yellow"
                if a["impact_level"] == "MEDIUM"
                else "green"
            )
            table.add_row(
                a["competitor_id"].upper(),
                a["category"],
                f"[{impact_style}]{a['impact_level']}[/{impact_style}]",
                a["summary"][:60] + "..." if len(a["summary"]) > 60 else a["summary"],
            )

        self.console.print(table)
        self.console.print()
