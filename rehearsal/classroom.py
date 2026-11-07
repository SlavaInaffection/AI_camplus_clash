"""During and after the rehearsal.

Live loop, per transcript chunk:
  Director (1 call)  -> updates all 15 students + picks 0-2 speakers
  Student agents (parallel, only the speakers) -> what they say out loud
After:
  lost moments (computed) -> 3 Fix agents in parallel -> Fix Evaluator -> Coach summary
"""

import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from . import mock
from .llm import ask
from .personas import BY_ID, PERSONAS, initial_states
from .schemas import (
    ChunkResult, CoachSummary, DirectorTurn, FixProposal, FixSelection, LectureAnalysis, LostMoment, MomentFix,
    RehearsalReport, Slide, Speaker, SpeakerPick, StudentJourney, StudentLine, StudentState,
)

RECENT_CHUNKS = 3
LOST_STATES = {"lost", "sleeping", "on_phone"}
# Live classroom: mostly silent reactions. Chunks are ~4s, so cooldowns are in chunk counts.
MIN_CHUNKS_BETWEEN_SPEAKERS = 6   # ~24s between any questions
MIN_CHUNKS_SAME_STUDENT = 12      # ~48s before the same student speaks again
# Riccardo (id 14) is the "confident asker" — hard-cap him harder than the prompt alone.
RICCARDO_ID = 14
MIN_CHUNKS_RICCARDO = 18          # ~72s — stops him monopolizing Q&A
CHEN_ID = 6                       # shy — almost never the public asker
MIN_CHUNKS_CHEN = 20
INVITE_RE = re.compile(
    r"\b(any questions|questions\??|ask(?:\s+me)?|speak up|raise (?:your )?hand|"
    r"does that make sense|is that clear|before we move on)\b",
    re.I,
)


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
        self.images: list = []  # Path per slide, filled in the background for PDF/PPTX uploads
        self.render_status = "none"  # none | rendering | ready | failed
        self.last_speaker_chunk: Optional[int] = None
        self.last_spoke_at: dict[int, int] = {}  # student_id -> chunk_index

    def public(self) -> dict:
        return {
            "id": self.id, "course": self.course, "slides": [s.model_dump() for s in self.slides],
            "analysis": self.analysis.model_dump() if self.analysis else None,
            "students": self.states, "chunks": len(self.chunks),
            "render_status": self.render_status, "slide_images": len(self.images),
        }


SESSIONS: dict[str, Session] = {}


# --- Director ---------------------------------------------------------------

DIRECTOR_SYSTEM = """You are the Director of a simulated university classroom used by lecturers to rehearse.
You receive a compact class roster, current states, optional slide context, recent speakers, and a short transcript chunk.

Keep the room CALM. A real lecture is mostly quiet faces — listening, nodding, taking notes.
Do NOT paint half the class as confused. At most ONE or TWO students may be "confused"; everyone else
stays listening / taking_notes / nodding unless something is clearly catastrophic.
"lost" / "sleeping" / "on_phone" should be rare. Prefer small attention/confusion drifts over dramatic states.

Most chunks have ZERO speakers. Not a Q&A show.

Update EVERY student:
- Changes are gradual (usually within +/-15 per chunk).
- "reason" = max 12 words, learning-science grounded.
- Good teaching moves bring people back toward listening/nodding.
- Speakers: default []. At most ONE.
  Speak ONLY when: (a) the lecturer invites questions, OR (b) one student is badly stuck on what was just said.
- ROTATE speakers. Prefer someone in "prefer_speakers" who has not spoken recently.
  NEVER default to Chen or Riccardo. Chen almost never speaks in public (rare whisper at most).
- If someone speaks, "says" = one short natural sentence about the last thing said.
- bubble matches state.
React only to the transcript; do not invent what the lecturer said."""


def _roster_compact() -> list[dict]:
    """Omit voice metadata from the live loop — tokens without payoff for the Director."""
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "situation": p["situation"],
            "knowledge": p["knowledge"],
            "loses_focus_when": p["loses_focus_when"],
        }
        for p in PERSONAS
    ]


def _slide(session: Session, slide_index: Optional[int]) -> Optional[dict]:
    if slide_index is None or not (0 <= slide_index < len(session.slides)):
        return None
    slide = session.slides[slide_index].model_dump()
    if session.analysis:
        # Keep only the hottest predicted issues for this slide (token budget).
        issues = [i.model_dump() for i in session.analysis.issues if i.slide_index == slide_index]
        issues.sort(key=lambda i: -i.get("severity", 0))
        slide["predicted_issues"] = issues[:2]
    return slide


def _prefer_speakers(session: Session) -> list[int]:
    """Students who have spoken least so far — used to break Chen/Riccardo monopolies."""
    counts = {p["id"]: 0 for p in PERSONAS}
    for c in session.chunks:
        for sp in c["result"].speakers:
            if sp.id in counts:
                counts[sp.id] += 1
    ranked = sorted(counts.keys(), key=lambda i: (counts[i], i))
    return [i for i in ranked if i != CHEN_ID][:6]


