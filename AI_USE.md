# How AI was used to build this

The brief says to use AI freely and be honest about it, and that hiding it — not using
it — is what gets penalised. So this file is a straight accounting, kept current as the
repo grows rather than assembled at the end.

## Tooling

- **Claude Code (Opus 5)** — used as a pair-programmer throughout: planning, scaffolding,
  writing modules and tests, and reviewing my own changes.
- **OpenAI API** — the analysis stage of the pipeline itself calls OpenAI's chat
  completions/function-calling API (originally built against Anthropic's API — switched
  mid-build, see ADR 0005, because that's the key that was actually available to run it
  against). That's product, not process; see `prompts/` for the prompts and `docs/` for
  why they look the way they do.

## Per-module accounting

Updated as each phase lands. "Authored by" describes who produced the first draft;
everything in this repo was read and revised by me before commit.

| Module / artefact | Authored by | Notes |
| --- | --- | --- |
| `pyproject.toml`, repo scaffold | Claude Code | Standard `uv init` plus config I reviewed. |
| `docs/decisions/0001-*.md` | Claude Code, from decisions we made jointly | Facts and rationale are ours; prose is drafted. |
| `docs/thesis.md` | Claude Code, first draft — **pending Karthik's review** | Grounded in the 15 real sourced candidates and the kickoff direction, not written from scratch. Flagged in the file itself: not yet argued with or internalized. The scores mean nothing if the thesis isn't actually mine by the time this is submitted — this row needs to change before it is. |
| `docs/worklog.md` | Karthik | Same reason. |
| `src/triage/schemas.py`, `evidence.py`, `util.py` | Claude Code, design co-decided | The evidence-traceability model (ADR 0002, computed `total_score`) was a joint call, drafted by Claude Code and reviewed line-by-line before commit. |
| `tests/test_schemas.py`, `test_evidence.py`, `test_util.py`, `conftest.py` | Claude Code | Test cases target the specific guarantees schemas.py claims to make (see each test module's docstring); reviewed for whether they'd actually catch a regression, not just pass. |
| `src/triage/cache.py`, `source.py`, `sources/yc.py`, `sources/hn.py` | Claude Code, tuned jointly against the live APIs | Founder-page parsing, the keyword filter, and the HTML body cap all came from actually running against the real YC/HN APIs during the build, not from spec alone — see docs/decisions/0003. |
| `tests/test_cache.py`, `test_source_yc.py`, `test_source_hn.py`, `test_source_pipeline.py`, `test_source_live.py` | Claude Code | The relevance-filter test runs against a trimmed but real slice of the Winter 2025 batch, not synthetic data, specifically to catch filter false positives (it did — see ADR 0003). |
| `src/triage/thesis.py`, `analyse.py`, `prompts/analyse_*.md` | Claude Code, design co-decided | The two ADR-0004 calls — call computed from the score rather than asked for, prompt generated live from `docs/thesis.md` rather than duplicated — were discussed and agreed before writing, mirroring the schemas.py pattern from ADR 0002. Originally built against Anthropic's tool-use API; reworked mid-build to OpenAI's function-calling shape once that was the key actually available — see ADR 0005. **Now run for real** (2026-08-20, `gpt-4o-mini`, `OPENAI_API_KEY` set locally): 15/15 candidates produced a valid, evidence-checked `Analysis`. One (`mastra`) failed to parse on its first attempt — a genuinely malformed tool-call response, not a test artifact — and the retry loop caught it and succeeded on attempt 2, exactly as designed. All 15 independently re-verified against `check_evidence_integrity` after the run, not just trusted at write time. |
| `tests/test_thesis.py`, `test_thesis_sync.py`, `test_analyse_prompts.py`, `test_analyse.py`, `test_analyse_pipeline.py`, `test_analyse_live.py` | Claude Code | The retry-loop tests (`test_analyse.py`) are the ones I'd defend hardest: each targets one specific way a model response can be wrong (malformed, wrong dimension names, dangling evidence, no tool call at all) and asserts the *correction text* sent back on retry actually names the problem, not just that a retry happened. |
| `templates/memo.md`, `src/triage/memo.py`, `pipeline.py` | Claude Code, design co-decided | Memo is deliberately pure rendering — no LLM call, no new judgement (ADR 0006). Two real formatting bugs (a blank-line-in-table bug that would have silently broken the Scores table on GitHub, and multi-paragraph bullets from embedded newlines in scraped bios) were found only by rendering the 15 real committed analyses, not by the offline test suite — both are now regression-tested and documented in ADR 0006 as a general lesson: the offline suite proves the logic, a real run proves the formatting. |
| `tests/test_memo.py`, `test_memo_pipeline.py`, `test_pipeline.py` | Claude Code | Includes the two regression tests for the formatting bugs above, added after finding them against real output, not written speculatively. |
| `src/triage/llm.py` | Claude Code | Extracted from analyse.py once eval.py needed the identical OpenAI tool-forcing/parsing logic — a real duplication found by writing the second call site, not speculative abstraction. |
| `src/triage/eval.py`, `prompts/eval_judge.md` | Claude Code, design co-decided | Scoped deliberately narrow (ADR 0007): only grades what structural validation can't already guarantee — evidence *quality*, not evidence *existence* — plus 60-second clarity. Not yet run against a real model in this environment; same honest-gap pattern as Phase 3's first commit. |
| `tests/test_eval.py`, `test_eval_pipeline.py`, `test_eval_live.py`, plus the empty-input tests added to `test_analyse_pipeline.py`/`test_memo_pipeline.py` and the `founders=[]` memo test | Claude Code | The empty-input and no-founders tests are genuine gaps found while writing ADR 0007's robustness table, not padding — each documents a real, previously-untested behaviour. |
| _(rows added per phase)_ | | |

## Where I overrode the AI

*(Keep this section populated — it's the part that shows judgment. Every time you reject
a suggestion or fix something it got wrong, add a line.)*

## What I'd have done differently with more time

*(Fill in at the end, honestly.)*
