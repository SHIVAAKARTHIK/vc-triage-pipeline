# ADR 0001 — Stack, scope, and what we are deliberately not building

- **Date:** 2026-08-17
- **Status:** Accepted
- **Authored by:** Karthik, drafted with Claude Code during the kickoff planning session

## Context

The brief asks for a three-stage pipeline (source → analyse → recommend) in an
estimated 6–8 hours, and grades scoping and judgment at 20% while explicitly warning
against overengineering ("if you're building a job queue, vector DB cluster, or React
frontend — stop"). So the binding constraint is not capability, it's restraint.

## Decision

**Stack:** Python 3.13, `uv` for dependency management, Pydantic for schemas, Typer for
the CLI, Jinja2 for memo rendering, pytest for tests, ruff for lint. Anthropic's API for
the analysis stage.

**Persistence:** the filesystem. JSON for structured artefacts, Markdown for memos.
No database, no ORM, no migrations.

**Stage boundaries:** each stage is a pure-ish function from one on-disk artefact to the
next, so any stage can be re-run in isolation without repeating the one before it.

```
source  → data/candidates.json      (+ data/raw/ cached HTTP responses)
analyse → data/analyses/<slug>.json
memo    → out/memos/<slug>.md
```

**Caching:** every outbound HTTP response is written to `data/raw/` keyed by URL hash,
and the cache is committed to the repo.

## Rationale

- Filesystem persistence is enough for 10–20 companies and keeps the artefacts *readable
  by a reviewer* — a reviewer can open `data/analyses/foo.json` in the GitHub UI and
  check it against the memo. A database would hide the same data behind a client.
- Committing the HTTP cache means a reviewer can run the pipeline end-to-end with no API
  keys for the sourcing stage and get byte-identical candidates. It also makes the test
  suite fully offline.
- Computing the score in Python from per-dimension ratings (rather than asking the model
  for one number) makes scores reproducible and auditable, and means changing a weight
  doesn't require re-running any LLM calls. See ADR 0003 when written.

## Alternatives considered

- **SQLite for artefacts.** Rejected: nothing here needs querying, and it makes the
  outputs less legible to a reviewer, which the brief explicitly cares about.
- **LangChain / an agent framework.** Rejected: three sequential stages with one LLM call
  each does not need an orchestration layer. The framework would be more code than the
  pipeline.
- **A web UI.** Rejected — the brief rules it out by name.

## Consequences

- No concurrency story beyond simple batching; with 10–20 companies that is fine, and if
  it stops being fine that is a signal the scope grew.
- The committed cache will go stale. Accepted: staleness is visible via the
  `retrieved_at` timestamp carried on every piece of evidence.
