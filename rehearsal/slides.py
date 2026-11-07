"""Turn an uploaded PDF / PPTX / plain text into a list of slides."""

import io
import re

from .schemas import Slide

_JUNK_LINE = re.compile(
    r"^(page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+|confidential|draft|"
    r"do not distribute|internal use only|copyright\b.*|\u00a9.*)$",
    re.I,
)
_BULLET_LEAD = re.compile(r"^([\-\*\u2013\u2014\u2022\u25cf\u25a0\u25aa\uf0b7▪◦]+)\s+")


def _title(text: str, index: int) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    # Prefer a real heading over a bullet
    if first.startswith("•"):
        first = first.lstrip("• ").strip()
    return first[:80] or f"Slide {index + 1}"


def clean_extracted_text(text: str) -> str:
    """Strip PDF/PPTX extraction junk and normalize for the presentation panel + agents."""
    if not text:
        return ""
    text = (
        text.replace("\u00ad", "")  # soft hyphen
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .replace("\t", " ")
    )
    # Common bullet glyphs → •
    for ch in ("\u2022", "\uf0b7", "\u25cf", "\u25aa", "\u25a0", "▪", "◦", ""):
        text = text.replace(ch, "•")
    # Rejoin words broken across lines with a hyphen
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Fix spaces before punctuation left by extractors
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r" +([,.;:!?])", r"\1", text)

    lines: list[str] = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t\f\v]+", " ", raw).strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if _JUNK_LINE.match(line):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        line = _BULLET_LEAD.sub("• ", line)
        # Drop exact consecutive duplicates (common with headers/footers)
        if lines and lines[-1] == line:
            continue
        lines.append(line)

    # Collapse runs of blank lines
    out: list[str] = []
    for line in lines:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)
    return "\n".join(out).strip()


def _split_notes(text: str) -> tuple[str, str]:
    marker = "Speaker notes:"
    i = text.find(marker)
    if i < 0:
        return text.strip(), ""
    return text[:i].strip(), text[i + len(marker) :].strip()


def _compose(main: str, notes: str) -> str:
    main = clean_extracted_text(main)
    notes = clean_extracted_text(notes)
    if notes:
        return f"{main}\n\nSpeaker notes: {notes}".strip() if main else f"Speaker notes: {notes}"
    return main


def from_pdf(data: bytes) -> list[Slide]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    slides = []
    for i, page in enumerate(reader.pages):
        text = clean_extracted_text(page.extract_text() or "")
        slides.append(Slide(index=i, title=_title(text, i), text=text))
    return slides


def _pptx_shape_lines(shape) -> list[str]:
    if not shape.has_text_frame:
        return []
    lines = []
    for p in shape.text_frame.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        level = getattr(p, "level", 0) or 0
        if level > 0:
            lines.append(("  " * level) + "• " + _BULLET_LEAD.sub("", t))
        elif _BULLET_LEAD.match(t) or t.startswith("•"):
            lines.append("• " + _BULLET_LEAD.sub("", t).lstrip("• ").strip())
        else:
            lines.append(t)
    return lines


def from_pptx(data: bytes) -> list[Slide]:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(io.BytesIO(data))
    slides = []
    for i, s in enumerate(prs.slides):
        parts: list[str] = []
        for sh in s.shapes:
            if sh.has_text_frame:
                parts.extend(_pptx_shape_lines(sh))
            elif sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                for child in sh.shapes:
                    if child.has_text_frame:
                        parts.extend(_pptx_shape_lines(child))
        on_slide = clean_extracted_text("\n".join(parts))
        title = _title(on_slide, i)
        if not on_slide:
            on_slide = title
        notes = ""
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
            notes = s.notes_slide.notes_text_frame.text
        slides.append(Slide(index=i, title=title, text=_compose(on_slide, notes)))
    return slides


def from_text(text: str) -> list[Slide]:
    """Slides separated by a line containing only '---', or by two blank lines."""
    chunks = re.split(r"\n\s*---+\s*\n|\n\s*\n\s*\n", text.strip())
    slides = []
    for i, c in enumerate(chunks):
        main, notes = _split_notes(c)
        composed = _compose(main, notes)
        if not composed:
            continue
        slides.append(Slide(index=len(slides), title=_title(composed, i), text=composed))
    return slides


def load(filename: str, data: bytes) -> list[Slide]:
    name = filename.lower()
    if name.endswith(".pdf"):
        return from_pdf(data)
    if name.endswith(".pptx"):
        return from_pptx(data)
    return from_text(data.decode("utf-8", errors="replace"))
