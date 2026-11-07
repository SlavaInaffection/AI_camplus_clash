"""Turn an uploaded PDF / PPTX / plain text into a list of slides."""

import io
import re

from .schemas import Slide


def _title(text: str, index: int) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first[:80] or f"Slide {index + 1}"


def from_pdf(data: bytes) -> list[Slide]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    slides = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        slides.append(Slide(index=i, title=_title(text, i), text=text))
    return slides


def from_pptx(data: bytes) -> list[Slide]:
    from pptx import Presentation

    prs = Presentation(io.BytesIO(data))
    slides = []
    for i, s in enumerate(prs.slides):
        parts = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
        on_slide = "\n".join(parts).strip()
        title = _title(on_slide, i)  # from what is on the slide, never from the notes
        if not on_slide:
            parts.append(title)  # keep "title on the first line" true for the frontend
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
            parts.append("Speaker notes: " + s.notes_slide.notes_text_frame.text)
        slides.append(Slide(index=i, title=title, text="\n".join(parts).strip()))
    return slides


def from_text(text: str) -> list[Slide]:
    """Slides separated by a line containing only '---', or by two blank lines."""
    chunks = re.split(r"\n\s*---+\s*\n|\n\s*\n\s*\n", text.strip())
    return [Slide(index=i, title=_title(c, i), text=c.strip()) for i, c in enumerate(chunks) if c.strip()]


def load(filename: str, data: bytes) -> list[Slide]:
    name = filename.lower()
    if name.endswith(".pdf"):
        return from_pdf(data)
    if name.endswith(".pptx"):
        return from_pptx(data)
    return from_text(data.decode("utf-8", errors="replace"))
