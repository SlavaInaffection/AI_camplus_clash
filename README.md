# 🎭 Rehearsal Room

**A flight simulator for teaching (and presentation rehearsal).**  
You teach your slides to a live class of **10 AI students**. Each one has a real situation (Erasmus listener, dyslexia, missed last week, misconception, …). They react, sometimes ask, and afterwards you see who you lost — and how to fix it.

> Predictions from learning-science principles — not measurements of real students.

**Hackathon:** Student Tech Clash 2026 · AI on Campus · **Coding path**  
**Level 2 map for judges:** [LEVEL2.md](./LEVEL2.md)

---

## Demo for judges

| What | URL / path |
|------|------------|
| **Interactive classroom** | http://localhost:3000 |
| **API docs** | http://localhost:8000/docs |
| **Example interactions (+ boundary)** | [examples/interactions.md](./examples/interactions.md) |
| **Architecture** | [§ Architecture](#architecture) below |

```bash
# API
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # set OPENAI_API_KEY, or REHEARSAL_MOCK=1
.venv/bin/uvicorn server:app --reload --port 8000

# UI (separate terminal)
cd web && npm install && npm run dev
```

Optional: `brew install --cask libreoffice` so uploaded **PPTX** renders as real slide images (PDF works without it).

---

## Architecture

```
INPUT
  mic / typed transcript  (+ optional PDF·PPTX·text slides)
       │
       ▼
GUARDRAILS (code) ────────────────────────────────────────────┐
  cheat · admin/logistics · jailbreak · harm → boundary_held   │
       │ (only if allowed)                                     │
       ▼                                                       │
KNOWLEDGE                                                      │
  course · cleaned slide text · 10 personas · prior states     │
  · optional pre-analysis (4 learning-science analysts)        │
       │                                                       │
       ▼                                                       │
ORCHESTRATOR = Director (1 LLM call / chunk)                   │
  plan → update every student → pick 0–1 speaker               │
  tools: none external; memory = session states + chunk log    │
       │                                                       │
       ▼                                                       │
DECISIONS                                                      │
  attention / confusion / state per student                    │
  rare grounded question (rotated; Chen rarely public)         │
       │                                                       │
       ▼                                                       │
OUTPUT                                                         │
  /chunk JSON → Next.js classroom (faces, !, TTS)              │
  /report → lost moments · fix agents · coach                  │
  logs/trace.jsonl ← every agent step                          │
       ▲                                                       │
       └──────────── refused requests jump here with           │
                     boundary_held (no LLM, class unchanged) ──┘
```

**Minimum “real agent” stack:** orchestrator (Director) + LLM + tools/guardrails (code) + memory (session JSON).

### Models & libraries

| Role | Default model | When |
|------|---------------|------|
| Director (live) | `gpt-4.1-mini` | Every ~4s transcript chunk |
| Analysts | `gpt-4.1` | Optional pre-lecture slide review |
| Coach / fixers | `gpt-4.1` | Post-rehearsal report |
| STT | `gpt-4o-mini-transcribe` | Mic chunks |
| TTS | `gpt-4o-mini-tts` | Student speech |

Configured via `.env` (see `.env.example`).  
**Libraries:** FastAPI, OpenAI SDK, Pydantic, pypdf, python-pptx, Next.js 16 / React 19.

### Custom logic (not “just a chatbot”)

- **Personas + seats** — [`rehearsal/personas.py`](./rehearsal/personas.py)  
- **Director + cooldowns + calm tempering** — [`rehearsal/classroom.py`](./rehearsal/classroom.py)  
- **Guardrails (boundary)** — [`rehearsal/guardrails.py`](./rehearsal/guardrails.py)  
- **Slide text cleaner** — [`rehearsal/slides.py`](./rehearsal/slides.py)  
- **Slide image render** — [`rehearsal/render.py`](./rehearsal/render.py)  
- **UI live loop** — [`web/app/components/Classroom.tsx`](./web/app/components/Classroom.tsx)

---

## Agents (pipeline)

```
BEFORE   slides ──► 4 analysts (Attention · Load · Prerequisites · Memory) ──► risk / slide
DURING   transcript ──► guardrails ──► Director ──► 0–1 speaker (+ TTS)
AFTER    lost moments ──► 3 Fix agents ──► Fix Evaluator ──► Coach
```

---

## API (short)

| Method | Path | What |
|--------|------|------|
| GET | `/api/health` | `{ok, mock, models}` |
| GET | `/api/personas` | Class roster (10 students in the room) |
| POST | `/api/sessions` | `course` + optional `file` / `slides_text` |
| POST | `/api/sessions/{id}/analyze` | Pre-lecture analysts |
| POST | `/api/sessions/{id}/chunk` | Transcript → class update **or** `boundary_held` |
| POST | `/api/sessions/{id}/report` | Coach + fixes |
| POST | `/api/transcribe` | Audio → text |
| POST | `/api/speak` | Student line → MP3 |

Regenerate judge examples (mock, no API key):

```bash
REHEARSAL_MOCK=1 .venv/bin/python tools/demo_interactions.py
```

---

## Frontend

Animated classroom in `web/`: desks, states, hand-raise, voices, presentation panel, report.  
Next proxies `/api/*` → `http://localhost:8000` (`BACKEND_URL`).

Legacy voice grid: http://localhost:8000/voice-test.html
