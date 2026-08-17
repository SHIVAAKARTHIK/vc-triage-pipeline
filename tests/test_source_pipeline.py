"""triage.source — turning raw YC records into evidenced Candidates end to end.

Everything routes through httpx.MockTransport keyed by URL, so these tests never
touch the network but exercise the real Cache, the real yc/hn clients, and the
real Candidate/Evidence validators together — the same path a live run takes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from triage.cache import Cache
from triage.source import build_candidate, run
from triage.sources import yc

FIXTURES = Path(__file__).parent / "fixtures"
YC_PAGE = (FIXTURES / "yc_company_page.html").read_text(encoding="utf-8")
HN_NO_MATCH = (FIXTURES / "hn_no_match.json").read_text(encoding="utf-8")
HN_MATCH = (FIXTURES / "hn_match.json").read_text(encoding="utf-8")

HOMEPAGE_HTML = (
    '<html><head><meta name="description" content="AI agent that chases invoices '
    'so SMB finance teams don\'t have to."></head><body>Ledgerly</body></html>'
)

EGRESS_RAW = {
    "name": "Egress Health",
    "website": "https://tryegress.com",
    "url": "https://www.ycombinator.com/companies/egress-health",
    "one_liner": "Automated revenue cycle management, starting with dentists",
    "long_description": "Egress Health builds AI agents to automate revenue cycle management.",
}


def _routed_cache(tmp_path, routes: dict[str, tuple[int, str]]) -> Cache:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for prefix, (status, body) in routes.items():
            if url.startswith(prefix):
                return httpx.Response(status, text=body)
        return httpx.Response(404, text="not routed in test")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Cache(tmp_path, client=client)


class TestBuildCandidate:
    def test_full_evidence_trail_when_everything_resolves(self, tmp_path) -> None:
        cache = _routed_cache(
            tmp_path,
            {
                EGRESS_RAW["url"]: (200, YC_PAGE),
                "https://hn.algolia.com": (200, HN_NO_MATCH),
                EGRESS_RAW["website"]: (200, HOMEPAGE_HTML),
            },
        )

        candidate = build_candidate(cache, EGRESS_RAW, batch="Winter 2025")

        assert candidate.slug == "egress-health"
        assert candidate.founders == [
            "Alex Pedersen — Co-founder of Egress. Prev Microsoft, Harvard CS"
        ]
        assert candidate.traction.kind == "yc_batch"  # no HN coverage -> falls back
        assert {e.source for e in candidate.evidence} == {"yc", "homepage"}

    def test_falls_back_to_yc_batch_traction_when_hn_has_no_match(self, tmp_path) -> None:
        cache = _routed_cache(
            tmp_path,
            {
                EGRESS_RAW["url"]: (200, YC_PAGE),
                "https://hn.algolia.com": (200, HN_NO_MATCH),
                EGRESS_RAW["website"]: (200, "<html></html>"),
            },
        )
        candidate = build_candidate(cache, EGRESS_RAW, batch="Winter 2025")
        assert candidate.traction.detail == "Winter 2025 admission"

    def test_uses_hn_traction_when_a_real_match_is_found(self, tmp_path) -> None:
        vetnio_raw = {**EGRESS_RAW, "name": "Vetnio", "website": "https://vetnio.com",
                       "url": "https://www.ycombinator.com/companies/vetnio"}
        cache = _routed_cache(
            tmp_path,
            {
                vetnio_raw["url"]: (200, "<html>no data-page here</html>"),
                "https://hn.algolia.com": (200, HN_MATCH),
                vetnio_raw["website"]: (200, "<html></html>"),
            },
        )
        candidate = build_candidate(cache, vetnio_raw, batch="Winter 2025")
        assert candidate.traction.kind == "hn_post"
        assert "87 pts" in candidate.traction.detail
        assert candidate.founders == []  # this page has no data-page blob

    def test_still_builds_a_valid_candidate_when_homepage_and_yc_page_both_fail(
        self, tmp_path
    ) -> None:
        """Robustness: a dead homepage and a reshaped/missing YC page shouldn't
        stop the candidate from being built — the YC listing evidence alone
        satisfies Candidate's min_length=1 evidence requirement."""
        cache = _routed_cache(
            tmp_path,
            {
                EGRESS_RAW["url"]: (404, "gone"),
                "https://hn.algolia.com": (200, HN_NO_MATCH),
                EGRESS_RAW["website"]: (500, "server error"),
            },
        )
        candidate = build_candidate(cache, EGRESS_RAW, batch="Winter 2025")
        assert len(candidate.evidence) == 1
        assert candidate.evidence[0].source == "yc"
        assert candidate.founders == []

    def test_still_builds_a_valid_candidate_when_the_yc_page_is_unreachable(self, tmp_path) -> None:
        """A transport-level failure (not just a 404) on the founder-page fetch
        must degrade the same way: no founders, no crash."""

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == EGRESS_RAW["url"]:
                raise httpx.ConnectError("connection refused", request=request)
            if url.startswith("https://hn.algolia.com"):
                return httpx.Response(200, text=HN_NO_MATCH)
            if url == EGRESS_RAW["website"]:
                return httpx.Response(200, text=HOMEPAGE_HTML)
            return httpx.Response(404, text="not routed")

        cache = Cache(tmp_path, client=httpx.Client(transport=httpx.MockTransport(handler)))
        candidate = build_candidate(cache, EGRESS_RAW, batch="Winter 2025")

        assert candidate.founders == []
        assert {e.source for e in candidate.evidence} == {"yc", "homepage"}

    def test_still_builds_a_valid_candidate_when_hn_lookup_is_unreachable(self, tmp_path) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == EGRESS_RAW["url"]:
                return httpx.Response(200, text=YC_PAGE)
            if url.startswith("https://hn.algolia.com"):
                raise httpx.ConnectError("connection refused", request=request)
            if url == EGRESS_RAW["website"]:
                return httpx.Response(200, text=HOMEPAGE_HTML)
            return httpx.Response(404, text="not routed")

        cache = Cache(tmp_path, client=httpx.Client(transport=httpx.MockTransport(handler)))
        candidate = build_candidate(cache, EGRESS_RAW, batch="Winter 2025")

        # falls back to yc_batch exactly as it would for a confirmed no-match
        assert candidate.traction.kind == "yc_batch"


