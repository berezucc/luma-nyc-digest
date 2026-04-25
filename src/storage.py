from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PRUNE_DAYS = 90


def connect(path: Path | str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_events (
            api_id TEXT PRIMARY KEY,
            seen_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def load_seen(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT api_id FROM seen_events").fetchall()
    return {row[0] for row in rows}


def mark_seen(conn: sqlite3.Connection, api_ids: list[str], seen_at: datetime | None = None) -> None:
    if not api_ids:
        return
    ts = (seen_at or datetime.now(timezone.utc)).isoformat()
    conn.executemany(
        "INSERT OR REPLACE INTO seen_events (api_id, seen_at) VALUES (?, ?)",
        [(api_id, ts) for api_id in api_ids],
    )
    conn.commit()


def prune(conn: sqlite3.Connection, days: int = PRUNE_DAYS) -> None:
    cutoff = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() - days * 86400,
        timezone.utc,
    ).isoformat()
    conn.execute("DELETE FROM seen_events WHERE seen_at < ?", (cutoff,))
    conn.commit()
