# triage

An AI-augmented deal triage pipeline for a seed-stage fund. Point it at a topic, get
investment memos out the other end.

> **Status: in development.** Sourcing and analysis are live; memo rendering lands next.
> See `docs/worklog.md` for the running account of how this is being built.

## Quickstart

```bash
uv sync
uv run triage source --batch "Winter 2025" --limit 15
ANTHROPIC_API_KEY=... uv run triage analyse
```

`source` ranks a YC batch by thesis relevance (see `docs/decisions/0003`) and writes
`data/candidates.json`, each candidate backed by evidenced founder/traction/product
facts. Re-running it replays entirely from the committed `data/raw/` cache — no network
needed.

`analyse` scores each candidate against `docs/thesis.md` — the whole thesis (slice,
why-now, anti-portfolio, scoring dimensions) is pulled live from that document into the
prompt, so editing the thesis is the only edit needed to change what the model sees (see
`docs/decisions/0004`). Needs a real `ANTHROPIC_API_KEY`; writes one evidence-checked,
validator-passed `Analysis` per candidate to `data/analyses/<slug>.json`.

`memo` lands next; the intended shape once it does:

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
