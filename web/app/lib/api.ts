// Thin client for the FastAPI backend, proxied by Next at /api (see next.config.ts).

import type { Analysis, ChunkResult, Persona, Report, Session } from "./types";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, init);
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
});

export const api = {
  health: () => call<{ ok: boolean; mock: boolean; models: Record<string, string> }>("/health"),
  personas: () => call<Persona[]>("/personas"),

  createSession(course: string, slidesText: string, file?: File | null) {
    const fd = new FormData();
    fd.append("course", course);
    if (file) fd.append("file", file, file.name);
    else if (slidesText.trim()) fd.append("slides_text", slidesText);
    return call<Session>("/sessions", { method: "POST", body: fd });
  },
  analyze: (id: string) => call<Analysis>(`/sessions/${id}/analyze`, { method: "POST" }),
  chunk: (id: string, text: string, slideIndex: number | null) => call<ChunkResult>(`/sessions/${id}/chunk`, json({ text, slide_index: slideIndex })),
  report: (id: string) => call<Report>(`/sessions/${id}/report`, { method: "POST" }),
  reset: (id: string) => call<Session>(`/sessions/${id}/reset`, { method: "POST" }),

  transcribe(audio: Blob, sessionId: string, slideIndex: number | null) {
    const fd = new FormData();
    fd.append("audio", audio, "chunk.webm");
    fd.append("session_id", sessionId);
    if (slideIndex !== null) fd.append("slide_index", String(slideIndex));
    return call<{ text: string }>("/transcribe", { method: "POST", body: fd });
  },

  /** MP3 in the student's own voice, or null in mock mode (use browser speech instead). */
  async speak(studentId: number, text: string): Promise<Blob | null> {
    const r = await fetch("/api/speak", json({ student_id: studentId, text }));
    if (r.status === 204) return null;
    if (!r.ok) throw new Error(`speak: ${r.status}`);
    return r.blob();
  },
};
