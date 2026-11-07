# 🎭 Rehearsal Room

**A flight simulator for teaching.** A lecturer rehearses in front of 15 simulated students. Each one reacts according to their situation and to learning-science principles. They get lost, fall asleep, raise their hand and ask questions. Afterwards the lecturer sees who they lost, when, and why, plus fixes proposed and compared by several agents.

> These are predictions based on learning-science principles. They are not measurements of real students.

## Agents

```
BEFORE   slides ──► 4 analysts in parallel (Attention · Cognitive Load · Prerequisites · Memory) ──► risk per slide
DURING   transcript chunk ──► Director (updates all 15, picks 0-2 speakers) ──► Student agents (parallel) speak
AFTER    lost moments ──► 3 Fix agents (Example · Visual · Structure) ──► Fix Evaluator ──► Coach summary
```

Every agent step is logged to `logs/trace.jsonl`.

## Run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY, or set REHEARSAL_MOCK=1
.venv/bin/uvicorn server:app --reload --port 8000
```

Open http://localhost:8000/docs to try every endpoint.

**Mock mode:** without `OPENAI_API_KEY`, or with `REHEARSAL_MOCK=1`, every agent returns fake but changing data. Use it to build the frontend without spending tokens.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | `{ok, mock, models}` |
| GET | `/api/personas` | The 15 students: `id, name, emoji, seat:[row,col], situation, ...` |
| POST | `/api/sessions` | Form fields: `course`, plus either `file` (PDF/PPTX/TXT) or `slides_text` (slides separated by `---`). Both are optional. |
| POST | `/api/sessions/{id}/analyze` | Runs the slide analysis (the 4 analysts) |
| POST | `/api/sessions/{id}/chunk` | `{"text": "...", "slide_index": 2}`. Send about 10 seconds of transcript. Returns the classroom state. |
| POST | `/api/sessions/{id}/report` | Who you lost, when, and the fixes |
| POST | `/api/sessions/{id}/reset` | Start the rehearsal again with the same slides |

**Slides-only mode** (no microphone): send each slide's own text to `/chunk` with its `slide_index`.

### `/chunk` response: the contract the 3D classroom consumes

```json
{
  "chunk_index": 3,
  "slide_index": 1,
  "students": [
    {"id": 1, "attention": 55, "confusion": 70, "state": "confused", "bubble": "🤔",
     "reason": "Jargon 'type I error' never written down; B1 listener"}
  ],
  "speakers": [
    {"id": 1, "action": "raise_hand", "says": "Sorry, what is a type I error?", "why": "..."}
  ],
  "summary": "Introduced hypothesis testing terms",
  "class_attention": 62,
  "class_confusion": 41
}
```

`state` is one of: `listening, taking_notes, nodding, confused, lost, bored, sleeping, on_phone, excited, hand_raised`
`action` is one of: `raise_hand, interrupt, whisper_to_neighbour`

## Frontend (Next.js, `web/`)

The animated classroom: 15 students at desks, animated live from `/chunk`. Students raise their hand and speak in their own voice.

```bash
.venv/bin/uvicorn server:app --port 8000   # backend
cd web && npm install && npm run dev        # http://localhost:3000
```

Next proxies `/api/*` to the backend (`BACKEND_URL`, default `http://localhost:8000`). The **Demo** buttons (Raise a hand, Shuffle moods) work without starting a session.

- `web/app/components/Student.tsx`: one animated student. Arms, head and props transition between the 10 states.
- `web/app/components/Classroom.tsx`: the room, the mic loop, the voices and the report.

## Static test page

Put the 3D classroom in `frontend/index.html`. The server serves it at `/` automatically, so there are no CORS issues (CORS is open anyway).
