# ADR 0007 — Robustness posture, and what the eval stage checks that structural validation can't

- **Date:** 2026-08-21
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code

## Context

The brief's Phase 5 ask (from the original build plan) was to deliberately
break things — dead links, missing founder data, malformed LLM output — and
confirm graceful degradation, then add a small LLM-judge eval over the
memos. Most of the actual degradation logic was already built and tested
stage-by-stage as Phases 2-4 landed, not saved up for a separate pass — this
ADR is where that posture gets consolidated into one place, plus the eval
stage that's genuinely new.

## Part 1 — Where each failure mode is actually handled

| Failure | Where | Behaviour |
| --- | --- | --- |
| YC/HN/homepage URL 404s or times out | `source.build_candidate` | Caught per-fetch; candidate still built from whatever evidence *did* resolve (min. the YC listing, which schemas.py requires ≥1 evidence item to build a Candidate at all) |
| A page has no founder data | `sources/yc.parse_founders` | Returns `[]`, not an error — `Candidate.founders` is optional by schema |
| No HN coverage (the common case, ADR 0003) | `sources/hn.find_traction` | Returns `None`; `build_candidate` falls back to a `yc_batch` traction signal |
| Model returns malformed/wrong-shaped JSON | `analyse.analyse_candidate`, `eval.judge_memo` | Retried with a corrective note naming the exact problem; caught as `AnalysisFailedError`/`JudgeFailedError` after the budget, and the *stage* (`run()`) skips that one item and keeps going rather than aborting |
| Model cites evidence that was never collected | `evidence.check_evidence_integrity`, re-checked in `memo.render_memo` | Rejected before an `Analysis` or memo can be built from it |
| Zero candidates / zero analyses / zero memos reach a stage | `analyse.run`, `memo.run`, `eval.run` | Each returns `[]` and writes nothing rather than raising — a legitimately empty upstream result isn't an error |
| A memo cites no matching candidate (stale/orphaned analysis file) | `memo.run` | Logged and skipped, not a crash |

None of this is new work added in this phase — it's what "graceful
degradation" actually meant at each stage when it was built, gathered here so
the posture is visible in one place rather than only discoverable by reading
five files.

**What's new in this phase:** the three empty-input tests
(`test_zero_candidates_produces_zero_analyses_without_error` and its `memo`/
`eval` counterparts) and the `founders=[]` memo-rendering test — genuine gaps
found while writing this ADR, not previously covered.

## Part 2 — The eval stage checks what structural validation can't

`check_evidence_integrity` already guarantees, before a memo can be built,
that every cited evidence *id* resolves to something the candidate actually
collected. It cannot check whether that evidence *actually supports* the
specific claim it's attached to — an id can resolve and still be a weak or
mismatched citation. That's the one thing worth spending an LLM call on
after the fact, and the only thing `eval.judge_memo` is asked to grade,
alongside the brief's other named concern: can a partner find the call in
60 seconds (`docs/decisions/0006`'s design goal, checked from the outside
this time instead of assumed).

`RawJudgment` deliberately has only two scored dimensions — traceability
quality and clarity, both 1-5 with required notes citing something specific
in the memo, not a generic restatement. A shorter retry budget than
`analyse_candidate`'s (2 attempts, not 3): a grading pass that fails to parse
twice isn't worth a third attempt the way a candidate's actual analysis is.

`src/triage/llm.py` exists because of this stage: extracting the OpenAI
tool-forcing/response-parsing logic out of `analyse.py` into a small shared
module was the honest move once a second stage needed the identical
plumbing, rather than copy-pasting `_tool_schema`/`_extract_tool_input` a
second time with a new tool name.

## Consequences

- `data/eval.json` is committed like every other stage's output — the
  brief's "commit outputs so we don't need to re-run" applies here too.
- The eval stage's own output has not been independently re-validated the
  way `check_evidence_integrity` re-validates analyses at read time — a
  judge score is read as-is. That's a deliberate scope boundary: the point of
  this stage is to *surface* a quality signal for a human to read, not to be
  another gate the pipeline enforces automatically.
