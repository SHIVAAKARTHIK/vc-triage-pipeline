"""Hacker News traction lookup via the free, keyless Algolia search API.

Empirically (docs/worklog.md, 2026-08-17): most YC Winter 2025 companies have
never been mentioned on HN at all — a domain-restricted search came back with
zero hits for the large majority tried during development. That's the normal
shape of the data for very early startups, not a broken query, so
`find_traction` returning `None` is an expected, common result every caller has
to handle gracefully (see `source.build_candidate`'s fallback to a `yc_batch`
traction signal) — not something to retry or treat as an error.

Matching is deliberately conservative: Algolia's free-text relevance can surface
stories that merely *mention* a company name without being about it, so this
searches by domain (`restrictSearchableAttributes=url`) and then double-checks
the returned hit's own URL actually contains that domain before trusting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode, urlsplit

ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"


class JsonFetcher(Protocol):
    """The one method find_traction needs — satisfied by triage.cache.Cache,
    and easy to fake in tests without spinning up a real Cache."""

    def get_json(self, url: str) -> dict: ...


@dataclass
class HNHit:
    title: str
    points: int
    num_comments: int
    story_id: str
    story_url: str
    external_url: str | None


def _domain(url: str) -> str:
    netloc = urlsplit(url).netloc or urlsplit(f"//{url}").netloc
    return netloc.removeprefix("www.").lower()


def find_traction(cache: JsonFetcher, website: str) -> HNHit | None:
    domain = _domain(website)
    if not domain:
        return None

    query = urlencode({"query": domain, "restrictSearchableAttributes": "url", "tags": "story"})
    data = cache.get_json(f"{ALGOLIA_SEARCH}?{query}")
    hits = data.get("hits") or []

    matching = [h for h in hits if domain in (h.get("url") or "").lower()]
    if not matching:
        return None

    best = max(matching, key=lambda h: h.get("points") or 0)
    story_id = str(best.get("objectID", ""))
    return HNHit(
        title=best.get("title") or "(untitled)",
        points=best.get("points") or 0,
        num_comments=best.get("num_comments") or 0,
        story_id=story_id,
        story_url=f"https://news.ycombinator.com/item?id={story_id}",
        external_url=best.get("url"),
    )
