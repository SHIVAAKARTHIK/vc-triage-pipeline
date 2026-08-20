# ADR 0005 — Analyse stage targets OpenAI, not Anthropic

- **Date:** 2026-08-19
- **Status:** Accepted, supersedes the Anthropic-specific parts of ADR 0004
- **Authored by:** Karthik, drafted with Claude Code

## Context

Phase 3 was originally built end-to-end against Anthropic's Messages API (tool
use, forced tool choice, `system` as a separate parameter). It shipped with 97
passing tests, all against a scripted fake client — genuinely untested against
any real model, because no `ANTHROPIC_API_KEY` was available in the build
environment (logged honestly in `AI_USE.md` at the time).

Karthik has an OpenAI key, not an Anthropic one. The brief's constraint is
"LLMs: any model" — so this is a which-provider-is-actually-runnable call, not
a quality judgement between the two.

## Decision

Reworked the LLM-facing half of `src/triage/analyse.py` to OpenAI's chat
completions / function-calling API instead. What changed and what didn't:

**Changed** (provider-shaped, in `analyse.py` only):
- System prompt is now `messages[0]` with `role: "system"`, not a separate
  `system=` parameter — so `render_system_prompt()`'s output is unchanged, only
  where it gets placed in the call.
- Tool schema wraps in `{"type": "function", "function": {name, description,
  parameters}}` instead of Anthropic's flatter `{name, description,
  input_schema}` — `RawAnalysis.model_json_schema()` still supplies the actual
  JSON Schema either way.
- `tool_choice` is `{"type": "function", "function": {"name": ...}}` instead
  of `{"type": "tool", "name": ...}`.
- The response's tool-call arguments arrive as a JSON **string**
  (`message.tool_calls[0].function.arguments`), not a dict
  (`block.input`) — `_extract_tool_input` now does its own `json.loads`, and a
  malformed string is caught as the same retry-able `LLMResponseError` a
  schema mismatch already was, not a new failure class.
- `DEFAULT_MODEL = "gpt-4o-mini"` (was `"claude-sonnet-5"`) — a placeholder
  worth overriding via `--model` if it's aged out of availability by the time
  this is run.

**Did not change** (everything that made this design worth having in the first
place, per ADR 0004):
- `RawAnalysis` — still the same fields, still no `total_score`, still no
  `call`.
- The retry loop's logic — malformed response, wrong dimension names, dangling
  evidence — untouched; only what `send_message` is and what shape its
  response takes moved.
- `call` is still computed from `weighted_total()` via
  `thesis.call_for_score()`, never asked for.
- The prompt is still generated live from `docs/thesis.md` via
  `thesis.section()` — provider-agnostic by construction.
- The `send_message` injection seam in `analyse_candidate` — designed as a
  bare callable from the start specifically so it wouldn't matter which
  provider's SDK method got passed in.

## Consequences

- `tests/conftest.py`'s `tool_response`/`text_response` fixtures were rewritten
  to build fake `ChatCompletion`-shaped objects
  (`choices[0].message.tool_calls[...].function.{name,arguments}`) instead of
  fake Anthropic `Message` objects. `tests/test_analyse.py`'s two assertions
  that inspect the corrective re-prompt moved from `messages[0]["content"]` to
  `messages[1]["content"]`, since the system prompt now occupies index 0.
- `anthropic` was removed from `pyproject.toml`; `openai` added. No dead
  dependency left pointing at the provider this stage no longer calls.
- This is the second provider-shaped rework of this stage inside one phase —
  worth naming as a real cost of the `send_message`-as-bare-callable design
  from ADR 0004: it isolated the blast radius to `analyse.py` and
  `conftest.py`'s two fixtures, and nothing in `thesis.py`, the prompts, the
  retry semantics, or `schemas.py` had to change at all.
