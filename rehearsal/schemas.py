"""Structured outputs exchanged between agents and returned by the API.

Ranges (0-100, 1-3) are stated in descriptions rather than validators so the schemas
stay compatible with strict structured-output mode.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Dimension = Literal["attention", "cognitive_load", "prerequisites", "memory"]

StudentStateName = Literal[
    "listening", "taking_notes", "nodding", "confused", "lost", "bored", "sleeping", "on_phone", "excited", "hand_raised"
]


# --- Slides -----------------------------------------------------------------

class Slide(BaseModel):
    index: int
    title: str
    text: str


# --- Pre-lecture analysis (cognitive-science analysts) ----------------------

class SlideIssue(BaseModel):
    slide_index: int
    dimension: Dimension
    severity: int = Field(description="1 = minor, 2 = notable, 3 = students will very likely struggle")
    problem: str = Field(description="What on this slide is likely to cause difficulty, concretely")
    principle: str = Field(description="The learning-science principle behind it, e.g. 'Cognitive load theory: too many interacting new elements'")
    suggestion: str = Field(description="A specific, evidence-informed change the professor could make")


class AnalystReport(BaseModel):
    dimension: Dimension
    issues: list[SlideIssue]
    overall: str = Field(description="One or two sentences on this dimension for the whole lecture")


class SlideRisk(BaseModel):
    index: int
    title: str
    risk: int = Field(description="0-100")
    top_issue: Optional[str]


class LectureAnalysis(BaseModel):
    slides: list[SlideRisk]
    issues: list[SlideIssue]
    overall: dict[str, str]
    disclaimer: str = "Predictions of likely cognitive difficulty based on learning-science principles, not measurements of real students."


# --- Live classroom (Director + student agents) ----------------------------

class StudentState(BaseModel):
    id: int
    attention: int = Field(description="0-100")
    confusion: int = Field(description="0-100")
    state: StudentStateName
    bubble: str = Field(description="One emoji shown over the student's head")
    reason: str = Field(description="Short reason for the change, tied to the persona and a learning-science principle")


class SpeakerPick(BaseModel):
    id: int
    action: Literal["raise_hand", "interrupt", "whisper_to_neighbour"]
    intent: str = Field(description="What this student wants to say or ask, in a few words")
    says: str = Field(
        description="Exactly what they say out loud: one short natural sentence in the lecture language"
    )


class DirectorTurn(BaseModel):
    students: list[StudentState] = Field(description="Updated state for EVERY student in the class")
    speakers: list[SpeakerPick] = Field(description="0-1 students who speak up now. Usually empty.")
    chunk_summary: str = Field(description="One line: what the lecturer just explained")


class StudentLine(BaseModel):
    says: str = Field(description="Exactly what the student says out loud, 1-2 sentences, in their own voice")


class Speaker(BaseModel):
    id: int
    action: str
    says: str
    why: str


class ChunkResult(BaseModel):
    """The contract the 3D classroom consumes after every transcript chunk."""

    chunk_index: int
    slide_index: Optional[int]
    students: list[StudentState]
    speakers: list[Speaker]
    summary: str
    class_attention: int
    class_confusion: int
    # Set when input guardrails refuse the request (Level 2: holding the boundary).
    boundary_held: Optional[str] = None


# --- After the rehearsal ----------------------------------------------------

class FixProposal(BaseModel):
    agent: str
    approach: str = Field(description="The rewritten explanation or concrete change, ready to use")
    why_it_helps: str = Field(description="Which learning-science principle it relies on")
    who_it_helps: list[str] = Field(description="Names of the students it would bring back")
    risk: str


class FixSelection(BaseModel):
    chosen_agent: str
    final_fix: str = Field(description="The chosen fix, optionally merged with another proposal")
    reasoning: str


class CoachSummary(BaseModel):
    summary: str
    strengths: list[str]
    top_changes: list[str] = Field(description="The three changes that would help the most students, most important first")


class LostMoment(BaseModel):
    chunk_index: int
    slide_index: Optional[int]
    excerpt: str
    lost_students: list[str]
    reasons: list[str]


class StudentJourney(BaseModel):
    id: int
    name: str
    attention: list[int]
    confusion: list[int]
    lost_at_chunks: list[int]


class MomentFix(BaseModel):
    moment: LostMoment
    proposals: list[FixProposal]
    selection: FixSelection


class RehearsalReport(BaseModel):
    coach: CoachSummary
    journeys: list[StudentJourney]
    lost_moments: list[LostMoment]
    fixes: list[MomentFix]
