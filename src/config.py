from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "llm", "agentic"],
    "tech": ["tech", "software", "developer", "engineering", "startup", "python", "data science"],
    "fintech": ["fintech", "finance", "banking", "payments", "stablecoin", "crypto", "defi"],
    "quant": [
        "quant",
        "quantitative",
        "trading",
        "trader",
        "hedge fund",
        "market making",
        "hft",
        "high frequency",
        "derivatives",
        "alpha",
        "systematic",
        "research",
    ],
}


@dataclass(frozen=True)
class DigestConfig:
    cities: list[str] = field(default_factory=lambda: ["nyc"])
    pages: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=lambda: ["ai", "tech", "fintech", "quant"])
    custom_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    topic_keywords: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_TOPIC_KEYWORDS))
    max_results: int = 20
    fetch_per_source: int = 200

    @property
    def sources(self) -> list[str]:
        out: list[str] = []
        for slug in [*self.cities, *self.pages]:
            normalized = slug.strip().strip("/")
            if normalized and normalized not in out:
                out.append(normalized)
        return out

    @property
    def keywords_any(self) -> list[str]:
        keywords: list[str] = []
        for topic in self.topics:
            keywords.extend(self.topic_keywords.get(topic, []))
        keywords.extend(self.custom_keywords)
        return _dedupe(keywords)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            out.append(normalized)
            seen.add(key)
    return out


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _get(mapping: dict[str, Any], key: str, default: Any = None) -> Any:
    return mapping[key] if key in mapping else default


def load_config(path: Path) -> DigestConfig:
    raw = yaml.safe_load(path.read_text()) or {}

    luma = raw.get("luma") or {}
    filters = raw.get("filters") or {}
    digest = raw.get("digest") or {}

    # Backward compatibility with the first config.yaml shape.
    legacy_categories = raw.get("categories")
    legacy_keywords = raw.get("keywords_any")
    legacy_excludes = raw.get("exclude_keywords")

    topic_keywords = dict(DEFAULT_TOPIC_KEYWORDS)
    topic_keywords.update(raw.get("topic_keywords") or {})

    cities = _get(luma, "cities", legacy_categories if legacy_categories is not None else ["nyc"])
    topics = _get(filters, "topics", raw["topics"] if "topics" in raw else ["ai", "tech", "fintech", "quant"])
    custom_keywords = _get(filters, "custom_keywords", legacy_keywords if legacy_keywords is not None else [])
    exclude_keywords = _get(filters, "exclude_keywords", legacy_excludes if legacy_excludes is not None else [])

    return DigestConfig(
        cities=_list(cities),
        pages=_list(luma.get("pages")),
        topics=_list(topics),
        custom_keywords=_list(custom_keywords),
        exclude_keywords=_list(exclude_keywords),
        topic_keywords={key: _list(value) for key, value in topic_keywords.items()},
        max_results=int(digest.get("max_results", raw.get("max_results", 20))),
        fetch_per_source=int(digest.get("fetch_per_source", raw.get("fetch_per_category", 200))),
    )


def with_overrides(
    config: DigestConfig,
    *,
    cities: list[str] | None = None,
    pages: list[str] | None = None,
    topics: list[str] | None = None,
    keywords: list[str] | None = None,
    excludes: list[str] | None = None,
    max_results: int | None = None,
) -> DigestConfig:
    return DigestConfig(
        cities=_dedupe(cities) if cities is not None else config.cities,
        pages=_dedupe([*config.pages, *pages]) if pages else config.pages,
        topics=_dedupe(topics) if topics is not None else config.topics,
        custom_keywords=_dedupe([*config.custom_keywords, *keywords]) if keywords else config.custom_keywords,
        exclude_keywords=_dedupe([*config.exclude_keywords, *excludes]) if excludes else config.exclude_keywords,
        topic_keywords=config.topic_keywords,
        max_results=max_results if max_results is not None else config.max_results,
        fetch_per_source=config.fetch_per_source,
    )
