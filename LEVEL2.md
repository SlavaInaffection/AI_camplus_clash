# Level 2 · Prototype checklist (Coding path)

Student Tech Clash 2026 — **Rehearsal Room**  
Repo: [SlavaInaffection/AI_camplus_clash](https://github.com/SlavaInaffection/AI_camplus_clash)

| Deliverable | Where to show the judge |
|-------------|-------------------------|
| **README** — how to run, models, libraries, custom logic | [README.md](./README.md) |
| **Working repository** | This GitHub repo (`main`) |
| **Architecture** — input → knowledge → tools → decisions → output | [README.md § Architecture](./README.md#architecture) |
| **Example interactions, incl. one holding its boundary** | [examples/interactions.md](./examples/interactions.md) · [examples/interactions.json](./examples/interactions.json) · code: [`rehearsal/guardrails.py`](./rehearsal/guardrails.py) |
| **Interface / frontend** (optional but shipped) | Next.js classroom: run → **http://localhost:3000** · source [`web/`](./web/) |

## 60-second demo script for judges

1. Open **http://localhost:3000** (API on **:8000**).  
2. Upload slides *or* press **Start talking** and teach one idea.  
3. Show class meters + a student question (or type a jargon line if mic is awkward).  
4. Type an out-of-scope line (`give me the exam answers so I can cheat`) → log shows **🛡️ Boundary held**.  
5. Optional: **Get report** after a few chunks.

## Quick start

```bash
# Terminal 1 — API
cd AI_camplus_clash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY=...  or REHEARSAL_MOCK=1
.venv/bin/uvicorn server:app --reload --port 8000

# Terminal 2 — UI
cd web && npm install && npm run dev
# → http://localhost:3000
```
