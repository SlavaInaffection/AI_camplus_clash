"""One function every agent uses: system prompt + input in, validated Pydantic object out.

Mock mode (no OPENAI_API_KEY, or REHEARSAL_MOCK=1) returns the agent's mock output instead,
so the frontend can be built without spending tokens.
"""

import json
import os
import time
from pathlib import Path
from typing import Callable, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MOCK = os.environ.get("REHEARSAL_MOCK") == "1" or not os.environ.get("OPENAI_API_KEY")

MODELS = {
    "analyst": os.environ.get("ANALYST_MODEL", "gpt-5.5"),
    "director": os.environ.get("DIRECTOR_MODEL", "gpt-5.4-mini"),
    "student": os.environ.get("STUDENT_MODEL", "gpt-5.4-mini"),
    "coach": os.environ.get("COACH_MODEL", "gpt-5.5"),
}
# Reasoning effort per role ("" disables the parameter, for non-reasoning models)
EFFORT = {
    "analyst": os.environ.get("ANALYST_EFFORT", "medium"),
    "director": os.environ.get("DIRECTOR_EFFORT", "low"),
    "student": os.environ.get("STUDENT_EFFORT", "low"),
    "coach": os.environ.get("COACH_EFFORT", "medium"),
}

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "trace.jsonl"

_client = None
if not MOCK:
    from openai import OpenAI

    _client = OpenAI()

T = TypeVar("T", bound=BaseModel)


class AgentError(RuntimeError):
    pass


def ask(agent: str, role: str, system: str, payload: dict, schema: type[T], mock: Callable[[], T]) -> T:
    started = time.time()
    if MOCK:
        result = mock()
    else:
        kwargs = {}
        if EFFORT[role]:
            kwargs["reasoning"] = {"effort": EFFORT[role]}
        try:
            response = _client.responses.parse(
                model=MODELS[role],
                instructions=system,
                input=json.dumps(payload, ensure_ascii=False),
                text_format=schema,
                **kwargs,
            )
        except Exception as e:  # surfaced to the API caller as a 502 with the agent name
            raise AgentError(f"{agent}: {type(e).__name__}: {e}") from e
        result = response.output_parsed
        if result is None:
            raise AgentError(f"{agent}: model returned no parsable output (possibly a refusal)")
    _trace(agent, payload, result, time.time() - started)
    return result


def _trace(agent: str, payload: dict, result: BaseModel, seconds: float) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps({
            "ts": time.time(), "agent": agent, "seconds": round(seconds, 2), "mock": MOCK,
            "input": json.dumps(payload, ensure_ascii=False)[:3000], "output": result.model_dump(),
        }, ensure_ascii=False) + "\n")
