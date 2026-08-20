"""The one-command path: source -> analyse -> memo, chained.

This is what the brief's "done" bar actually asks for — "run one command,
point it at a topic, get memos out the other end." The seed input here is a
YC batch rather than a free-text topic (docs/decisions/0003: sourcing goes
deep on one structured feed rather than wide across many query-driven
sources), which the brief explicitly allows ("a feed like the YC W25 batch"
is one of its own examples of a valid seed input) — `--batch` is just the
honest name for what this pipeline's seed input actually is.

Each stage still runs and is testable standalone (`triage source`, `triage
analyse`, `triage memo`) — this module is a thin sequencing layer over them,
not a fourth place business logic lives.
"""

from __future__ import annotations

import logging
from pathlib import Path

from triage import analyse as analyse_stage
from triage import memo as memo_stage
from triage import source as source_stage

logger = logging.getLogger(__name__)


def run(
    batch: str = "Winter 2025",
    limit: int = 15,
    model: str = analyse_stage.DEFAULT_MODEL,
    max_attempts: int = 3,
    cache_dir: Path = source_stage.DEFAULT_CACHE_DIR,
    candidates_path: Path = source_stage.DEFAULT_OUT_PATH,
    analyses_dir: Path = analyse_stage.DEFAULT_ANALYSES_DIR,
    memos_dir: Path = memo_stage.DEFAULT_MEMOS_DIR,
) -> list[Path]:
    candidates = source_stage.run(
        batch=batch, limit=limit, cache_dir=cache_dir, out_path=candidates_path
    )
    logger.info("source: %d candidates", len(candidates))

    analyses = analyse_stage.run(
        candidates_path=candidates_path,
        out_dir=analyses_dir,
        model=model,
        max_attempts=max_attempts,
    )
    skipped = len(candidates) - len(analyses)
    logger.info("analyse: %d analyses (%d candidates skipped)", len(analyses), skipped)

    memos = memo_stage.run(
        candidates_path=candidates_path, analyses_dir=analyses_dir, out_dir=memos_dir
    )
    logger.info("memo: %d memos", len(memos))

    return memos
