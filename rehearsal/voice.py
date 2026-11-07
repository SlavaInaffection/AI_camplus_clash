"""Voice in (lecturer speech -> text) and voice out (each student speaks with their own voice)."""

import os
from typing import Optional

from .llm import MOCK, _client
from .personas import BY_ID

TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
TTS_MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")


def transcribe(audio: bytes, filename: str, language: Optional[str] = None, context: str = "") -> str:
    """context: course name and slide text, so jargon like 'p-value' or 'H0' is spelled correctly."""
    if MOCK:
        return "[mock transcript] so the p-value is the probability of the data given the null hypothesis"
    kwargs = {}
    if language:
        kwargs["language"] = language
    if context:
        kwargs["prompt"] = context[:800]
    result = _client.audio.transcriptions.create(model=TRANSCRIBE_MODEL, file=(filename, audio), **kwargs)
    return result.text.strip()


def speak(student_id: int, text: str) -> Optional[bytes]:
    """MP3 bytes in the student's own voice. None in mock mode (frontend falls back to browser speech)."""
    if MOCK:
        return None
    persona = BY_ID[student_id]
    response = _client.audio.speech.create(
        model=TTS_MODEL,
        voice=persona["voice"],
        input=text,
        instructions=f"You are a university student speaking up in class. {persona['voice_style']} Sound natural, like a real student, not a narrator.",
        response_format="mp3",
    )
    return response.content
