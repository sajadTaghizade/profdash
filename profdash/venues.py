"""Venue-tier matching shared by paper selection and scoring digests.

DBLP venue strings carry volume suffixes ("ECCV (12)", "CRYPTO (3)") and
vary in case; normalize both sides, then match exactly. Long tier entries
(journal names, >= 8 chars) also match as substrings so e.g.
"Proc. ACM Program. Lang." still hits a slightly longer DBLP string.
Short entries never substring-match: "sp" must not hit "ispass".
"""
from __future__ import annotations

import re

_VOLUME = re.compile(r"\s*\((\d+|[ivx]+)\)\s*$")
_MIN_SUBSTRING = 8


def normalize_venue(venue: str) -> str:
    v = (venue or "").strip().lower()
    v = _VOLUME.sub("", v)
    return re.sub(r"\s+", " ", v)


def _matches(v: str, entries: set[str]) -> bool:
    if v in entries:
        return True
    return any(len(e) >= _MIN_SUBSTRING and e in v for e in entries)


def venue_tier(venue: str, strong, moderate) -> str:
    """'strong' | 'moderate' | 'unknown'."""
    v = normalize_venue(venue)
    if not v:
        return "unknown"
    if _matches(v, {normalize_venue(s) for s in strong}):
        return "strong"
    if _matches(v, {normalize_venue(m) for m in moderate}):
        return "moderate"
    return "unknown"
