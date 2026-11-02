"""Provider-neutral LLM client with tool calling.

The rest of the app talks to `LLMClient.complete()` using three message shapes:
  {"role": "user", "content": str}
  {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "input"}]}
  {"role": "tool", "tool_call_id": str, "content": str}
Each provider class translates these to its own API format, so switching
between OpenAI and Anthropic is a one-line config change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import settings


class LLMError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    def complete(
        self, system: str, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse: ...


class AnthropicClient:
    def __init__(self, api_key: str, model: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @staticmethod
    def _convert(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }
                # consecutive tool results must share one user message
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            elif m["role"] == "assistant" and m.get("tool_calls"):
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [
                    {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["input"]}
                    for c in m["tool_calls"]
                ]
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def complete(self, system, messages, tools=None) -> LLMResponse:
        kwargs = {
            "model": self._model,
            "max_tokens": 2000,
            "system": system,
            "messages": self._convert(messages),
        }
        if tools:
            kwargs["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]
        try:
            resp = self._client.messages.create(**kwargs)
        except Exception as e:
            raise LLMError(f"Anthropic call failed: {e}") from e
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [
            ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"
        ]
        return LLMResponse(text, calls)


class OpenAIClient:
    def __init__(self, api_key: str, model: str):
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    @staticmethod
    def _convert(system: str, messages: list[dict]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "tool":
                out.append(
                    {"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]}
                )
            elif m["role"] == "assistant" and m.get("tool_calls"):
                out.append(
                    {
                        "role": "assistant",
                        "content": m.get("content") or None,
                        "tool_calls": [
                            {
                                "id": c["id"],
                                "type": "function",
                                "function": {
                                    "name": c["name"],
                                    "arguments": json.dumps(c["input"], ensure_ascii=False),
                                },
                            }
                            for c in m["tool_calls"]
                        ],
                    }
                )
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def complete(self, system, messages, tools=None) -> LLMResponse:
        kwargs = {"model": self._model, "messages": self._convert(system, messages)}
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ]
        try:
            msg = self._client.chat.completions.create(**kwargs).choices[0].message
        except Exception as e:
            raise LLMError(f"OpenAI call failed: {e}") from e
        calls = [
            ToolCall(c.id, c.function.name, json.loads(c.function.arguments or "{}"))
            for c in (msg.tool_calls or [])
        ]
        return LLMResponse(msg.content or "", calls)


DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini"}


def get_llm() -> LLMClient:
    """Build the configured client. Raises LLMError with a clear message if unset."""
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not set in .env")
    provider = settings.llm_provider.lower()
    if provider not in DEFAULT_MODELS:
        raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'")
    model = settings.llm_model or DEFAULT_MODELS[provider]
    cls = AnthropicClient if provider == "anthropic" else OpenAIClient
    return cls(settings.llm_api_key, model)
