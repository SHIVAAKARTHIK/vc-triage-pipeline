"""slugify and evidence_id — small but load-bearing: they're the join keys and the
dedup key the rest of the pipeline trusts."""

from __future__ import annotations

import pytest

from triage.util import evidence_id, slugify


class TestSlugify:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Ledgerly", "ledgerly"),
            ("Ledgerly, Inc.", "ledgerly-inc"),
            ("  Spaced   Out  ", "spaced-out"),
            ("C3.ai", "c3-ai"),
        ],
    )
    def test_produces_url_safe_slugs(self, name: str, expected: str) -> None:
        assert slugify(name) == expected

    def test_rejects_a_name_with_no_alphanumerics(self) -> None:
        with pytest.raises(ValueError, match="cannot derive a slug"):
            slugify("!!!")


class TestEvidenceId:
    def test_matches_the_expected_format(self) -> None:
        eid = evidence_id("https://news.ycombinator.com/item?id=1")
        assert eid.startswith("ev_")
        assert len(eid) == len("ev_") + 8

    def test_is_stable_for_the_same_url(self) -> None:
        url = "https://ycombinator.com/companies/ledgerly"
        assert evidence_id(url) == evidence_id(url)

    def test_differs_for_different_urls(self) -> None:
        a = evidence_id("https://example.com/a")
        b = evidence_id("https://example.com/b")
        assert a != b
