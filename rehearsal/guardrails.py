"""Input guardrails — code checks the model cannot be talked around.

The rehearsal room only supports teaching / presentation practice.
Out-of-scope requests are refused with a clear boundary message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Keep lines short: these strings are shown in the UI and in example logs for judges.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(hack|cheat|exam answers?|solve (the )?test|plagiar|give me the (answers|solutions))\b", re.I),
        "Boundary held: I won't help cheat on exams or steal answers. Rehearse teaching — don't short-circuit assessment.",
    ),
    (
        re.compile(r"\b(weapon|bomb|kill|harm yourself|suicide|make a virus)\b", re.I),
        "Boundary held: that request is outside the rehearsal room. This agent only simulates a classroom audience.",
    ),
    (
        re.compile(r"\b(enroll|enrolment|tuition|timetable|room booking|campus bus|fees?|housing application)\b", re.I),
        "Boundary held: admin/logistics are out of scope. This room is for teaching, learning, and presentation rehearsal only.",
    ),
    (
        re.compile(r"\b(ignore (your|all) (rules|instructions)|jailbreak|DAN mode)\b", re.I),
        "Boundary held: I stay in role as a teaching rehearsal simulator. Ask me to react to your lecture instead.",
    ),
]


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str | None = None


def check_input(text: str) -> GuardrailResult:
    trimmed = (text or "").strip()
    if not trimmed:
        return GuardrailResult(False, "Empty input.")
    if len(trimmed) > 8000:
        return GuardrailResult(False, "Input too long for one rehearsal step.")
    for pattern, reason in _RULES:
        if pattern.search(trimmed):
            return GuardrailResult(False, reason)
    return GuardrailResult(True)


def sanitize_line(line: str, limit: int = 280) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())[:limit]
