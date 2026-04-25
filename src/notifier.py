from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .luma import Event

DISCORD_LIMIT = 1900  # leave headroom under the 2000-char hard cap


def _format_when(dt: datetime) -> str:
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return "TBD"
    # platform-portable formatting (no %-d / %-I)
    day = dt.strftime("%a %b ") + str(dt.day)
    hour12 = dt.hour % 12 or 12
    minute = dt.strftime("%M")
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{day}, {hour12}:{minute} {ampm}"


def format_event(e: Event) -> str:
    when = _format_when(e.start_at)
    bits = [when]
    if e.location:
        bits.append(e.location)
    if e.is_free:
        bits.append("Free")
    if e.is_sold_out:
        bits.append("Sold out")
    if e.guest_count:
        bits.append(f"{e.guest_count} going")
    meta = " · ".join(bits)
    hosts = f"\n_by {', '.join(e.hosts)}_" if e.hosts else ""
    title_line = f"**[{e.name}]({e.url})**" if e.url else f"**{e.name}**"
    return f"{title_line}\n{meta}{hosts}"


def chunk_message(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if cur_len + len(block) > limit and cur:
            chunks.append("".join(cur).rstrip())
            cur, cur_len = [block], len(block)
        else:
            cur.append(block)
            cur_len += len(block)
    if cur:
        chunks.append("".join(cur).rstrip())
    return chunks


def send_digest(webhook_url: str, events: list[Event], header: str | None = None) -> None:
    if not events:
        return
    title = header or f"NYC Luma digest — {len(events)} new event(s)"
    body = "\n\n".join([f"# {title}", *[format_event(e) for e in events]])
    chunks = chunk_message(body)
    with httpx.Client(timeout=30.0) as client:
        for c in chunks:
            r = client.post(
                webhook_url,
                json={"content": c, "allowed_mentions": {"parse": []}},
            )
            r.raise_for_status()
