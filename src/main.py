from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, with_overrides
from .filters import matches
from .luma import fetch_events
from .notifier import format_event, send_digest
from .storage import connect, load_seen, mark_seen, prune


def _truthy(val: str | None) -> bool:
    return (val or "").lower() in ("1", "true", "yes", "y")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a filtered Luma events digest to Discord.")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--dry-run", action="store_true", help="Print the digest without sending or updating state.")
    parser.add_argument("--city", action="append", help="Luma city slug to scan, such as nyc, sf, london.")
    parser.add_argument("--page", action="append", help="Additional Luma page slug to scan, such as nyc/tech.")
    parser.add_argument("--topic", action="append", help="Topic from config topic_keywords. Replaces configured topics.")
    parser.add_argument("--keyword", action="append", help="Additional custom keyword or phrase.")
    parser.add_argument("--exclude", action="append", help="Additional keyword or phrase to exclude.")
    parser.add_argument("--max-results", type=int, help="Maximum number of events to send.")
    parser.add_argument("--list-topics", action="store_true", help="Print built-in topics and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path

    config = load_config(config_path)

    if args.list_topics:
        for topic in sorted(config.topic_keywords):
            print(topic)
        return 0

    config = with_overrides(
        config,
        cities=args.city,
        pages=args.page,
        topics=args.topic,
        keywords=args.keyword,
        excludes=args.exclude,
        max_results=args.max_results,
    )
    seen_path = root / "seen.sqlite"

    dry_run = args.dry_run or _truthy(os.environ.get("DRY_RUN"))
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook and not dry_run:
        print("ERROR: DISCORD_WEBHOOK_URL not set (use DRY_RUN=1 for local testing)", file=sys.stderr)
        return 1

    db_path = ":memory:" if dry_run else seen_path
    conn = connect(db_path)
    prune(conn)
    seen = load_seen(conn)

    by_id: dict[str, "object"] = {}
    for source in config.sources:
        try:
            evs = fetch_events(source, limit=config.fetch_per_source)
        except Exception as ex:
            print(f"WARN: fetch failed for source={source}: {ex}", file=sys.stderr)
            continue
        for e in evs:
            if e.api_id and e.api_id not in by_id:
                by_id[e.api_id] = e

    filtered = [e for e in by_id.values() if matches(e, config.keywords_any, config.exclude_keywords)]

    new = [e for e in filtered if e.api_id not in seen]
    new.sort(key=lambda e: e.start_at)

    to_send = new[: config.max_results]

    print(
        f"fetched={len(by_id)} matched={len(filtered)} new={len(new)} sending={len(to_send)} "
        f"sources={','.join(config.sources)} topics={','.join(config.topics) or 'custom'} dry_run={dry_run}"
    )

    if to_send:
        if dry_run:
            for e in to_send:
                print("---")
                print(format_event(e))
        else:
            send_digest(webhook, to_send)

    if to_send and not dry_run:
        mark_seen(conn, [e.api_id for e in to_send], datetime.now(timezone.utc))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
