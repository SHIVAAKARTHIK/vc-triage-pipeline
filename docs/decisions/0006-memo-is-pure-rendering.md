# ADR 0006 — The memo stage makes no judgement calls; templates/ is not prompts/

- **Date:** 2026-08-21
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code

## Context

Phase 4 turns each `data/analyses/<slug>.json` into `out/memos/<slug>.md` — the
brief's "Recommendation" stage made visible. Two design questions came up, and
a real formatting bug turned up only once real committed data was rendered
through it, not from the offline test suite alone.

## Decision 1 — memo.py is pure rendering; no new judgement happens here

Every fact in a rendered memo already exists on its `Analysis` — the call, the
score, the rationale, the risks. `render_memo` doesn't call an LLM, doesn't
re-score anything, and doesn't decide what to include based on the content
(no "only show risks if severe" branching). Its only real logic is:

- `CALL_LABELS` — mapping the internal literal (`"meet"`) to the brief's own
  words ("Take a meeting"), a display concern, not a judgement one.
- `cited_evidence` — resolving the *union of evidence ids actually cited*
  across team/product/market/risks into an ordered, deduplicated `Sources`
  footer, so a reader can trace any claim without leaving the file. This
  reuses `check_evidence_integrity` from Phase 1/3 rather than re-implementing
  a trust check — the same guarantee holds at read time, not just write time.

This keeps the traceability property from ADR 0002 intact all the way to the
document a partner actually reads: the Sources footer isn't a dump of
everything the candidate ever collected, it's exactly what this specific
memo's claims depend on.

## Decision 2 — `templates/` is a separate directory from `prompts/`

Both use Jinja2. `prompts/` is read by an LLM (`analyse.py`); `templates/` is
read by a person (`memo.py`). Same mechanism, different audience — kept in
separate directories so the distinction is visible in the repo layout, not
just in a comment. `README.md`'s reading map documents both.

## Decision 3 — `Environment(trim_blocks=True, lstrip_blocks=True)`, found by actually rendering real data

The offline test suite (all synthetic fixtures) never caught this. Rendering
the 15 real committed analyses did: Jinja's default `{% for %}`/`{% endfor %}`
tags each leave their own newline in the output, which showed up as a blank
line between every row of the Scores table. A blank line inside a GFM table
terminates it — this wasn't cosmetic, the table would have silently stopped
rendering as a table after its first row on GitHub. Fixed by constructing the
`Environment` with `trim_blocks=True, lstrip_blocks=True` (memo.py), with a
regression test (`test_scores_table_has_no_blank_lines_between_rows`) that
asserts the table's rows are contiguous in the rendered output.

The same real-data pass surfaced a second, related issue: founder bios and
evidence snippets are scraped/model text that can carry embedded newlines,
which broke a single `- {{ f }}` bullet into a loose multi-paragraph block.
Fixed with a small `oneline` filter (`" ".join(s.split())`) applied to every
field rendered inside a single-line bullet.

## Consequences

- Both fixes exist *because* the pipeline was run against real data before
  being called done, not just tested against synthetic fixtures — worth
  remembering as a general lesson for any future stage: the offline suite
  proves the logic; a real run proves the formatting.
- `escape_pipe` (ADR-adjacent, added alongside `oneline`) and `oneline` are
  the only two Jinja filters this project defines, both narrowly scoped to
  the one real markdown-breaking failure mode each guards against.