def _temper_reactions(prev: list[dict], students: list[StudentState]) -> list[StudentState]:
    """Keep the room from looking like a panic — most faces stay calm."""
    by_old = {s["id"]: s for s in prev}
    tempered: list[StudentState] = []
    for s in students:
        old = by_old.get(s.id, {})
        # Slow confusion spikes
        old_c = int(old.get("confusion", 10))
        if s.confusion > old_c + 12:
            s.confusion = old_c + 12
        # Don't mark confused unless confusion is actually high
        if s.state == "confused" and s.confusion < 55:
            s.state = "listening" if s.attention >= 50 else "bored"
        if s.state == "lost" and s.confusion < 75:
            s.state = "confused" if s.confusion >= 55 else "listening"
        # Soft default faces
        if s.state in ("excited",) and s.attention < 85:
            s.state = "nodding"
        tempered.append(s)

    dramatic = [s for s in tempered if s.state in ("confused", "lost", "sleeping", "on_phone")]
    dramatic.sort(key=lambda s: (-s.confusion, s.id))
    keep = {s.id for s in dramatic[:2]}  # at most two stressed faces
    for s in tempered:
        if s.id not in keep and s.state in ("confused", "lost", "sleeping", "on_phone"):
            s.state = "listening"
            s.confusion = min(s.confusion, 40)
            s.bubble = "🙂"
        elif s.state == "confused":
            s.bubble = "🤔"
        elif s.state == "listening":
            s.bubble = "🙂"
        elif s.state == "nodding":
            s.bubble = "👍"
        elif s.state == "taking_notes":
            s.bubble = "📝"
    return tempered


def direct(session: Session, text: str, slide_index: Optional[int]) -> DirectorTurn:
    prefer = _prefer_speakers(session)
    payload = {
        "course": session.course,
        "roster": _roster_compact(),
        "current_states": [
            {k: s[k] for k in ("id", "attention", "confusion", "state", "bubble")} for s in session.states
        ],
        "slide": _slide(session, slide_index),
        "recent_transcript": [c["text"][:280] for c in session.chunks[-RECENT_CHUNKS:]],
        "new_chunk": text[:500],
        "chunk_index": len(session.chunks),
        "prefer_speakers": prefer,
        "recent_speakers": [
            {"id": sid, "chunk": at} for sid, at in sorted(session.last_spoke_at.items(), key=lambda x: -x[1])[:5]
        ],
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
            if len(new.reason) > 80:
                new.reason = new.reason[:77] + "…"
            merged.append(new)
        else:
            merged.append(StudentState(**old))
    turn.students = _temper_reactions(session.states, merged)
    turn.speakers = _filter_speakers(
        session, [sp for sp in turn.speakers if sp.id in BY_ID][:1], text, prefer
    )
    return turn


def _filter_speakers(session: Session, speakers: list, transcript: str, prefer: list[int]) -> list:
    """Hard rate-limits + rotation so one shy student does not become the class voice."""
    if not speakers:
        return []
    chunk_i = len(session.chunks)
    invited = bool(INVITE_RE.search(transcript))
    min_gap = 2 if invited else MIN_CHUNKS_BETWEEN_SPEAKERS
    if session.last_speaker_chunk is not None and chunk_i - session.last_speaker_chunk < min_gap:
        return []

    def cooldown_for(sid: int) -> int:
        if sid == RICCARDO_ID:
            return MIN_CHUNKS_RICCARDO
        if sid == CHEN_ID:
            return MIN_CHUNKS_CHEN
        return MIN_CHUNKS_SAME_STUDENT

    kept = []
    for sp in speakers:
        last = session.last_spoke_at.get(sp.id)
        if last is not None and chunk_i - last < cooldown_for(sp.id):
            continue
        # Chen: public hand-raises are off; rare whisper only
        if sp.id == CHEN_ID:
            if sp.action != "whisper_to_neighbour":
                continue
            sp.action = "whisper_to_neighbour"
        kept.append(sp)

    if not kept and speakers and prefer:
        # Model picked someone on cooldown — try redirecting the line to a preferred classmate
        original = speakers[0]
        for pid in prefer:
            last = session.last_spoke_at.get(pid)
            if last is not None and chunk_i - last < cooldown_for(pid):
                continue
            if pid == CHEN_ID:
                continue
            kept = [SpeakerPick(
                id=pid,
                action="raise_hand" if original.action != "whisper_to_neighbour" else "whisper_to_neighbour",
                intent=original.intent,
                says=original.says,
            )]
            break
    return kept[:1]


# --- Student agents (optional; live loop uses Director.says to stay fast) ---

def _student_system(persona: dict) -> str:
    return f"""You are {persona['name']}, a university student in a lecture.
Your situation: {persona['situation']}
Background: {persona['knowledge']}. You lose focus when: {persona['loses_focus_when']}.
Say ONE short, natural thing out loud (or whispered, if that is your action) that a real student in your state
would say right now: a question, a request to slow down or repeat, a challenge, or a comment.
Speak in the same language the lecturer is using, at your own language level. Be specific to what was just said."""


def speak(session: Session, turn: DirectorTurn, text: str, slide_index: Optional[int]) -> list[Speaker]:
    """Optional second pass for richer dialogue. Off by default in the live path."""
    if os.environ.get("LIVE_STUDENT_AGENTS", "0") != "1":
        states = {s.id: s for s in turn.students}
        return [
            Speaker(
                id=sp.id,
                action=sp.action,
                says=(sp.says or sp.intent).strip(),
                why=states[sp.id].reason,
            )
            for sp in turn.speakers
            if (sp.says or sp.intent).strip()
        ]

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
    if speakers:
        session.last_speaker_chunk = result.chunk_index
        for sp in speakers:
            session.last_spoke_at[sp.id] = result.chunk_index
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
