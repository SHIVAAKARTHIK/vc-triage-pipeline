"""triage.thesis — the structured config, independent of docs/thesis.md's exact
prose (that cross-check lives in test_thesis_sync.py)."""

from __future__ import annotations

import pytest

from triage import thesis


def test_dimension_weights_sum_to_100() -> None:
    assert sum(d.weight for d in thesis.DIMENSIONS) == 100


def test_weight_for_a_known_dimension() -> None:
    assert thesis.weight_for("workflow_ownership") == 30


def test_weight_for_an_unknown_dimension_raises() -> None:
    with pytest.raises(KeyError):
        thesis.weight_for("not_a_real_dimension")


class TestCallForScore:
    def test_at_or_above_meet_threshold_is_meet(self) -> None:
        assert thesis.call_for_score(thesis.MEET_THRESHOLD) == "meet"
        assert thesis.call_for_score(100) == "meet"

    def test_between_watch_and_meet_is_watch(self) -> None:
        assert thesis.call_for_score(thesis.WATCH_THRESHOLD) == "watch"
        assert thesis.call_for_score(thesis.MEET_THRESHOLD - 1) == "watch"

    def test_below_watch_threshold_is_pass(self) -> None:
        assert thesis.call_for_score(thesis.WATCH_THRESHOLD - 1) == "pass"
        assert thesis.call_for_score(0) == "pass"


class TestThesisVersion:
    def test_is_stable_for_unchanged_content(self) -> None:
        assert thesis.thesis_version() == thesis.thesis_version()

    def test_has_the_expected_shape(self) -> None:
        version = thesis.thesis_version()
        assert version.startswith("thesis@")
        assert len(version) == len("thesis@") + 10


class TestSection:
    def test_extracts_a_known_section(self) -> None:
        text = thesis.section("The slice")
        assert text  # non-empty

    def test_raises_on_an_unknown_heading(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            thesis.section("Not A Real Heading")
