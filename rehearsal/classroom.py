"""During and after the rehearsal.

Live loop, per transcript chunk:
  Director (1 call)  -> updates all 15 students + picks 0-2 speakers
  Student agents (parallel, only the speakers) -> what they say out loud
After:
  lost moments (computed) -> 3 Fix agents in parallel -> Fix Evaluator -> Coach summary
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from . import mock
from .llm import ask
from .personas import BY_ID, PERSONAS, initial_states
from .schemas import (
    ChunkResult, CoachSummary, DirectorTurn, FixProposal, FixSelection, LectureAnalysis, LostMoment, MomentFix,
    RehearsalReport, Slide, Speaker, StudentJourney, StudentLine, StudentState,
)

RECENT_CHUNKS = 3
LOST_STATES = {"lost", "sleeping", "on_phone"}


def is_lost(s: dict) -> bool:
    return s["state"] in LOST_STATES or s["confusion"] >= 75 or s["attention"] <= 25


class Session:
    def __init__(self, course: str, slides: list[Slide]):
        self.id = uuid.uuid4().hex[:8]
        self.course = course
        self.slides = slides
        self.analysis: Optional[LectureAnalysis] = None
        self.states: list[dict] = initial_states()
        self.chunks: list[dict] = []  # {"text", "slide_index", "result": ChunkResult}

    def public(self) -> dict:
        return {
            "id": self.id, "course": self.course, "slides": [s.model_dump() for s in self.slides],
            "analysis": self.analysis.model_dump() if self.analysis else None,
            "students": self.states, "chunks": len(self.chunks),
        }


SESSIONS: dict[str, Session] = {}


# --- Director ---------------------------------------------------------------

DIRECTOR_SYSTEM = """You are the Director of a simulated university classroom used by lecturers to rehearse.
You receive the class roster (15 students defined by their situation), their current state, the slide being
shown, learning-science issues predicted for that slide, and the latest chunk of what the lecturer SAID.

Update EVERY student realistically:
- Changes are gradual (usually within +/-25 per chunk) unless something clearly helps or hurts.
- Base every change on the student's situation AND a learning-science principle (cognitive load, missing
  prerequisite, no example, pace, split attention, motivation, accessibility). Put that in "reason", short.
- Good teaching moves (a concrete example, a recap, a question to the class, a visual, defining a term)
  should visibly bring students back. Reward them.
- Pick 0-2 speakers, only when a real student in that state would speak. Shy students whisper instead of
  raising a hand. About one speaker every two or three chunks is realistic; do not make it constant.
- bubble is one emoji that matches the state.
Do not invent what the lecturer said; react only to the transcript."""


def _slide(session: Session, slide_index: Optional[int]) -> Optional[dict]:
    if slide_index is None or not (0 <= slide_index < len(session.slides)):
        return None
    slide = session.slides[slide_index].model_dump()
    if session.analysis:
        slide["predicted_issues"] = [i.model_dump() for i in session.analysis.issues if i.slide_index == slide_index]
    return slide


def direct(session: Session, text: str, slide_index: Optional[int]) -> DirectorTurn:
    payload = {
        "course": session.course,
        "roster": PERSONAS,
        "current_states": session.states,
        "slide": _slide(session, slide_index),
        "recent_transcript": [c["text"] for c in session.chunks[-RECENT_CHUNKS:]],
        "new_chunk": text,
        "chunk_index": len(session.chunks),
    }
    turn = ask("Director", "director", DIRECTOR_SYSTEM, payload, DirectorTurn,
               lambda: mock.director(session.states, len(session.chunks)))
    # Keep every student even if the model dropped one, and clamp numbers.
    by_id = {s.id: s for s in turn.students if s.id in BY_ID}
    merged = []
    for old in session.states:
        new = by_id.get(old["id"])
        if new:
            new.attention = max(0, min(100, new.attention))
            new.confusion = max(0, min(100, new.confusion))
            merged.append(new)
        else:
            merged.append(StudentState(**old))
    turn.students = merged
    turn.speakers = [sp for sp in turn.speakers if sp.id in BY_ID][:2]
    return turn


# --- Student agents ---------------------------------------------------------

def _student_system(persona: dict) -> str:
    return f"""You are {persona['name']}, a university student in a lecture.
