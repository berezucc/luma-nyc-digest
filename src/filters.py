from __future__ import annotations

import re

from .luma import Event


def _contains_term(text: str, term: str) -> bool:
    term = term.strip().lower()
    if not term:
        return False
    pattern = r"(?<![a-z0-9])" + r"\s+".join(re.escape(part) for part in term.split()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def matches(event: Event, keywords_any: list[str], exclude_keywords: list[str]) -> bool:
    haystack = " ".join([event.name, " ".join(event.hosts)]).lower()

    if exclude_keywords and any(_contains_term(haystack, k) for k in exclude_keywords):
        return False
    if not keywords_any:
        return True
    return any(_contains_term(haystack, k) for k in keywords_any)
