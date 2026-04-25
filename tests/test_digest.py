from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.config import load_config, with_overrides
from src.filters import matches
from src.luma import Event
from src.notifier import chunk_message, format_event
from src.storage import connect, load_seen, mark_seen, prune


def make_event(**overrides: object) -> Event:
    defaults = {
        "api_id": "evt_1",
        "name": "Quant ML Trading Meetup",
        "url": "https://lu.ma/test",
        "start_at": datetime(2026, 5, 4, 22, 30, tzinfo=timezone.utc),
        "location": "New York, NY",
        "hosts": ["Jane Host"],
        "guest_count": 42,
        "is_free": True,
        "is_sold_out": False,
    }
    defaults.update(overrides)
    return Event(**defaults)


def test_matches_keyword_and_excludes_noise() -> None:
    assert matches(make_event(), ["quant"], [])
    assert not matches(make_event(name="Yoga for traders"), ["trader"], ["yoga"])
    assert not matches(make_event(name="Pridefit NYC Workout", hosts=["Carli"]), ["defi"], [])
    assert matches(make_event(name="Anything"), [], [])


def test_sqlite_seen_round_trip_and_prune(tmp_path) -> None:
    conn = connect(tmp_path / "seen.sqlite")
    old = datetime.now(timezone.utc) - timedelta(days=100)

    mark_seen(conn, ["old"], old)
    mark_seen(conn, ["new"], datetime.now(timezone.utc))
    prune(conn, days=90)

    assert load_seen(conn) == {"new"}


def test_format_event_includes_core_fields() -> None:
    formatted = format_event(make_event())

    assert "**[Quant ML Trading Meetup](https://lu.ma/test)**" in formatted
    assert "New York, NY" in formatted
    assert "Free" in formatted
    assert "42 going" in formatted
    assert "_by Jane Host_" in formatted


def test_chunk_message_respects_limit() -> None:
    chunks = chunk_message("a\n\nb" * 100, limit=25)

    assert len(chunks) > 1
    assert all(len(chunk) <= 25 for chunk in chunks)


def test_config_loads_topics_and_cli_overrides(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
luma:
  cities: [nyc]
filters:
  topics: [ai]
  custom_keywords: [robotics]
  exclude_keywords: [yoga]
topic_keywords:
  ai: [ai, llm]
digest:
  max_results: 5
  fetch_per_source: 25
"""
    )

    config = load_config(path)
    overridden = with_overrides(config, cities=["sf"], topics=["ai"], keywords=["agents"])

    assert config.sources == ["nyc"]
    assert config.keywords_any == ["ai", "llm", "robotics"]
    assert config.max_results == 5
    assert config.fetch_per_source == 25
    assert overridden.sources == ["sf"]
    assert overridden.keywords_any == ["ai", "llm", "robotics", "agents"]


def test_empty_topics_are_respected(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
luma:
  cities: [nyc]
filters:
  topics: []
  custom_keywords: [robotics]
"""
    )

    config = load_config(path)

    assert config.topics == []
    assert config.keywords_any == ["robotics"]
