"""Rehearsal Room API.

Run:   .venv/bin/uvicorn server:app --reload --port 8000
Docs:  http://localhost:8000/docs
"""

import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rehearsal import analysis, classroom, render, slides, voice
from rehearsal.llm import MOCK, MODELS, AgentError
from rehearsal.personas import BY_ID, PERSONAS
from rehearsal.schemas import ChunkResult, LectureAnalysis, RehearsalReport

app = FastAPI(title="Rehearsal Room", description="A flight simulator for teaching: 15 AI students react to your lecture.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AgentError)
def agent_error(_, exc: AgentError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def _session(session_id: str) -> classroom.Session:
    if session_id not in classroom.SESSIONS:
        raise HTTPException(404, f"No session {session_id}")
    return classroom.SESSIONS[session_id]


@app.get("/api/health")
def health():
    return {"ok": True, "mock": MOCK, "models": MODELS}


@app.get("/api/personas")
def personas():
    return PERSONAS


@app.post("/api/sessions")
async def create_session(
    course: str = Form("Untitled course"),
    slides_text: Optional[str] = Form(None, description="Plain text, slides separated by a line '---'"),
    file: Optional[UploadFile] = File(None, description="PDF, PPTX or .txt"),
):
    """Create a rehearsal. Slides are optional: you can rehearse with speech only."""
    deck, upload = [], None
    if file is not None and file.filename:
        upload = (file.filename, await file.read())
        deck = slides.load(*upload)
    elif slides_text:
        deck = slides.from_text(slides_text)
    session = classroom.Session(course, deck)
    classroom.SESSIONS[session.id] = session
    if upload and upload[0].lower().endswith((".pdf", ".pptx")):
        # rendering real slide images can take a while (Keynote/LibreOffice): do it in the background
        session.render_status = "rendering"
        threading.Thread(target=_render_slides, args=(session, *upload), daemon=True).start()
    return session.public()


def _render_slides(session: classroom.Session, filename: str, data: bytes) -> None:
    try:
        session.images = render.render(filename, data)
        session.render_status = "ready" if session.images else "failed"
    except Exception:
        session.render_status = "failed"


@app.get("/api/sessions/{session_id}/slides/{index}.png")
def slide_image(session_id: str, index: int):
    """The real slide, rendered from the uploaded PDF or PPTX."""
    session = _session(session_id)
    if not (0 <= index < len(session.images)):
        raise HTTPException(404, "No image for this slide (yet)")
    return FileResponse(session.images[index], media_type="image/png")


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return _session(session_id).public()


@app.post("/api/sessions/{session_id}/analyze", response_model=LectureAnalysis)
def analyze(session_id: str):
    """Before the lecture: 4 learning-science analysts review the slides in parallel."""
    session = _session(session_id)
    if not session.slides:
        raise HTTPException(400, "This session has no slides to analyse")
    session.analysis = analysis.analyze(session.slides, session.course)
    return session.analysis


class ChunkIn(BaseModel):
    text: str
    slide_index: Optional[int] = None


@app.post("/api/sessions/{session_id}/chunk", response_model=ChunkResult)
def chunk(session_id: str, body: ChunkIn):
    """Send ~10 seconds of transcript. Returns the new state of all 15 students and who speaks up."""
    if not body.text.strip():
        raise HTTPException(400, "Empty transcript chunk")
    return classroom.process_chunk(_session(session_id), body.text.strip(), body.slide_index)


@app.post("/api/sessions/{session_id}/report", response_model=RehearsalReport)
def report(session_id: str):
    """After the lecture: who you lost and when, plus multi-agent fixes for the worst moments."""
    session = _session(session_id)
    if not session.chunks:
        raise HTTPException(400, "Nothing rehearsed yet")
    return classroom.report(session)


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(..., description="A short recording, e.g. 10 s of webm/opus from MediaRecorder"),
    session_id: Optional[str] = Form(None, description="If given, course + current slide are used as a spelling hint"),
    slide_index: Optional[int] = Form(None),
    language: Optional[str] = Form(None, description="ISO code like 'en' or 'it'; omit to auto-detect"),
):
    """Voice in: lecturer speech -> text. Send the text on to /chunk."""
    context = ""
    if session_id in classroom.SESSIONS:
        s = classroom.SESSIONS[session_id]
        context = s.course
        if slide_index is not None and 0 <= slide_index < len(s.slides):
            context += "\n" + s.slides[slide_index].text
    try:
        text = voice.transcribe(await audio.read(), audio.filename or "audio.webm", language, context)
    except Exception as e:
        raise AgentError(f"Transcription: {type(e).__name__}: {e}") from e
    return {"text": text}


class SpeakIn(BaseModel):
    student_id: int
    text: str


@app.post("/api/speak", responses={200: {"content": {"audio/mpeg": {}}}, 204: {"description": "Mock mode: use browser speech"}})
def speak(body: SpeakIn):
    """Voice out: a student says their line in their own voice (MP3)."""
    if body.student_id not in BY_ID:
        raise HTTPException(404, f"No student {body.student_id}")
    try:
        audio = voice.speak(body.student_id, body.text)
    except Exception as e:
        raise AgentError(f"Speech: {type(e).__name__}: {e}") from e
    if audio is None:
        return Response(status_code=204)
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/sessions/{session_id}/reset")
def reset(session_id: str):
    """Restart the rehearsal with the same slides and analysis."""
    session = _session(session_id)
    session.states = classroom.initial_states()
    session.chunks = []
    return session.public()


# Serve the 3D classroom if someone builds it in ./frontend (index.html)
FRONTEND = Path(__file__).parent / "frontend"
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
