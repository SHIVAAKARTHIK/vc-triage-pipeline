"""triage.pipeline.run — does the aggregate command actually call source,
analyse, then memo, in order, wiring each stage's output into the next?

Each stage's own behaviour is covered elsewhere (test_source_pipeline.py,
test_analyse_pipeline.py, test_memo_pipeline.py); this file is wiring only.
"""

from __future__ import annotations

from triage import pipeline


def test_calls_all_three_stages_in_order_with_matching_paths(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fake_source_run(batch, limit, cache_dir, out_path):
        calls.append("source")
        assert batch == "Winter 2025"
        return ["candidate-placeholder"]

    def fake_analyse_run(candidates_path, out_dir, model, max_attempts):
        calls.append("analyse")
        return ["analysis-placeholder"]

    def fake_memo_run(candidates_path, analyses_dir, out_dir):
        calls.append("memo")
        return [tmp_path / "memos" / "alpha.md"]

    monkeypatch.setattr("triage.pipeline.source_stage.run", fake_source_run)
    monkeypatch.setattr("triage.pipeline.analyse_stage.run", fake_analyse_run)
    monkeypatch.setattr("triage.pipeline.memo_stage.run", fake_memo_run)

    result = pipeline.run(batch="Winter 2025")

    assert calls == ["source", "analyse", "memo"]
    assert len(result) == 1