Your situation: {persona['situation']}
Background: {persona['knowledge']}. You lose focus when: {persona['loses_focus_when']}.
Say ONE short, natural thing out loud (or whispered, if that is your action) that a real student in your state
would say right now: a question, a request to slow down or repeat, a challenge, or a comment.
Speak in the same language the lecturer is using, at your own language level. Be specific to what was just said."""


def speak(session: Session, turn: DirectorTurn, text: str, slide_index: Optional[int]) -> list[Speaker]:
    states = {s.id: s for s in turn.students}

    def one(pick) -> Speaker:
        persona = BY_ID[pick.id]
        payload = {
            "what_lecturer_just_said": text,
            "slide": _slide(session, slide_index),
            "your_state": states[pick.id].model_dump(),
            "action": pick.action,
            "what_you_want_to_say": pick.intent,
        }
        line = ask(f"Student:{persona['name']}", "student", _student_system(persona), payload, StudentLine,
                   lambda: mock.student(persona, pick))
        return Speaker(id=pick.id, action=pick.action, says=line.says, why=states[pick.id].reason)

    if not turn.speakers:
        return []
    with ThreadPoolExecutor(max_workers=len(turn.speakers)) as pool:
        return list(pool.map(one, turn.speakers))


def process_chunk(session: Session, text: str, slide_index: Optional[int]) -> ChunkResult:
    turn = direct(session, text, slide_index)
    speakers = speak(session, turn, text, slide_index)
    states = [s.model_dump() for s in turn.students]
    result = ChunkResult(
        chunk_index=len(session.chunks),
        slide_index=slide_index,
        students=turn.students,
        speakers=speakers,
        summary=turn.chunk_summary,
        class_attention=round(sum(s["attention"] for s in states) / len(states)),
        class_confusion=round(sum(s["confusion"] for s in states) / len(states)),
    )
    session.states = states
    session.chunks.append({"text": text, "slide_index": slide_index, "result": result})
    return result


# --- Report: lost moments -> Fix agents -> Evaluator -> Coach --------------

FIXERS = {
    "Example Maker": "Fix it with a concrete worked example or a familiar real-life case.",
    "Visual Designer": "Fix it with a visual: a diagram, a step-by-step build-up, or restructuring the slide (dual coding).",
    "Structure Coach": "Fix it by changing the sequence: recap the prerequisite, chunk the idea, add a check-for-understanding question.",
}

FIX_EVALUATOR_SYSTEM = """You are the Fix Evaluator. Several specialists proposed how the lecturer could re-explain a moment
where students got lost. Compare them on: how many of the lost students it brings back (especially the most excluded),
how well it is grounded in learning science, and how practical it is in a real lecture. Pick one or merge two.
Explain the choice in 1-2 plain sentences to the lecturer. The lecturer decides; you advise."""

COACH_SYSTEM = """You are a teaching coach reviewing a rehearsal in a simulated classroom. Be honest, specific and kind.
Point to concrete moments. Remember these are simulated students: predictions, not measurements."""


def _lost_moments(session: Session, limit: int) -> list[LostMoment]:
    moments, previously_lost = [], set()
    for c in session.chunks:
        r: ChunkResult = c["result"]
        lost = [s for s in r.students if is_lost(s.model_dump())]
        new = [s for s in lost if s.id not in previously_lost]
        previously_lost = {s.id for s in lost}
        if len(new) >= 2 or len(lost) >= 4:
            moments.append(LostMoment(
                chunk_index=r.chunk_index, slide_index=r.slide_index, excerpt=c["text"][:400],
                lost_students=[BY_ID[s.id]["name"] for s in (new or lost)],
                reasons=list(dict.fromkeys(s.reason for s in (new or lost)))[:4],
            ))
    moments.sort(key=lambda m: -len(m.lost_students))
    return moments[:limit]


def _fix(session: Session, moment: LostMoment) -> MomentFix:
    payload = {"course": session.course, "moment": moment.model_dump(), "slide": _slide(session, moment.slide_index)}

    def propose(name: str) -> FixProposal:
        system = (f"You are the {name}. A lecturer lost some students at this moment. {FIXERS[name]} "
                  f"Write the fix so the lecturer can use it directly. Set agent=\"{name}\".")
        return ask(name, "coach", system, payload, FixProposal, lambda: mock.fix(name, moment))

    with ThreadPoolExecutor(max_workers=len(FIXERS)) as pool:
        proposals = list(pool.map(propose, FIXERS))
    selection = ask("Fix Evaluator", "coach", FIX_EVALUATOR_SYSTEM,
                    {**payload, "proposals": [p.model_dump() for p in proposals]}, FixSelection,
                    lambda: mock.select(proposals))
    return MomentFix(moment=moment, proposals=proposals, selection=selection)


def report(session: Session, max_fixes: int = 2) -> RehearsalReport:
    journeys = []
    for p in PERSONAS:
        history = [next(s for s in c["result"].students if s.id == p["id"]) for c in session.chunks]
        journeys.append(StudentJourney(
            id=p["id"], name=p["name"],
            attention=[s.attention for s in history], confusion=[s.confusion for s in history],
            lost_at_chunks=[i for i, s in enumerate(history) if is_lost(s.model_dump())],
        ))
    moments = _lost_moments(session, max_fixes)
    with ThreadPoolExecutor(max_workers=max(1, len(moments))) as pool:
        fixes = list(pool.map(lambda m: _fix(session, m), moments))
    coach = ask("Coach", "coach", COACH_SYSTEM, {
        "course": session.course,
        "transcript": [{"chunk": i, "slide": c["slide_index"], "text": c["text"], "summary": c["result"].summary,
                        "class_attention": c["result"].class_attention, "class_confusion": c["result"].class_confusion}
                       for i, c in enumerate(session.chunks)],
        "journeys": [j.model_dump() for j in journeys],
        "lost_moments": [m.model_dump() for m in moments],
    }, CoachSummary, lambda: mock.coach(moments))
    return RehearsalReport(coach=coach, journeys=journeys, lost_moments=moments, fixes=fixes)
