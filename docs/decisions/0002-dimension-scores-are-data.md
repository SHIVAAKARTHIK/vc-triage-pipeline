# ADR 0002 — Score dimensions are data, not schema fields; the total is computed, not asked for

- **Date:** 2026-08-17
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code

## Context

Phase 1 (schemas) landed before `docs/thesis.md` was fully written. The thesis's
scoring table names the dimensions (e.g. workflow ownership, team–domain fit) and
their weights, and those are exactly the things most likely to change as the thesis
gets sharpened.

## Decision

`DimensionScore` is `{name, weight, score, rationale}` — a generic row, not a
Pydantic field per dimension (no `Analysis.workflow_ownership_score: int`). The
thesis's dimension table becomes a small config the analyse stage loads and hands to
the model as part of the prompt; `Analysis.dimension_scores` just has to sum its
weights to 100, whatever the names turn out to be.

`Analysis.total_score` is a `@computed_field` — a property, not a field the model
fills in. Python always derives it as `sum(score/10 * weight)` from the dimension
list. The model is never asked for a total and never trusted to do the arithmetic.

## Rationale

- Decouples the schema from the thesis's wording. Renaming or re-weighting a
  dimension in `docs/thesis.md` is a one-file change; it doesn't touch
  `schemas.py`, doesn't ripple into old `data/analyses/*.json` files written under
  a different dimension set, and doesn't need a migration.
- A model asked to both rate dimensions *and* report a total will occasionally
  report a total that doesn't match its own ratings — that's a class of bug worth
  eliminating by construction rather than catching in review.
- Every `Analysis` carries `thesis_version` (a hash/tag of the thesis snapshot it
  was scored against), so even as the dimension set evolves, each stored analysis
  stays self-describing about which thesis produced it.

## Alternatives considered

- **Hardcoded fields per dimension.** Rejected: ties the schema to today's wording
  of the thesis and forces a schema change on every scoring tweak — friction in
  exactly the place (thesis iteration) that should stay cheap this week.
- **Ask the model for `total_score` directly.** Rejected: removes the guarantee
  that the number on a memo is arithmetically traceable to the ratings above it,
  which is the same traceability property `evidence.py` enforces for claims.

## Consequences

- The analyse stage must validate the model's dimension names against the
  thesis's config before accepting a response (a dimension the model invents, or
  drops, should fail loudly rather than silently changing what's being measured).
  That check lands in Phase 3, alongside the config loader.
- `docs/thesis.md`'s scoring table is now load-bearing for more than
  documentation — Phase 3 reads it. It still needs to be finished before Phase 3.
