"""triage.sources.yc — founder-page parsing and the relevance filter.

The relevance test runs against tests/fixtures/yc_batch_sample.json, a trimmed
but *unedited* slice of the real YC Winter 2025 batch (fetched 2026-08-17): six
companies that should match the thesis's two-bucket keyword filter and six that
shouldn't, picked by hand after eyeballing what the filter did against the full
167-company batch. See docs/decisions/0003-sourcing-is-a-loose-filter.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from triage.sources import yc

FIXTURES = Path(__file__).parent / "fixtures"

RELEVANT_NAMES = {"Egress Health", "Vetnio", "Toothy AI", "Cardamon", "Cifrato", "careCycle"}
IRRELEVANT_NAMES = {"Exin Therapeutics", "Enhanced Radar", "Red Barn Robotics", "Miyagi Labs"}


def _load_batch_sample() -> list[dict]:
    return json.loads((FIXTURES / "yc_batch_sample.json").read_text(encoding="utf-8"))


class TestBatchSlug:
    def test_matches_the_oss_apis_own_slug_convention(self) -> None:
        assert yc.batch_slug("Winter 2025") == "winter-2025"
        assert yc.batch_slug("Fall 2025") == "fall-2025"


class TestParseFounders:
    def test_extracts_name_and_bio_from_a_real_yc_page(self) -> None:
        page = (FIXTURES / "yc_company_page.html").read_text(encoding="utf-8")
        founders = yc.parse_founders(page)
        assert founders == ["Alex Pedersen — Co-founder of Egress. Prev Microsoft, Harvard CS"]

    def test_returns_empty_list_when_data_page_attribute_is_absent(self) -> None:
        assert yc.parse_founders("<html><body>no data-page here</body></html>") == []

    def test_returns_empty_list_on_malformed_json_rather_than_raising(self) -> None:
        html = '<div data-page="{not: valid json"></div>'
        assert yc.parse_founders(html) == []

    def test_returns_empty_list_when_founders_key_is_missing(self) -> None:
        html = '<div data-page="{&quot;props&quot;: {&quot;company&quot;: {}}}"></div>'
        assert yc.parse_founders(html) == []


class TestRelevanceScore:
    def test_zero_when_only_the_capability_bucket_matches(self) -> None:
        company = {"one_liner": "An AI agent for creative writing", "long_description": ""}
        assert yc.relevance_score(company) == 0

    def test_zero_when_only_the_workflow_bucket_matches(self) -> None:
        company = {"one_liner": "Software for invoice printing", "long_description": ""}
        assert yc.relevance_score(company) == 0

    def test_positive_when_both_buckets_match(self) -> None:
        company = {
            "one_liner": "AI agents that automate billing and compliance",
            "long_description": "",
        }
        assert yc.relevance_score(company) > 0


class TestRankCandidates:
    def test_keeps_known_relevant_companies_from_a_real_batch_slice(self) -> None:
        ranked_names = {c["name"] for c in yc.rank_candidates(_load_batch_sample(), limit=20)}
        assert ranked_names >= RELEVANT_NAMES

    def test_drops_known_irrelevant_companies_from_a_real_batch_slice(self) -> None:
        ranked_names = {c["name"] for c in yc.rank_candidates(_load_batch_sample(), limit=20)}
        assert ranked_names.isdisjoint(IRRELEVANT_NAMES)

    def test_respects_the_limit(self) -> None:
        ranked = yc.rank_candidates(_load_batch_sample(), limit=2)
        assert len(ranked) == 2

    def test_orders_by_score_descending(self) -> None:
        ranked = yc.rank_candidates(_load_batch_sample(), limit=20)
        scores = [yc.relevance_score(c) for c in ranked]
        assert scores == sorted(scores, reverse=True)
