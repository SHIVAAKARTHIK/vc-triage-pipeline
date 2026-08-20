# ADR 0004 — The call is computed from the score, never asked from the model; the prompt is generated from the thesis document, never duplicated

- **Date:** 2026-08-19
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code

## Context

Phase 3 (`src/triage/analyse.py`) is the first stage that calls an LLM. Two
questions came up building it that ADR 0002 had already answered once for
`total_score`, and answering them the same way turned out to matter more than
expected.

## Decision 1 — `call` is derived from the computed total, not asked for

The model is never asked to choose Pass / Watch / Take a meeting. `RawAnalysis`
(the tool schema the model must fill in) has no `call` field at all — only
`call_rationale`, which explains what drove the picture rather than asserting a
verdict. `analyse._build_analysis` computes `weighted_total(dimension_scores)`
first, using the exact same function `Analysis.total_score` uses internally
(extracted to `schemas.weighted_total` specifically so there's one formula, not
two that could drift), then calls `thesis.call_for_score(total)` to get the
call, and only then constructs the `Analysis`.

This is the same move ADR 0002 made for `total_score` — remove a class of bug
by construction rather than catching it in review — applied one level up. A
model asked to both rate five dimensions *and* separately assert "Watch" will
occasionally produce a call that doesn't match what its own ratings add up to;
that's not a hypothetical, it's the same failure mode `total_score` already
protects against, just at the categorical level instead of the numeric one.

## Decision 2 — The prompt is generated from `docs/thesis.md`, never duplicated

`triage.thesis.section(heading)` reads the slice / why-now / anti-portfolio
prose straight out of `docs/thesis.md` at prompt-render time — it is not
copied into `analyse.py`, `thesis.py`, or the prompt template by hand anywhere.
Only the *numbers* (dimension names, weights, call thresholds) live in
`thesis.py` as a small structured config, because those are what code needs to
compute with, and `tests/test_thesis_sync.py` parses the document's own
markdown tables and fails the suite if they drift from `thesis.py`.

Prose isn't given the same drift check — asserting exact-text parity would be
brittle for no real benefit — but it doesn't need one: there's only one copy of
it, in the document. Editing `docs/thesis.md`'s wording is the only edit needed
to change what the model actually sees.

## Decision 3 — Retries are stateless single-shot re-prompts, not a threaded tool_result conversation

When a response fails to parse, uses the wrong dimension names, or cites a
dangling evidence id, `analyse_candidate` re-sends the *entire* candidate
prompt again with a corrective sentence appended, rather than building a
proper multi-turn conversation with `tool_result` blocks referencing the
original `tool_use` call. Simpler code, and at 10-20 candidates with a handful
of retries at most, the extra tokens from re-sending full context each attempt
are not worth the conversation-state bookkeeping. Documented here mainly so a
reviewer doesn't read the retry loop and wonder if the state-threading was
missed by accident — it's a scope call, not an oversight.

## Consequences

- `call_rationale` is written by the model *without* knowing the categorical
  call it will end up attached to (that's computed after the fact from the
  same dimension scores). In practice these agree, because the rationale and
  the scores come from the same reasoning pass — but a rationale that reads
  as "mostly positive" next to a computed "Watch" is a real, known possibility,
  not fully engineered away. Worth a spot-check when reading real output.
- `DEFAULT_MODEL` is overridable per-run via `--model`; see ADR 0005 for which
  provider it targets and why that changed mid-build.
