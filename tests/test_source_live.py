"""One real run against the actual network — not part of the default suite.

Run explicitly with `uv run pytest -m live`. Everything else in tests/ is offline
by design (see pyproject.toml's default `-m "not live"`); this file exists so
there's still an honest, automated check that the fixtures above haven't drifted
from what YC/HN actually return.
"""

from __future__ import annotations

import pytest

from triage import source

pytestmark = pytest.mark.live


def test_a_real_batch_produces_at_least_one_valid_candidate(tmp_path) -> None:
    candidates = source.run(
        batch="Winter 2025",
        limit=5,
        cache_dir=tmp_path / "raw",
        out_path=tmp_path / "candidates.json",
    )
    assert len(candidates) >= 1
    for c in candidates:
        assert c.evidence  # schema already guarantees this, but assert the intent
        assert c.one_liner
