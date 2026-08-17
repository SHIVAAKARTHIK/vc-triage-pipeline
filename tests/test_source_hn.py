"""triage.sources.hn — traction lookup and its false-positive guard.

hn_no_match.json is an unedited capture of the real Algolia response for
"tryegress.com" (2026-08-17) — zero hits, which is the common case for very
early startups (see docs/worklog.md). hn_match.json is hand-built in the same
shape to exercise the match path deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path

from triage.sources import hn

FIXTURES = Path(__file__).parent / "fixtures"


class FakeCache:
    """Satisfies hn.JsonFetcher without touching the network or the real Cache."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requested_urls: list[str] = []

    def get_json(self, url: str) -> dict:
        self.requested_urls.append(url)
        return self.payload


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_returns_none_on_a_real_zero_hit_response() -> None:
    cache = FakeCache(_load("hn_no_match.json"))
    assert hn.find_traction(cache, "https://tryegress.com") is None


def test_returns_a_hit_when_the_domain_actually_matches() -> None:
    cache = FakeCache(_load("hn_match.json"))
    result = hn.find_traction(cache, "https://vetnio.com")

    assert result is not None
    assert result.points == 87
    assert result.num_comments == 24
    assert result.story_url == "https://news.ycombinator.com/item?id=43112233"


def test_queries_by_bare_domain_without_www_or_scheme() -> None:
    cache = FakeCache(_load("hn_match.json"))
    hn.find_traction(cache, "https://www.vetnio.com/pricing")
    assert "vetnio.com" in cache.requested_urls[0]
    assert "www." not in cache.requested_urls[0]


def test_rejects_a_hit_whose_own_url_does_not_contain_the_domain() -> None:
    """Algolia's relevance search can surface a story that merely mentions the
    company; this is the guard that stops that becoming a false traction claim."""
    noisy = {
        "hits": [
            {
                "objectID": "1",
                "title": "Some unrelated story that happens to mention vetnio in passing",
                "url": "https://totally-unrelated-domain.com/post",
                "points": 500,
                "num_comments": 200,
            }
        ]
    }
    cache = FakeCache(noisy)
    assert hn.find_traction(cache, "https://vetnio.com") is None


def test_picks_the_highest_points_hit_when_several_match() -> None:
    multi = {
        "hits": [
            {
                "objectID": "1", "title": "low", "url": "https://vetnio.com/a",
                "points": 5, "num_comments": 1,
            },
            {
                "objectID": "2", "title": "high", "url": "https://vetnio.com/b",
                "points": 200, "num_comments": 50,
            },
        ]
    }
    cache = FakeCache(multi)
    result = hn.find_traction(cache, "https://vetnio.com")
    assert result is not None
    assert result.title == "high"
