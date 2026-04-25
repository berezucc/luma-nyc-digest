from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

API_URL = "https://api.lu.ma/discover/get-paginated-events"
EVENT_BASE = "https://lu.ma"
PAGE_BASE = "https://luma.com"
USER_AGENT = "luma-nyc-digest/1.0 (+https://github.com)"


@dataclass
class Event:
    api_id: str
    name: str
    url: str
    start_at: datetime
    location: str
    hosts: list[str] = field(default_factory=list)
    guest_count: int = 0
    is_free: bool = False
    is_sold_out: bool = False

    @classmethod
    def from_api(cls, entry: dict[str, Any]) -> "Event":
        e = entry.get("event") or {}
        slug = e.get("url") or ""

        start_raw = e.get("start_at")
        try:
            start = (
                datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                if start_raw
                else datetime.min.replace(tzinfo=timezone.utc)
            )
        except (ValueError, AttributeError):
            start = datetime.min.replace(tzinfo=timezone.utc)

        loc_info = e.get("geo_address_info") or {}
        location = (
            loc_info.get("city_state")
            or loc_info.get("address")
            or loc_info.get("city")
            or ("Online" if e.get("location_type") == "virtual" else "")
        )

        hosts = [h.get("name", "") for h in (entry.get("hosts") or []) if h.get("name")]

        ticket = e.get("ticket_info") or {}

        return cls(
            api_id=e.get("api_id", ""),
            name=e.get("name", "").strip(),
            url=f"{EVENT_BASE}/{slug}" if slug else "",
            start_at=start,
            location=location,
            hosts=hosts,
            guest_count=int(e.get("guest_count") or 0),
            is_free=bool(ticket.get("is_free")),
            is_sold_out=bool(ticket.get("is_sold_out")),
        )


def _extract_next_data(html: str) -> dict[str, Any]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def _page_data(client: httpx.Client, slug: str) -> tuple[str | None, list[Event]]:
    response = client.get(f"{PAGE_BASE}/{slug.strip('/')}", follow_redirects=True)
    response.raise_for_status()
    next_data = _extract_next_data(response.text)
    initial = (
        next_data.get("props", {})
        .get("pageProps", {})
        .get("initialData", {})
        .get("data", {})
    )
    place_api_id = (initial.get("place") or {}).get("api_id")
    entries = [*initial.get("featured_events", []), *initial.get("events", [])]
    return place_api_id, [Event.from_api(entry) for entry in entries]


def fetch_events(category_slug: str, limit: int = 200, period: str = "upcoming") -> list[Event]:
    """Fetch Luma discover events, resolving city pages to their current place id."""
    events: list[Event] = []
    seen: set[str] = set()
    cursor: str | None = None
    page_size = 50

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        try:
            place_api_id, page_events = _page_data(client, category_slug)
            for event in page_events:
                if event.api_id and event.api_id not in seen:
                    events.append(event)
                    seen.add(event.api_id)
        except httpx.HTTPError:
            place_api_id = None

        while len(events) < limit:
            params: dict[str, Any] = {
                "period": period,
                "pagination_limit": min(page_size, limit - len(events)),
            }
            if place_api_id:
                params["discover_place_api_id"] = place_api_id
            else:
                params["category_url_slug"] = category_slug
            if cursor:
                params["pagination_cursor"] = cursor

            r = client.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json()

            entries = data.get("entries") or []
            if not entries:
                break

            for entry in entries:
                event = Event.from_api(entry)
                if event.api_id and event.api_id not in seen:
                    events.append(event)
                    seen.add(event.api_id)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break

    return events
