"""Shared OpenAI function-calling plumbing — used by both analyse.py and
eval.py so the "how do we force and parse a tool call" logic exists in exactly
one place, not duplicated per LLM-calling stage.

Kept deliberately tiny: this is not a general LLM abstraction layer (see ADR
0005 — the project targets one provider on purpose, not an abstraction over
several), just the one bit of response-shape handling two different stages
both need.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class LLMResponseError(RuntimeError):
    """A model response couldn't be turned into usable structured output."""


def function_tool_schema(name: str, description: str, model: type[BaseModel]) -> dict:
    """Build an OpenAI `tools=[...]` entry that forces the model to fill in
    `model`'s JSON Schema via a single named function call."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": model.model_json_schema(),
        },
    }


def extract_tool_arguments(response: Any, tool_name: str) -> dict:
    """OpenAI returns function-call arguments as a JSON *string*, not a dict —
    a malformed one is exactly as retry-able as a schema mismatch, so a bad
    JSON parse here raises the same LLMResponseError a caller already has to
    handle for "model didn't call the tool at all"."""
    message = response.choices[0].message
    for tool_call in message.tool_calls or []:
        if tool_call.function.name == tool_name:
            try:
                return json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as exc:
                raise LLMResponseError(f"tool call arguments were not valid JSON: {exc}") from exc
    raise LLMResponseError(f"model response did not include a {tool_name!r} tool call")
