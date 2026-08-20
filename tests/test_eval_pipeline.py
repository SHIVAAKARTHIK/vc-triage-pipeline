"""triage.eval.run — out/memos/*.md in, data/eval.json out."""

from __future__ import annotations

import json
import logging

from triage.eval import TOOL_NAME


def _valid_judgment(traceability: int = 4, clarity: int = 4) -> dict:
    return {
        "traceability_score": traceability,
        "traceability_notes": "Matches the cited source.",
        "clarity_score": clarity,
        "clarity_notes": "Call is clear early.",
    }


class TestRun:
    def test_writes_one_judgment_per_memo_and_returns_them(
        self, tmp_path, scripted_sender, tool_response
    ) -> None:
        from triage.eval import run

        memos_dir = tmp_path / "memos"
        memos_dir.mkdir()
        (memos_dir / "alpha.md").write_text("# Alpha — Take a meeting\n\nbody", encoding="utf-8")
        (memos_dir / "beta.md").write_text("# Beta — Pass\n\nbody", encoding="utf-8")

        judgment = _valid_judgment()
        both = [
            tool_response(judgment, tool_name=TOOL_NAME),
            tool_response(judgment, tool_name=TOOL_NAME),
        ]
        sender = scripted_sender(both)
        out_path = tmp_path / "eval.json"

        results = run(memos_dir=memos_dir, out_path=out_path, send_message=sender)

        assert {r.memo_slug for r in results} == {"alpha", "beta"}
        written = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(written) == 2
        assert {row["memo_slug"] for row in written} == {"alpha", "beta"}

    def test_skips_a_memo_that_never_produces_a_valid_judgment(
        self, tmp_path, caplog, scripted_sender, tool_response
    ) -> None:
        from triage.eval import run

        memos_dir = tmp_path / "memos"
        memos_dir.mkdir()
        (memos_dir / "alpha.md").write_text("# Alpha", encoding="utf-8")
        (memos_dir / "beta.md").write_text("# Beta", encoding="utf-8")

        # alpha: both attempts malformed; beta: valid on the first try
        sender = scripted_sender(
            [
                tool_response({"traceability_score": 4}, tool_name=TOOL_NAME),
                tool_response({"traceability_score": 4}, tool_name=TOOL_NAME),
                tool_response(_valid_judgment(), tool_name=TOOL_NAME),
            ]
        )

        with caplog.at_level(logging.WARNING):
            results = run(
                memos_dir=memos_dir,
                out_path=tmp_path / "eval.json",
                send_message=sender,
                max_attempts=2,
            )

        assert [r.memo_slug for r in results] == ["beta"]
        assert "skipping alpha" in caplog.text

    def test_zero_memos_produces_zero_judgments_without_error(
        self, tmp_path, scripted_sender
    ) -> None:
        from triage.eval import run

        memos_dir = tmp_path / "memos"
        memos_dir.mkdir()
        sender = scripted_sender([])

        results = run(memos_dir=memos_dir, out_path=tmp_path / "eval.json", send_message=sender)

        assert results == []
