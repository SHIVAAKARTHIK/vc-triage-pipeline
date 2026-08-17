"""Command-line entrypoint.

Stages land here as they're built (Phase 2 onwards). For now this exists so the
`triage` console script resolves and the smoke test has something to assert on.
"""

import typer

from triage import __version__

app = typer.Typer(
    help="Source, analyse and write investment memos on seed-stage startups.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Keep `triage` a command group even while only one command exists.

    Without this, Typer collapses a single-command app into the root and
    `triage version` becomes an unexpected-argument error.
    """


@app.command()
def version() -> None:
    """Print the pipeline version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
