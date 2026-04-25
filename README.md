# Luma Digest

A small, scheduled Discord digest for Luma events.

Luma Digest scans public Luma discovery pages, filters events by configurable cities and topics, dedupes events across runs with SQLite, and posts a clean weekly digest to Discord.

## Features

- City-based Luma discovery, such as `nyc`, `sf`, or `london`
- Topic filters for `ai`, `tech`, `fintech`, and `quant`
- Custom include and exclude keywords
- SQLite dedupe state in `seen.sqlite`
- Discord webhook delivery
- GitHub Actions weekly schedule with manual runs
- Local dry-run mode for tuning filters before sending

## Quick Start

```bash
git clone https://github.com/berezucc/luma-nyc-digest.git
cd luma-nyc-digest

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m src.main --dry-run
```

To send a real digest:

```bash
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." python -m src.main
```

## Configuration

Most users only need to edit `config.yaml`.

```yaml
luma:
  cities:
    - nyc

filters:
  topics:
    - ai
    - tech
    - fintech
    - quant
  custom_keywords:
    - robotics
  exclude_keywords:
    - yoga
    - dating

digest:
  max_results: 20
  fetch_per_source: 200
```

### Cities

Set `luma.cities` to Luma discovery slugs:

```yaml
luma:
  cities:
    - nyc
    - sf
```

These map to pages like `https://luma.com/nyc` and `https://luma.com/sf`.

### Topics

Set `filters.topics` to any topic defined under `topic_keywords`:

```yaml
filters:
  topics:
    - ai
    - fintech
```

To create a new topic, add it to `topic_keywords`:

```yaml
topic_keywords:
  climate:
    - climate
    - energy
    - carbon
```

Then enable it:

```yaml
filters:
  topics:
    - climate
```

### Custom Keywords

Use `custom_keywords` for one-off terms without creating a named topic:

```yaml
filters:
  custom_keywords:
    - market structure
    - reinforcement learning
```

Matching is case-insensitive and word-aware, so `defi` will not match inside `Pridefit`.

## CLI Overrides

You can test different filters locally without editing `config.yaml`:

```bash
python -m src.main --dry-run --city sf --topic ai --topic fintech
```

Add ad-hoc keywords:

```bash
python -m src.main --dry-run --keyword "market making" --keyword "agents"
```

List built-in topics:

```bash
python -m src.main --list-topics
```

Common options:

```text
--city <slug>          Replace configured cities
--topic <name>         Replace configured topics
--keyword <phrase>     Add a custom include keyword
--exclude <phrase>     Add a custom exclude keyword
--max-results <n>      Override digest size
--dry-run              Print without sending or updating seen.sqlite
```

## GitHub Actions

The included workflow runs every Monday at `14:00 UTC`.

To enable it in your own repo:

1. Create a Discord webhook for the target channel.
2. Add it as a GitHub Actions secret named `DISCORD_WEBHOOK_URL`.
3. Push the repo to GitHub.
4. Run **Weekly Luma Digest** once from the Actions tab.

The workflow commits `seen.sqlite` back to the repo so future runs do not resend the same events.

## Development

```bash
pytest
python -m src.main --dry-run
```

## License

MIT
