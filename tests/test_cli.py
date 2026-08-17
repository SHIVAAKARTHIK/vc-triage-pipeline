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
