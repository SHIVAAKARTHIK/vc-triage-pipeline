# How AI was used to build this

The brief says to use AI freely and be honest about it, and that hiding it — not using
it — is what gets penalised. So this file is a straight accounting, kept current as the
repo grows rather than assembled at the end.

## Tooling

- **Claude Code (Opus 5)** — used as a pair-programmer throughout: planning, scaffolding,
  writing modules and tests, and reviewing my own changes.
- **Claude (API)** — the analysis stage of the pipeline itself calls the Anthropic API.
  That's product, not process; see `prompts/` for the prompts and `docs/` for why they
  look the way they do.

## Per-module accounting

Updated as each phase lands. "Authored by" describes who produced the first draft;
everything in this repo was read and revised by me before commit.

| Module / artefact | Authored by | Notes |
| --- | --- | --- |
| `pyproject.toml`, repo scaffold | Claude Code | Standard `uv init` plus config I reviewed. |
| `docs/decisions/0001-*.md` | Claude Code, from decisions we made jointly | Facts and rationale are ours; prose is drafted. |
| `docs/thesis.md` | Karthik | Written by hand, deliberately. The scores mean nothing if the thesis isn't mine. |
| `docs/worklog.md` | Karthik | Same reason. |
| _(rows added per phase)_ | | |

## Where I overrode the AI

*(Keep this section populated — it's the part that shows judgment. Every time you reject
a suggestion or fix something it got wrong, add a line.)*

## What I'd have done differently with more time

*(Fill in at the end, honestly.)*
