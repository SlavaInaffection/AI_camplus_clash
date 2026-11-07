"""Turn an uploaded deck into one PNG per slide, so the app shows the real slides.

PDF  -> pages rendered with pypdfium2.
PPTX -> PDF first with LibreOffice (headless, like web apps do it), or Keynote on macOS as a fallback, then as above.

Keynote is sandboxed and cannot open files under /tmp, so work happens in <repo>/.cache/slides.
"""

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

RENDER_ROOT = Path(__file__).resolve().parent.parent / ".cache" / "slides"
WIDTH = 1600  # px of the rendered slide images


def _find_soffice() -> Optional[str]:
    for candidate in (shutil.which("soffice"), shutil.which("libreoffice"),
                      "/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/bin/soffice"):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _pptx_to_pdf(src: Path, out_dir: Path) -> Optional[Path]:
    soffice = _find_soffice()
    if soffice:
        # its own profile dir, so conversions never clash with each other or an open LibreOffice window
        profile = (out_dir / "lo-profile").as_uri()
        r = subprocess.run([soffice, f"-env:UserInstallation={profile}", "--headless", "--convert-to", "pdf",
                            "--outdir", str(out_dir), str(src)], check=False, timeout=180, capture_output=True, text=True)
        pdf = out_dir / (src.stem + ".pdf")
        if pdf.exists():
            return pdf
        (out_dir / "libreoffice-error.txt").write_text(f"exit {r.returncode}\n{r.stdout}\n{r.stderr}")

    if Path("/Applications/Keynote.app").exists():
        pdf = out_dir / (src.stem + ".pdf")
        script = f'''
        tell application "Keynote"
            open POSIX file "{src}"
            set waited to 0
            repeat until (count of documents) > 0 or waited > 120
                delay 0.5
                set waited to waited + 1
            end repeat
            set d to front document
            export d to POSIX file "{pdf}" as PDF
            close d saving no
        end tell'''
        r = subprocess.run(["osascript", "-e", script], check=False, timeout=240, capture_output=True, text=True)
        if not pdf.exists():
            (out_dir / "keynote-error.txt").write_text(f"exit {r.returncode}\n{r.stderr}")
        return pdf if pdf.exists() else None

    return None


def _pdf_to_pngs(pdf: Path, out_dir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    paths = []
    for i, page in enumerate(doc):
        w, _ = page.get_size()
        image = page.render(scale=WIDTH / w).to_pil()
        path = out_dir / f"slide-{i}.png"
        image.save(path, optimize=True)
        paths.append(path)
    doc.close()
    return paths


def render(filename: str, data: bytes) -> list[Path]:
    """Returns the PNG paths in slide order, or [] if this kind of file cannot be rendered here."""
    name = filename.lower()
    if not (name.endswith(".pdf") or name.endswith(".pptx")):
        return []
    out_dir = RENDER_ROOT / uuid.uuid4().hex[:10]
    out_dir.mkdir(parents=True, exist_ok=True)
    src = out_dir / ("deck.pdf" if name.endswith(".pdf") else "deck.pptx")
    src.write_bytes(data)
    pdf = src if name.endswith(".pdf") else _pptx_to_pdf(src, out_dir)
    return _pdf_to_pngs(pdf, out_dir) if pdf else []
