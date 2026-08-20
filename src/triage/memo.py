"""The memo stage: data/candidates.json + data/analyses/*.json in,
out/memos/<slug>.md out.

Pure rendering — no judgement calls happen here (Fig. 1, ADR 0001). Every
number and sentence in a memo already exists in its Analysis; this stage's
only job is arranging it so the call is readable in the first five lines and
the whole memo in the brief's own 60-second bar, and so a reader can trace any
claim back to its source without leaving the file — the "Sources" footer is
built from `check_evidence_integrity`'s own evidence set, not a fresh guess at
what was cited.

Templates live in `templates/`, not `prompts/`: `prompts/` is what an LLM
reads, `templates/` is what a person reads. Same tool (Jinja2), different
audience, kept in separate directories on purpose.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Environment

from triage.evidence import check_evidence_integrity
from triage.schemas import Analysis, Candidate, Evidence

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATES_PATH = Path("data/candidates.json")
DEFAULT_ANALYSES_DIR = Path("data/analyses")
DEFAULT_MEMOS_DIR = Path("out/memos")

CALL_LABELS = {"pass": "Pass", "watch": "Watch", "meet": "Take a meeting"}

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "memo.md"

# A model-written rationale landing inside a markdown table cell can contain a
# literal "|" and silently break the table's column alignment — a real
# formatting bug, not paranoia, since that text is never checked for markdown
# safety anywhere upstream. escape_pipe is the one place it's handled.
# trim_blocks/lstrip_blocks: without these, every {% for/if %} tag leaves its
# own newline in the output, which shows up as a blank line between every list
# item and — worse — between every row of the Scores table. A blank line
# inside a GFM table terminates it, so this isn't cosmetic: without this, the
# table silently stops rendering as a table on GitHub after its first row.
_env = Environment(trim_blocks=True, lstrip_blocks=True)
_env.filters["escape_pipe"] = lambda s: s.replace("|", "\\|").replace("\n", " ")
# Founder bios and evidence snippets are scraped/model text that can carry
# embedded newlines — inside a single "- {{ }}" bullet those break the item
# into a loose multi-paragraph block instead of one tight line.
_env.filters["oneline"] = lambda s: " ".join(s.split())


def cited_evidence(candidate: Candidate, analysis: Analysis) -> list[Evidence]:
    """Evidence actually cited in this analysis, in first-citation order,
    deduplicated — the memo's Sources section, so a reader can trace any claim
    without leaving the file."""
    by_id = {e.id: e for e in candidate.evidence}
    seen: set[str] = set()
    ordered: list[Evidence] = []
    for claim in (analysis.team, analysis.product, analysis.market, *analysis.risks):
        for eid in claim.evidence_ids:
            if eid not in seen:
                seen.add(eid)
                ordered.append(by_id[eid])
    return ordered


def render_memo(candidate: Candidate, analysis: Analysis) -> str:
    """Raises DanglingEvidenceError if `analysis` cites evidence `candidate`
    never collected — re-checked here, not just trusted from write time, so a
    hand-edited or corrupted data/analyses/*.json fails loudly instead of
    rendering a memo with a broken Sources section."""
    check_evidence_integrity(candidate, analysis)
    template = _env.from_string(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(
        candidate=candidate,
        analysis=analysis,
        call_label=CALL_LABELS[analysis.call],
        sources=cited_evidence(candidate, analysis),
    )


def run(
    candidates_path: Path = DEFAULT_CANDIDATES_PATH,
    analyses_dir: Path = DEFAULT_ANALYSES_DIR,
    out_dir: Path = DEFAULT_MEMOS_DIR,
) -> list[Path]:
    raw_candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = {c["slug"]: Candidate(**c) for c in raw_candidates}

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for analysis_path in sorted(analyses_dir.glob("*.json")):
        analysis = Analysis(**json.loads(analysis_path.read_text(encoding="utf-8")))
        candidate = candidates.get(analysis.candidate_slug)
        if candidate is None:
            logger.warning(
                "no candidate found for analysis %s -- skipping", analysis.candidate_slug
            )
            continue

        memo_text = render_memo(candidate, analysis)
        memo_path = out_dir / f"{candidate.slug}.md"
        memo_path.write_text(memo_text, encoding="utf-8")
        written.append(memo_path)

    logger.info("wrote %d memos to %s", len(written), out_dir)
    return written
