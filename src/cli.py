"""CLI management and execution commands for the Competitor Intelligence Agent."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional
import yaml
from rich.console import Console

from config.settings import settings, load_competitors
from src.storage.db import Database
from src.collectors.pricing_collector import PricingCollector
from src.collectors.changelog_collector import ChangelogCollector
from src.analyzer.gemini_client import GeminiClient
from src.analyzer.claude_client import ClaudeClient
from src.analyzer.engine import IntelligenceEngine
from src.reporters.executive_briefing import BriefingReporter
from src.reporters.slack_publisher import SlackPublisher

console = Console()


def cmd_track(args):
    """Run data collection across all configured competitors."""
    console.print("\n[bold cyan]🔍 Starting Competitor Monitoring Cycle...[/bold cyan]")
    competitors = load_competitors(settings.config_file)
    if not competitors:
        console.print("[yellow]No competitors configured in config/competitors.yaml.[/yellow]")
        return

    db = Database(settings.db_path)
    pricing_collector = PricingCollector(db=db, min_diff_lines=settings.min_diff_lines)
    changelog_collector = ChangelogCollector(db=db)

    total_pricing_events = 0
    total_changelog_events = 0

    for comp in competitors:
        console.print(f"\n[bold]Checking [cyan]{comp.name}[/cyan] ({comp.id})...[/bold]")

        # 1. Pricing Page
        if comp.pricing:
            res = pricing_collector.collect(competitor_id=comp.id, pricing_config=comp.pricing)
            if res:
                total_pricing_events += 1
                console.print(f"  [bold green]✓ Pricing change detected![/bold green]")
            else:
                console.print(f"  [dim]• Pricing page checked (no new changes).[/dim]")

        # 2. Product Changelog
        if comp.changelog:
            events = changelog_collector.collect(competitor_id=comp.id, changelog_config=comp.changelog)
            if events:
                total_changelog_events += len(events)
                console.print(f"  [bold green]✓ Recorded {len(events)} new product updates.[/bold green]")
            else:
                console.print(f"  [dim]• Changelog checked (up to date).[/dim]")

    console.print(
        f"\n[bold green]✓ Monitoring complete![/bold green] "
        f"New pricing changes: [bold]{total_pricing_events}[/bold], "
        f"New product updates: [bold]{total_changelog_events}[/bold]\n"
    )


def cmd_analyze(args):
    """Run LLM intelligence analysis on newly detected events using Claude or Gemini."""
    console.print("\n[bold cyan]🧠 Starting Strategic Intelligence Analysis...[/bold cyan]")
    db = Database(settings.db_path)

    # Determine LLM client based on provider or configured keys
    if settings.llm_provider.lower() == "claude" or settings.anthropic_api_key:
        client = ClaudeClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
        provider_name = f"Anthropic Claude ({settings.anthropic_model})"
        key_var = "ANTHROPIC_API_KEY"
    else:
        client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        provider_name = f"Google Gemini ({settings.gemini_model})"
        key_var = "GEMINI_API_KEY"

    if not client.is_configured:
        console.print(
            f"[yellow]Notice: {key_var} is not set in your environment or .env file.\n"
            f"Using offline heuristic intelligence engine. To enable live AI synthesis, set {key_var}.[/yellow]\n"
        )
    else:
        console.print(f"[green]✓ Connected to {provider_name}[/green]")

    engine = IntelligenceEngine(db=db, client=client)
    analyzed_count = engine.process_unanalyzed_events()

    console.print(f"[bold green]✓ Analysis complete![/bold green] Analyzed {analyzed_count} events.\n")


def cmd_report(args):
    """Generate Markdown and HTML executive briefings, and optionally post to Slack."""
    console.print("\n[bold cyan]📊 Generating Executive Intelligence Briefing...[/bold cyan]")
    db = Database(settings.db_path)
    reporter = BriefingReporter(db=db, reports_dir=settings.reports_dir)

    result = reporter.generate_briefing(title=args.title if hasattr(args, "title") else None)
    reporter.print_terminal_summary(result)

    console.print(f"[bold green]✓ Briefings saved successfully:[/bold green]")
    console.print(f"  • Markdown: [cyan]{result['markdown_path']}[/cyan]")
    console.print(f"  • HTML Briefing: [cyan]{result['html_path']}[/cyan]\n")

    # Post to Slack if requested or configured
    if getattr(args, "slack", False):
        console.print("[cyan]📡 Dispatching briefing to Slack channel...[/cyan]")
        slack = SlackPublisher(webhook_url=settings.slack_webhook_url)
        if not slack.is_configured:
            console.print(
                "[yellow]Warning: Slack webhook not configured. Set SLACK_WEBHOOK_URL in .env to post directly to Slack.[/yellow]\n"
            )
        else:
            success = slack.send_briefing(result["title"], db.get_recent_analyses())
            if success:
                console.print("[bold green]✓ Briefing successfully posted to Slack channel![/bold green]\n")
            else:
                console.print("[bold red]✗ Failed to post briefing to Slack. Check logs and webhook URL.[/bold red]\n")


def cmd_test_slack(args):
    """Send a verification test message to the configured Slack webhook."""
    console.print("\n[bold cyan]🔔 Testing Slack Webhook Connection...[/bold cyan]")
    slack = SlackPublisher(webhook_url=settings.slack_webhook_url)

    if not slack.is_configured:
        console.print(
            "[red]Error: SLACK_WEBHOOK_URL is not set or invalid in your .env file.[/red]\n"
            "Format: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...\n"
        )
        return

    success = slack.send_test_message()
    if success:
        console.print("[bold green]✓ Test message delivered successfully to your Slack channel![/bold green]\n")
    else:
        console.print("[bold red]✗ Test message delivery failed. Please verify your webhook URL.[/bold red]\n")


def cmd_run_all(args):
    """Run full pipeline: track -> analyze -> report (with optional Slack dispatch)."""
    cmd_track(args)
    cmd_analyze(args)
    cmd_report(args)


def cmd_daemon(args):
    """Run continuously on a set interval schedule."""
    import time
    from datetime import datetime, timedelta

    interval_hours = getattr(args, "interval_hours", 24) or 24
    interval_seconds = int(interval_hours * 3600)

    console.print(f"\n[bold cyan]🔄 Running Competitor Intelligence Daemon (Every {interval_hours} hours)...[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop the daemon at any time.[/dim]\n")

    while True:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"[bold]▶ Scan cycle triggered at {now_str}[/bold]")
            cmd_run_all(args)

            next_run = (datetime.now() + timedelta(seconds=interval_seconds)).strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"[cyan]⏳ Next scan scheduled for: {next_run}. Sleeping...[/cyan]\n")
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            console.print("\n[yellow]Daemon stopped by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Unexpected error in daemon cycle: {e}[/red]")
            time.sleep(60)


def cmd_add_competitor(args):
    """Helper to register a new competitor in config/competitors.yaml."""
    console.print("\n[bold cyan]➕ Add New Competitor[/bold cyan]")
    comp_id = args.id or input("Competitor ID (slug, e.g. vercel): ").strip()
    name = args.name or input("Competitor Name (e.g. Vercel): ").strip()
    website = args.website or input("Website URL: ").strip()
    pricing_url = args.pricing_url or input("Pricing URL (optional, press Enter to skip): ").strip()
    changelog_url = args.changelog_url or input("Changelog Feed/Page URL (optional, press Enter to skip): ").strip()

    if not comp_id or not name:
        console.print("[red]Competitor ID and Name are required.[/red]")
        return

    with open(settings.config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {"competitors": []}

    new_comp = {
        "id": comp_id,
        "name": name,
        "website": website,
    }
    if pricing_url:
        new_comp["pricing"] = {"url": pricing_url, "selector": "main"}
    if changelog_url:
        new_comp["changelog"] = {"type": "feed", "url": changelog_url}

    data["competitors"].append(new_comp)

    with open(settings.config_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)

    console.print(f"[bold green]✓ Competitor '{name}' successfully added to config/competitors.yaml![/bold green]\n")


def main():
    parser = argparse.ArgumentParser(
        description="Competitor Intelligence Agent — Monitor pricing, packaging, and product releases."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # track
    p_track = subparsers.add_parser("track", help="Scan competitor websites and changelogs for changes")
    p_track.set_defaults(func=cmd_track)

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Run strategic intelligence analysis on detected changes")
    p_analyze.set_defaults(func=cmd_analyze)

    # report
    p_report = subparsers.add_parser("report", help="Generate executive Markdown & HTML briefings")
    p_report.add_argument("--title", help="Custom briefing title", default=None)
    p_report.add_argument("--slack", action="store_true", help="Post briefing directly to configured Slack channel")
    p_report.set_defaults(func=cmd_report)

    # run-all
    p_all = subparsers.add_parser("run-all", help="Execute complete pipeline: track -> analyze -> report")
    p_all.add_argument("--slack", action="store_true", help="Post briefing directly to configured Slack channel")
    p_all.set_defaults(func=cmd_run_all)

    # test-slack
    p_test_slack = subparsers.add_parser("test-slack", help="Test Slack webhook connection")
    p_test_slack.set_defaults(func=cmd_test_slack)

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run continuously in background on schedule")
    p_daemon.add_argument("--interval-hours", type=float, default=24.0, help="Interval between runs in hours (default: 24)")
    p_daemon.add_argument("--slack", action="store_true", help="Post briefing directly to Slack channel")
    p_daemon.set_defaults(func=cmd_daemon)

    # add-competitor
    p_add = subparsers.add_parser("add-competitor", help="Register a new competitor")
    p_add.add_argument("--id", help="Competitor slug ID")
    p_add.add_argument("--name", help="Competitor display name")
    p_add.add_argument("--website", help="Competitor website URL")
    p_add.add_argument("--pricing-url", help="Competitor pricing URL")
    p_add.add_argument("--changelog-url", help="Competitor changelog RSS feed URL")
    p_add.set_defaults(func=cmd_add_competitor)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
