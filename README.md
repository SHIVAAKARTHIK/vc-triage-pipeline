# triage

An AI-augmented deal triage pipeline for a seed-stage fund. Point it at a YC batch,
get investment memos out the other end.

> **Status: all three stages are live and have been run end-to-end against real data.**
> See `docs/worklog.md` for the running account of how this was built.

## Quickstart

```bash
uv sync
OPENAI_API_KEY=... uv run triage run --batch "Winter 2025" --limit 15
```

Runs the full pipeline in one command — the brief's own "done" bar. Individually:

```bash
uv run triage source --batch "Winter 2025" --limit 15
OPENAI_API_KEY=... uv run triage analyse
uv run triage memo
```

`source` ranks a YC batch by thesis relevance (see `docs/decisions/0003`) and writes
`data/candidates.json`, each candidate backed by evidenced founder/traction/product
facts. Re-running it replays entirely from the committed `data/raw/` cache — no network
needed.

`analyse` scores each candidate against `docs/thesis.md` — the whole thesis (slice,
why-now, anti-portfolio, scoring dimensions) is pulled live from that document into the
prompt, so editing the thesis is the only edit needed to change what the model sees (see
`docs/decisions/0004`). Needs a real `OPENAI_API_KEY`; writes one evidence-checked,
validator-passed `Analysis` per candidate to `data/analyses/<slug>.json`.

`memo` renders each analysis to a one-page Markdown memo, with a Sources footer traced
back to exactly the evidence that analysis cites (see `docs/decisions/0006`). Pure
rendering — no network, no LLM, no judgement calls.

The seed input is a YC batch rather than a free-text topic query — a deliberate scoping
choice (`docs/decisions/0003`), and one of the brief's own named examples of a valid
seed input ("a feed like the YC W25 batch").

## How it works

Three stages, each reading the previous stage's artefact from disk so any stage can be
re-run in isolation:

| Stage | Reads | Writes |
| --- | --- | --- |
| `source` | a YC batch | `data/candidates.json` |
| `analyse` | `data/candidates.json` | `data/analyses/<slug>.json` |
| `memo` | `data/candidates.json` + `data/analyses/<slug>.json` | `out/memos/<slug>.md` |

Raw HTTP responses are cached under `data/raw/` and committed, so `source` is replayable
offline and the test suite needs no network. `data/analyses/` and `out/memos/` are also
committed — real output from a real run against `gpt-4o-mini`, not placeholders.

## Reading this repo

| If you want to know… | Read |
| --- | --- |
| What this fund invests in and how companies are scored | `docs/thesis.md` |
| Why it's built this way | `docs/decisions/` |
| How it actually got built, day by day | `docs/worklog.md` |
| Where AI did the work | `AI_USE.md` |
| The prompts driving the analysis stage (LLM-facing) | `prompts/` |
| The memo template (human-facing) | `templates/` |
| The actual output, for one real startup end-to-end | `out/memos/*.md` |

## Development

```bash
uv run pytest
uv run ruff check .
```

Tests are offline by default. Tests marked `live` hit the network or a real LLM:

```bash
uv run pytest -m live
```
