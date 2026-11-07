"""Before the lecture: four learning-science analysts read the slides in parallel."""

from concurrent.futures import ThreadPoolExecutor

from . import mock
from .llm import ask
from .schemas import AnalystReport, LectureAnalysis, Slide, SlideRisk

ANALYSTS = {
    "attention": (
        "Attention Analyst",
        "Predict where students will focus or drift. Use: signalling/cueing, novelty and change of pace, "
        "the ~10-minute attention decline, seductive details, and whether the slide motivates WHY the topic matters.",
    ),
    "cognitive_load": (
        "Cognitive Load Analyst",
        "Predict where working memory will be overloaded. Use cognitive load theory: number of new interacting elements, "
        "split-attention, redundancy (reading text while listening to the same text), modality, missing worked examples.",
    ),
    "prerequisites": (
        "Prerequisite Analyst",
        "Find comprehension barriers: concepts, notation or jargon used before they are defined, assumed prior knowledge, "
        "big jumps in abstraction, and common misconceptions the slide will collide with.",
    ),
    "memory": (
        "Memory Analyst",
        "Predict what will be hard to encode and retain. Use: elaboration and concrete examples, dual coding, "
        "chunking, retrieval practice opportunities, spacing, and links to what students already know.",
    ),
}


def _system(name: str, focus: str, dimension: str) -> str:
    return f"""You are the {name} in a team that reviews university lecture slides before they are taught.
{focus}
Report only real, specific issues (0-3 per slide, most slides have 0-1). For each, name the principle and give
one concrete, evidence-informed fix the professor can apply. Set dimension="{dimension}" on the report and on every issue.
These are predictions about likely difficulty, not claims about real students."""


def analyze(slides: list[Slide], course: str) -> LectureAnalysis:
    payload = {"course": course, "slides": [s.model_dump() for s in slides]}

    def run(dimension: str) -> AnalystReport:
        name, focus = ANALYSTS[dimension]
        return ask(name, "analyst", _system(name, focus, dimension), payload, AnalystReport,
                   lambda: mock.analyst(dimension, slides))

    with ThreadPoolExecutor(max_workers=len(ANALYSTS)) as pool:
        reports = list(pool.map(run, ANALYSTS))

    issues = [i for r in reports for i in r.issues if 0 <= i.slide_index < len(slides)]
    risks = []
    for s in slides:
        mine = sorted((i for i in issues if i.slide_index == s.index), key=lambda i: -i.severity)
        # 12 = four dimensions at max severity 3; more than that still caps at 100
        risk = min(100, round(sum(i.severity for i in mine) / 12 * 100))
        risks.append(SlideRisk(index=s.index, title=s.title, risk=risk, top_issue=mine[0].problem if mine else None))
    return LectureAnalysis(slides=risks, issues=issues, overall={r.dimension: r.overall for r in reports})
