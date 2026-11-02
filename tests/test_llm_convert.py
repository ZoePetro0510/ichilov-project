"""Message translation between our neutral format and each provider's format."""

import json

from app.llm import AnthropicClient, OpenAIClient

HISTORY = [
    {"role": "user", "content": "שאלה"},
    {
        "role": "assistant",
        "content": "בודק",
        "tool_calls": [
            {"id": "a", "name": "t1", "input": {"x": 1}},
            {"id": "b", "name": "t2", "input": {}},
        ],
    },
    {"role": "tool", "tool_call_id": "a", "content": "r1"},
    {"role": "tool", "tool_call_id": "b", "content": "r2"},
]


def test_anthropic_groups_tool_results_in_one_user_message():
    out = AnthropicClient._convert(HISTORY)
    assert [m["role"] for m in out] == ["user", "assistant", "user"]
    assert [b["type"] for b in out[1]["content"]] == ["text", "tool_use", "tool_use"]
    assert [b["tool_use_id"] for b in out[2]["content"]] == ["a", "b"]


def test_openai_uses_tool_role_and_json_arguments():
    out = OpenAIClient._convert("sys", HISTORY)
    assert out[0] == {"role": "system", "content": "sys"}
    assert json.loads(out[2]["tool_calls"][0]["function"]["arguments"]) == {"x": 1}
    assert [m["role"] for m in out[3:]] == ["tool", "tool"]
