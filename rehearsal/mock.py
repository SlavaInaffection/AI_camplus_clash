"""Fake-but-plausible agent outputs for REHEARSAL_MOCK=1 (frontend work without an API key).

Deterministic per chunk, so the 3D classroom gets reproducible, visibly changing states.
"""

import random

from .personas import BY_ID
from .schemas import (
    AnalystReport, CoachSummary, DirectorTurn, FixProposal, FixSelection, SlideIssue, SpeakerPick, StudentLine,
    StudentState,
)

BUBBLES = {
    "listening": "🙂", "taking_notes": "📝", "nodding": "👍", "confused": "🤔", "lost": "😵", "bored": "😐",
    "sleeping": "💤", "on_phone": "📱", "excited": "🤩", "hand_raised": "✋",
}

ISSUES = {
    "attention": ("No reason given for why this matters before the details start.", "Motivation and signalling", "Open with a one-line real-world question this slide answers."),
    "cognitive_load": ("Four new terms are introduced on one slide with no worked example.", "Cognitive load theory: element interactivity", "Split into two slides and add a worked example between them."),
    "prerequisites": ("Uses notation from last week without recapping it.", "Missing prerequisite knowledge", "Add a 30-second recap of the notation at the top."),
    "memory": ("Key definition appears once and is never revisited.", "Retrieval practice and spacing", "End with a one-question check that asks students to restate it."),
}


def analyst(dimension: str, slides) -> AnalystReport:
    rng = random.Random(dimension)
    problem, principle, suggestion = ISSUES[dimension]
    picked = rng.sample(range(len(slides)), k=min(2, len(slides))) if slides else []
    issues = [SlideIssue(slide_index=i, dimension=dimension, severity=rng.randint(1, 3), problem=problem,
                         principle=principle, suggestion=suggestion) for i in picked]
    return AnalystReport(dimension=dimension, issues=issues, overall=f"[mock] {principle} is the main {dimension} risk.")


def director(states: list[dict], chunk_index: int) -> DirectorTurn:
    rng = random.Random(chunk_index)
    out = []
    for s in states:
        drift = rng.randint(-20, 12)
        attention = max(0, min(100, s["attention"] + drift))
        confusion = max(0, min(100, s["confusion"] + rng.randint(-10, 22)))
        if attention < 25:
            state = rng.choice(["sleeping", "on_phone"])
        elif confusion > 70:
            state = "lost"
        elif confusion > 45:
            state = "confused"
        elif attention > 75:
            state = rng.choice(["taking_notes", "nodding", "listening", "excited"])
        else:
            state = rng.choice(["listening", "bored"])
        out.append(StudentState(id=s["id"], attention=attention, confusion=confusion, state=state,
                                bubble=BUBBLES[state], reason=f"[mock] {BY_ID[s['id']]['loses_focus_when']}"))
    speakers = []
    confused = [s for s in out if s.state in ("confused", "lost")]
    if confused and chunk_index % 2 == 1:
        who = rng.choice(confused)
        who.state, who.bubble = "hand_raised", BUBBLES["hand_raised"]
        action = "whisper_to_neighbour" if who.id == 6 else "raise_hand"
        speakers.append(SpeakerPick(
            id=who.id, action=action, intent="ask to clarify the last point",
            says="Sorry — could you say that last bit again with an example?",
        ))
    return DirectorTurn(students=out, speakers=speakers, chunk_summary=f"[mock] chunk {chunk_index}")


def student(persona: dict, pick) -> StudentLine:
    lines = {
        "whisper_to_neighbour": "Psst, did you get what that last part meant?",
        "interrupt": "Sorry, can I stop you there for a second?",
        "raise_hand": "Sorry, could you explain that last step again with an example?",
    }
    return StudentLine(says=f"[{persona['name']}] {lines.get(pick.action, lines['raise_hand'])}")


def fix(name: str, moment) -> FixProposal:
    return FixProposal(agent=name, approach=f"[mock] {name} version of the explanation at chunk {moment.chunk_index}.",
                       why_it_helps="[mock] Reduces cognitive load with a concrete anchor.",
                       who_it_helps=moment.lost_students[:3], risk="[mock] Takes two extra minutes.")


def select(proposals) -> FixSelection:
    return FixSelection(chosen_agent=proposals[0].agent, final_fix=proposals[0].approach,
                        reasoning="[mock] Helps the most lost students with the least extra time.")


def coach(moments) -> CoachSummary:
    return CoachSummary(summary=f"[mock] You lost the class at {len(moments)} key moments.",
                        strengths=["[mock] Clear opening"],
                        top_changes=["[mock] Add an example", "[mock] Recap prerequisites", "[mock] Pause for questions"])
