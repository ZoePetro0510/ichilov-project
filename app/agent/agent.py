"""The agent loop: the LLM picks tools, we run them, until it answers."""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agent.tools import DOCUMENTS_SCHEMA, TOOL_SPECS, run_tool
from app.llm import LLMClient
from app.models import AgentStep, Query
from app.prompts import AGENT_SYSTEM

MAX_STEPS = 6
MAX_OUTPUT_LOGGED = 4000


def run_agent(session: Session, llm: LLMClient, question: str) -> dict:
    started = time.perf_counter()
    system = AGENT_SYSTEM.format(schema=DOCUMENTS_SCHEMA)
    messages: list[dict] = [{"role": "user", "content": question}]

    query = Query(question=question)
    session.add(query)
    session.flush()

    steps: list[dict] = []
    answer = ""
    for _ in range(MAX_STEPS):
        resp = llm.complete(system, messages, TOOL_SPECS)
        if not resp.tool_calls:
            answer = resp.text.strip()
            break
        messages.append(
            {
                "role": "assistant",
                "content": resp.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "input": c.input} for c in resp.tool_calls
                ],
            }
        )
        for call in resp.tool_calls:
            output = run_tool(call.name, call.input, session, llm)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
            order = len(steps) + 1
            steps.append(
                {
                    "step": order,
                    "tool": call.name,
                    "input": call.input,
                    "output": output[:MAX_OUTPUT_LOGGED],
                }
            )
            session.add(
                AgentStep(
                    query_id=query.id,
                    step_order=order,
                    tool_name=call.name,
                    tool_input=call.input,
                    tool_output=output[:MAX_OUTPUT_LOGGED],
                )
            )
    else:
        answer = "לא הצלחתי להשלים את המשימה במספר הצעדים המותר."

    query.answer = answer
    query.latency_ms = int((time.perf_counter() - started) * 1000)
    session.commit()
    return {"query_id": query.id, "answer": answer, "steps": steps, "latency_ms": query.latency_ms}