def _patch_cache_transport(monkeypatch, handler) -> None:
    """run() builds its own Cache internally; monkeypatch the Cache symbol it
    calls so `with Cache(cache_dir) as cache` picks up our mocked transport."""
    import triage.source as source_module

    original_cache_cls = source_module.Cache

    def cache_factory(root, client=None, user_agent=None):
        return original_cache_cls(root, client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(source_module, "Cache", cache_factory)


class TestRun:
    def test_writes_candidates_json_and_returns_them(self, tmp_path, monkeypatch) -> None:
        batch_url = yc.BATCH_API.format(slug="winter-2025")

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == batch_url:
                return httpx.Response(200, json=[EGRESS_RAW])
            if url == EGRESS_RAW["url"]:
                return httpx.Response(200, text=YC_PAGE)
            if url.startswith("https://hn.algolia.com"):
                return httpx.Response(200, text=HN_NO_MATCH)
            if url == EGRESS_RAW["website"]:
                return httpx.Response(200, text=HOMEPAGE_HTML)
            return httpx.Response(404, text="not routed")

        _patch_cache_transport(monkeypatch, handler)
        out_path = tmp_path / "candidates.json"
        candidates = run(
            batch="Winter 2025", limit=5, cache_dir=tmp_path / "raw", out_path=out_path
        )

        assert len(candidates) == 1
        assert candidates[0].slug == "egress-health"
        assert out_path.exists()
        written = json.loads(out_path.read_text(encoding="utf-8"))
        assert written[0]["slug"] == "egress-health"

    def test_dedupes_candidates_that_slugify_to_the_same_value(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        dupe_a = {**EGRESS_RAW, "name": "Vetnio"}
        dupe_b = {**EGRESS_RAW, "name": "Vetnio!", "one_liner": dupe_a["one_liner"]}
        batch_url = yc.BATCH_API.format(slug="winter-2025")

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == batch_url:
                return httpx.Response(200, json=[dupe_a, dupe_b])
            if url == EGRESS_RAW["url"]:
                return httpx.Response(200, text=YC_PAGE)
            if url.startswith("https://hn.algolia.com"):
                return httpx.Response(200, text=HN_NO_MATCH)
            if url == EGRESS_RAW["website"]:
                return httpx.Response(200, text=HOMEPAGE_HTML)
            return httpx.Response(404, text="not routed")

        _patch_cache_transport(monkeypatch, handler)
        with caplog.at_level(logging.WARNING):
            candidates = run(
                batch="Winter 2025", limit=5, cache_dir=tmp_path / "raw",
                out_path=tmp_path / "out.json",
            )

        assert len(candidates) == 1
        assert "collides" in caplog.text
