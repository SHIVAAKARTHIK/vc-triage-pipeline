"""Smoke test: the CLI wiring resolves and the app is invokable.

Deliberately thin. Its job is to fail loudly if the package layout or the console
script entrypoint breaks, not to test behaviour that doesn't exist yet.
"""

from typer.testing import CliRunner

from triage import __version__
from triage.cli import app

runner = CliRunner()


def test_version_command_reports_package_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Source, analyse and write investment memos" in result.stdout


def test_source_command_invokes_the_source_stage(monkeypatch, tmp_path) -> None:
    """CLI wiring only: does `triage source` call source_stage.run with the flags
    it was given? The stage's own behaviour is covered in test_source_pipeline.py."""
    calls = {}

    def fake_run(batch, limit, cache_dir, out_path):
        calls["args"] = (batch, limit, cache_dir, out_path)
        return []

    monkeypatch.setattr("triage.cli.source_stage.run", fake_run)

    out = tmp_path / "candidates.json"
    result = runner.invoke(
        app, ["source", "--batch", "Fall 2025", "--limit", "5", "--out", str(out)]
    )

    assert result.exit_code == 0
    assert calls["args"][0] == "Fall 2025"
    assert calls["args"][1] == 5
    assert "wrote 0 candidates" in result.stdout


def test_analyse_command_invokes_the_analyse_stage(monkeypatch, tmp_path) -> None:
    """CLI wiring only: does `triage analyse` call analyse_stage.run with the
    flags it was given? The stage's own behaviour is covered in
    test_analyse_pipeline.py."""
    calls = {}

    def fake_run(candidates_path, out_dir, model, max_attempts):
        calls["args"] = (candidates_path, out_dir, model, max_attempts)
        return []

    monkeypatch.setattr("triage.cli.analyse_stage.run", fake_run)

    out_dir = tmp_path / "analyses"
    result = runner.invoke(
        app,
        ["analyse", "--model", "claude-opus-5", "--max-attempts", "2", "--out-dir", str(out_dir)],
    )

    assert result.exit_code == 0
    assert calls["args"][2] == "claude-opus-5"
    assert calls["args"][3] == 2
    assert "wrote 0 analyses" in result.stdout
