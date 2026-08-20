"""Command-line entrypoint. Stages land here as they're built."""

from pathlib import Path

import typer

from triage import __version__
from triage import analyse as analyse_stage
from triage import source as source_stage

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


@app.command()
def source(
    batch: str = typer.Option("Winter 2025", help='YC batch, e.g. "Winter 2025".'),
    limit: int = typer.Option(
        15, min=1, max=20, help="Candidates to keep after relevance ranking."
    ),
    cache_dir: Path = typer.Option(
        source_stage.DEFAULT_CACHE_DIR, help="Raw HTTP response cache."
    ),
    out: Path = typer.Option(
        source_stage.DEFAULT_OUT_PATH, help="Where to write the candidate list."
    ),
) -> None:
    """Source stage: rank a YC batch by thesis relevance, write data/candidates.json."""
    candidates = source_stage.run(batch=batch, limit=limit, cache_dir=cache_dir, out_path=out)
    typer.echo(f"wrote {len(candidates)} candidates to {out}")


@app.command()
def analyse(
    candidates: Path = typer.Option(
        analyse_stage.DEFAULT_CANDIDATES_PATH, help="Input candidates file."
    ),
    out_dir: Path = typer.Option(
        analyse_stage.DEFAULT_ANALYSES_DIR, help="Where to write analyses."
    ),
    model: str = typer.Option(analyse_stage.DEFAULT_MODEL, help="OpenAI model id."),
    max_attempts: int = typer.Option(
        3, min=1, max=5, help="Retries per candidate on invalid model output."
    ),
) -> None:
    """Analyse stage: score each candidate against docs/thesis.md via an LLM call.

    Reads OPENAI_API_KEY from the environment.
    """
    analyses = analyse_stage.run(
        candidates_path=candidates, out_dir=out_dir, model=model, max_attempts=max_attempts
    )
    typer.echo(f"wrote {len(analyses)} analyses to {out_dir}")


if __name__ == "__main__":
    app()
