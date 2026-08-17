# triage

An AI-augmented deal triage pipeline for a seed-stage fund. Point it at a topic, get
investment memos out the other end.

> **Status: in development.** Phase 0 (scaffold) complete. See `docs/worklog.md` for the
> running account of how this is being built.

## Quickstart

```bash
uv sync
uv run triage version
```

Full pipeline usage lands in Phase 2. The intended shape:

```bash
uv run triage run --topic "AI agents for back-office ops"
```

## How it works

Three stages, each reading the previous stage's artefact from disk so any stage can be
re-run in isolation:

| Stage | Reads | Writes |
| --- | --- | --- |
| `source` | a topic or feed | `data/candidates.json` |
| `analyse` | `data/candidates.json` | `data/analyses/<slug>.json` |
| `memo` | `data/analyses/<slug>.json` | `out/memos/<slug>.md` |

Raw HTTP responses are cached under `data/raw/` and committed, so runs are replayable
offline and the test suite needs no network.

## Reading this repo

| If you want to know… | Read |
| --- | --- |
| What this fund invests in and how companies are scored | `docs/thesis.md` |
| Why it's built this way | `docs/decisions/` |
| How it actually got built, day by day | `docs/worklog.md` |
| Where AI did the work | `AI_USE.md` |
| The prompts driving the analysis stage | `prompts/` |

## Development

```bash
uv run pytest
uv run ruff check .
```

Tests are offline by default. Tests marked `live` hit the network or a real LLM:

```bash
uv run pytest -m live
```
