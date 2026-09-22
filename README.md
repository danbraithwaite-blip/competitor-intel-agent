# Competitor Intelligence Tracking Agent

An automated intelligence agent built to monitor competitor **pricing/packaging changes** and **product releases/changelogs**, analyze strategic intent using **Anthropic Claude** (or Google Gemini), and deliver executive briefings directly to a **Slack channel** and local HTML/Markdown dashboards.

---

## Features

- **💰 Pricing & Packaging Radar**:
  - Scrapes target `/pricing` pages with noise-reduction algorithms (strips dynamic footers, cookie banners, tracking scripts).
  - Maintains historical snapshots in SQLite and performs structural line-by-line diffing.
  - Detects price hikes, price drops, new tiers, feature gating (e.g. Pro -> Enterprise), and packaging limits.
- **🚀 Product Updates & Changelogs**:
  - Consumes RSS/Atom feeds and HTML changelog pages (e.g. `/changelog`, `/releases`).
  - Automatically deduplicates and extracts release titles, key capabilities, and publication dates.
- **🧠 Claude Strategic Intelligence Engine**:
  - Eliminates noise and categorizes strategic moves.
  - Classifies threat levels (`HIGH`, `MEDIUM`, `LOW`).
  - Evaluates strategic intent (why the competitor made this move).
  - Generates actionable counter-strategies for your product, sales, and marketing teams.
  - Includes offline heuristic fallback if an API key is not yet configured.
- **📢 Slack Briefing Publisher**:
  - Formats briefings into sleek Slack Block Kit messages with emoji badges, threat counters, and executive takeaways.
- **📊 Executive Reports**:
  - Standalone dark-mode HTML reports with key metric cards and categorized event timelines.
  - Terminal dashboards powered by `rich`.

---

## Quickstart

### 1. Setup & Environment
The project is set up with a Python virtual environment:
```bash
cd /Users/danielbraithwaite/Documents/competitor-intel-agent
source .venv/bin/activate
```

### 2. Configure Credentials (.env)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your keys:
```env
# Anthropic Claude API Key (https://console.anthropic.com/)
ANTHROPIC_API_KEY=sk-ant-your_claude_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Optional: Google Gemini API Key
# GEMINI_API_KEY=your_gemini_api_key

# Slack Incoming Webhook (Slack App -> Incoming Webhooks)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../X...
```

### 3. Verify Slack Connection
```bash
python main.py test-slack
```

---

## Usage Commands

### 🔍 1. Track Competitors
Scans all configured competitors for pricing changes and new changelog updates:
```bash
python main.py track
```

### 🧠 2. Analyze Detected Events
Runs the Gemini Intelligence Engine to analyze changes, detect strategic threats, and formulate counter-moves:
```bash
python main.py analyze
```

### 📊 3. Generate Executive Briefing
Generates local Markdown & HTML briefings:
```bash
# Generate report and view terminal summary
python main.py report

# Generate report AND dispatch directly to your Slack channel
python main.py report --slack
```

### ⚡ 4. One-Click Pipeline
Runs track -> analyze -> report in one go:
```bash
python main.py run-all --slack
```

### ➕ 5. Add a New Competitor
Interactively or via flags:
```bash
python main.py add-competitor --id vercel --name Vercel --website https://vercel.com --pricing-url https://vercel.com/pricing --changelog-url https://vercel.com/changelog/rss.xml
```

---

## Configuring Competitors (`config/competitors.yaml`)

Edit `config/competitors.yaml` to add any competitor you want to monitor:

```yaml
competitors:
  - id: "linear"
    name: "Linear"
    website: "https://linear.app"
    pricing:
      url: "https://linear.app/pricing"
      selector: "main" # optional CSS selector to isolate pricing
    changelog:
      type: "web_page"
      url: "https://linear.app/changelog"

  - id: "supabase"
    name: "Supabase"
    website: "https://supabase.com"
    pricing:
      url: "https://supabase.com/pricing"
      selector: "main"
    changelog:
      type: "feed"
      url: "https://supabase.com/rss.xml"
```

---

## Automating Periodic Briefings (Cron)

To receive automated daily briefings in Slack, add a cron schedule:
```bash
crontab -e
```
Add an entry (e.g., daily at 9:00 AM):
```cron
0 9 * * 1-5 cd /Users/danielbraithwaite/Documents/competitor-intel-agent && .venv/bin/python main.py run-all --slack >> reports/cron.log 2>&1
```

---

## Running Automated Tests
```bash
.venv/bin/pytest -v
```
All 7 unit tests cover HTML noise-cleaning, diff calculation, snapshot persistence, Gemini offline fallbacks, and Slack Block Kit generation.
