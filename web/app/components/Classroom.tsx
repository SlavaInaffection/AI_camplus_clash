"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import { LOOKS } from "../lib/characters";
import { STATES, type ChunkResult, type Persona, type Report, type Session, type StudentState, type StudentStateName } from "../lib/types";
import Student from "./Student";
import styles from "./Classroom.module.css";

const ROWS = [2, 1, 0]; // back row first (top of the screen), front row nearest the lectern
const ROW_SCALE: Record<number, number> = { 2: 0.8, 1: 0.9, 0: 1 };
const CHUNK_SECONDS = 10;

const DEFAULT_SLIDES = `Hypothesis testing
H0, H1, alpha, beta, type I error, type II error, power = 1 - beta, p-value
---
The p-value
P(T >= t_obs | H0). Reject H0 if p < alpha.
---
Example: is this coin fair?
100 flips, 62 heads.`;

const DEMO_QUESTIONS = [
  "Sorry, could you explain that last step with an example?",
  "Wait, what does alpha mean here?",
  "Can you slow down a bit? I didn't get the formula.",
  "Why is that true, though?",
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

type Speaking = { id: number; says: string; action: string } | null;

const initialStates = (): Record<number, StudentState> =>
  Object.fromEntries(LOOKS.map((l) => [l.id, { id: l.id, attention: 80, confusion: 10, state: "listening", bubble: "🙂", reason: "Start of lecture" }]));

export default function Classroom() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [backend, setBackend] = useState<"checking" | "live" | "mock" | "offline">("checking");
  const [students, setStudents] = useState<Record<number, StudentState>>(initialStates);
  const [speaking, setSpeaking] = useState<Speaking>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [course, setCourse] = useState("Intro to Statistics, first year");
  const [slidesText, setSlidesText] = useState(DEFAULT_SLIDES);
  const [slideIndex, setSlideIndex] = useState<number | null>(null);
  const [stats, setStats] = useState<{ attention: number; confusion: number; summary: string } | null>(null);
  const [recording, setRecording] = useState(false);
  const [typed, setTyped] = useState("");
  const [pending, setPending] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [setupOpen, setSetupOpen] = useState(false);
  const [logOpen, setLogOpen] = useState(false);

  const sessionRef = useRef<Session | null>(null);
  const slideRef = useRef<number | null>(null);
  const recordingRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);
  const chunkQueue = useRef<Promise<void>>(Promise.resolve());
  const speechQueue = useRef<Promise<void>>(Promise.resolve());
  const recordChunkRef = useRef<() => void>(() => {});
  useEffect(() => { sessionRef.current = session; }, [session]);
  useEffect(() => { slideRef.current = slideIndex; }, [slideIndex]);

  const note = useCallback((m: string) => setLog((l) => [`${new Date().toLocaleTimeString()}  ${m}`, ...l].slice(0, 60)), []);
  const nameOf = useCallback((id: number) => personas.find((p) => p.id === id)?.name ?? LOOKS[id].name, [personas]);

  useEffect(() => {
    api.personas().then(setPersonas).catch(() => {});
    api.health().then((h) => setBackend(h.mock ? "mock" : "live")).catch(() => setBackend("offline"));
  }, []);

  // --- voices: one student at a time, hand up and waving while they talk ---
  const say = useCallback((sp: { id: number; says: string; action: string }) => {
    speechQueue.current = speechQueue.current.then(async () => {
      // the hand goes up first, then they talk; the hand stays up at least a moment even if audio fails
      await sleep(700);
      setSpeaking(sp);
      const started = performance.now();
      try {
        const audio = backend === "offline" ? null : await api.speak(sp.id, sp.says).catch(() => null);
        await new Promise<void>((done) => {
          if (audio) {
            const a = new Audio(URL.createObjectURL(audio));
            a.onended = () => done(); a.onerror = () => done();
            a.play().catch(() => done());
          } else if ("speechSynthesis" in window) {
            const u = new SpeechSynthesisUtterance(sp.says);
            u.onend = () => done(); u.onerror = () => done();
            speechSynthesis.speak(u);
          } else setTimeout(done, 3000);
        });
      } finally {
        await sleep(Math.max(0, 2500 - (performance.now() - started)));
        setSpeaking(null);
        // after asking, the hand comes down
        setStudents((s) => s[sp.id]?.state === "hand_raised" ? { ...s, [sp.id]: { ...s[sp.id], state: "listening", bubble: "🙂" } } : s);
      }
    });
  }, [backend]);

  // --- applying a /chunk result ---
  const apply = useCallback((r: ChunkResult) => {
    setStudents((prev) => {
      const next = { ...prev };
      for (const s of r.students) next[s.id] = s;
      for (const sp of r.speakers) if (sp.action !== "whisper_to_neighbour") next[sp.id] = { ...next[sp.id], state: "hand_raised", bubble: "✋" };
      return next;
    });
    setStats({ attention: r.class_attention, confusion: r.class_confusion, summary: r.summary });
    for (const sp of r.speakers) {
      note(`🗣 ${nameOf(sp.id)} (${sp.action.replaceAll("_", " ")}): ${sp.says}`);
      say(sp);
    }
  }, [nameOf, note, say]);

  const sendChunk = useCallback((text: string) => {
    const s = sessionRef.current;
    if (!s) return;
    setPending((n) => n + 1);
    const slide = slideRef.current;
    chunkQueue.current = chunkQueue.current.then(async () => {
      try {
        const t = performance.now();
        const r = await api.chunk(s.id, text, slide);
        note(`chunk ${r.chunk_index} · ${((performance.now() - t) / 1000).toFixed(1)}s · ${r.summary}`);
        apply(r);
      } catch (e) {
        note(`⚠️ ${(e as Error).message}`);
      } finally {
        setPending((n) => n - 1);
      }
    });
  }, [apply, note]);

  // --- microphone: a fresh MediaRecorder per chunk so each blob is a complete file ---
  const recordChunk = useCallback(() => {
    if (!recordingRef.current || !streamRef.current) return;
    const rec = new MediaRecorder(streamRef.current, { mimeType: "audio/webm" });
    const parts: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && parts.push(e.data);
    rec.onstop = async () => {
      recordChunkRef.current(); // start the next chunk straight away
      const blob = new Blob(parts, { type: "audio/webm" });
      const s = sessionRef.current;
      if (blob.size < 2000 || !s) return;
      try {
        const { text } = await api.transcribe(blob, s.id, slideRef.current);
        note(`🎤 ${text || "(silence)"}`);
        if (text && text.split(/\s+/).length >= 3) sendChunk(text);
      } catch (e) {
        note(`⚠️ ${(e as Error).message}`);
      }
    };
    rec.start();
    setTimeout(() => rec.state === "recording" && rec.stop(), CHUNK_SECONDS * 1000);
  }, [note, sendChunk]);
  useEffect(() => { recordChunkRef.current = recordChunk; }, [recordChunk]);

  async function toggleMic() {
    if (recordingRef.current) {
      recordingRef.current = false;
      setRecording(false);
      return;
    }
    try {
      streamRef.current ??= await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingRef.current = true;
      setRecording(true);
      recordChunk();
    } catch {
      note("⚠️ Microphone permission was denied");
    }
  }

  async function start(): Promise<Session | null> {
    try {
      const s = await api.createSession(course, slidesText);
      sessionRef.current = s;
      slideRef.current = s.slides.length ? 0 : null;
      setSession(s);
      setStudents(initialStates());
      setSlideIndex(s.slides.length ? 0 : null);
      setReport(null);
      setStats(null);
      setSetupOpen(false);
      note(`Session ${s.id} · ${s.slides.length} slides`);
      if (s.slides.length) {
        note("Analysing slides…");
        api.analyze(s.id).then((a) => a.slides.forEach((x) => note(`slide ${x.index + 1} · risk ${x.risk} · ${x.top_issue ?? "ok"}`))).catch(() => {});
      }
      return s;
    } catch (e) {
      note(`⚠️ ${(e as Error).message}`);
      return null;
    }
  }

  /** The one big button: starts a session with the current setup if needed, then the mic. */
  async function startTalking() {
    if (!recordingRef.current && !sessionRef.current && !(await start())) return;
    await toggleMic();
  }

  async function getReport() {
    if (!session) return;
    setReportBusy(true);
    try {
      setReport(await api.report(session.id));
    } catch (e) {
      note(`⚠️ ${(e as Error).message}`);
    } finally {
      setReportBusy(false);
    }
  }

  async function resetClass() {
    if (!session) return;
    await api.reset(session.id).catch(() => {});
    setStudents(initialStates());
    setStats(null);
    setReport(null);
    note("Class reset");
  }

  // --- demo buttons: work without the backend ---
  function demoRaiseHand() {
    const candidates = LOOKS.filter((l) => students[l.id].state !== "hand_raised");
    const who = candidates[Math.floor(Math.random() * candidates.length)];
    setStudents((s) => ({ ...s, [who.id]: { ...s[who.id], state: "hand_raised", bubble: "✋" } }));
    say({ id: who.id, says: DEMO_QUESTIONS[Math.floor(Math.random() * DEMO_QUESTIONS.length)], action: "raise_hand" });
  }

  function demoShuffle() {
    const pool: StudentStateName[] = STATES.filter((s) => s !== "hand_raised");
    setStudents((s) => Object.fromEntries(Object.values(s).map((st) => [st.id, { ...st, state: pool[Math.floor(Math.random() * pool.length)] }])));
  }

  const seats = useMemo(() => {
    const byRow: Record<number, number[]> = { 0: [], 1: [], 2: [] };
    const seatOf = (id: number) => personas.find((p) => p.id === id)?.seat ?? [Math.floor(id / 5), id % 5];
    for (const l of LOOKS) byRow[seatOf(l.id)[0]].push(l.id);
    for (const r of ROWS) byRow[r].sort((a, b) => seatOf(a)[1] - seatOf(b)[1]);
    return byRow;
  }, [personas]);

  const slide = session && slideIndex !== null ? session.slides[slideIndex] : null;

  return (
    <div className={styles.page}>
      <header className={styles.top}>
        <div className={styles.brand}>
          <p className={styles.eyebrow}>Rehearsal Room</p>
          <h1 className={styles.title}>{session ? session.course : "A flight simulator for teaching"}</h1>
        </div>

        <button className={recording ? styles.talkOn : styles.talk} onClick={startTalking} aria-pressed={recording}
          disabled={backend === "offline" || backend === "checking"}>
          <span className={styles.dot} aria-hidden="true" />
          {recording ? "Stop talking" : "Start talking"}
        </button>

        <div className={styles.meters} aria-live="polite">
          <Meter label="Attention" value={stats?.attention ?? 80} tone="blue" />
          <Meter label="Confusion" value={stats?.confusion ?? 10} tone="pink" />
          {pending > 0 && <span className={styles.pending}>Class is reacting…</span>}
        </div>

        <div className={styles.tools}>
          {session && session.slides.length > 0 && (
            <label>
              <span className={styles.srOnly}>Current slide</span>
              <select value={slideIndex ?? ""} onChange={(e) => setSlideIndex(e.target.value === "" ? null : Number(e.target.value))}>
                {session.slides.map((sl) => <option key={sl.index} value={sl.index}>Slide {sl.index + 1}</option>)}
              </select>
            </label>
          )}
          {session && <button onClick={getReport} disabled={reportBusy}>{reportBusy ? "Building…" : "Report"}</button>}
          {session && <button onClick={resetClass}>Reset</button>}
          <button onClick={() => setSetupOpen(true)}>Setup</button>
          <button onClick={() => setLogOpen((o) => !o)} aria-pressed={logOpen}>Log</button>
          <span className={`${styles.badge} ${styles[backend]}`}>
            {backend === "live" ? "Live AI" : backend === "mock" ? "Mock" : backend === "offline" ? "Offline" : "…"}
          </span>
        </div>
      </header>

      <main className={styles.room}>
        <div className={styles.board}>
          <p className={styles.boardLabel}>{slide ? `Slide ${slide.index + 1} of ${session?.slides.length}` : "Whiteboard"}</p>
          <p className={styles.boardTitle}>{slide?.title ?? "Press Start talking and teach your class"}</p>
          {stats?.summary && <p className={styles.boardSummary}>{stats.summary}</p>}
        </div>

        <div className={styles.rows}>
          {ROWS.map((row) => (
            <div key={row} className={styles.row} style={{ ["--scale" as string]: ROW_SCALE[row] }}>
              {seats[row].map((id) => {
                const st = students[id];
                const talking = speaking?.id === id;
                return (
                  <div key={id} className={styles.seat} title={`${nameOf(id)} · ${st.state.replaceAll("_", " ")}\n${st.reason}`}>
                    {talking && (
                      <div className={`${styles.speech} ${speaking.action === "whisper_to_neighbour" ? styles.whisper : ""}`} role="status">
                        <span className={styles.speechWho}>{nameOf(id)} {speaking.action === "whisper_to_neighbour" ? "whispers" : "asks"}</span>
                        {speaking.says}
                      </div>
                    )}
                    <span key={st.bubble} className={styles.emoji} aria-hidden="true">{st.bubble}</span>
                    <div className={styles.figure}>
                      <Student id={id} state={st.state} waving={talking} />
                    </div>
                    <div className={styles.desk}>
                      <span className={styles.name}>{nameOf(id)}</span>
                      <span className={styles.bar} aria-label={`attention ${st.attention}`}>
                        <i style={{ width: `${st.attention}%` }} />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {session && (
          <form className={styles.typeBar} onSubmit={(e) => { e.preventDefault(); if (typed.trim()) { note(`⌨️ ${typed}`); sendChunk(typed); setTyped(""); } }}>
            <label className={styles.srOnly} htmlFor="typed">Say something to the class</label>
            <input id="typed" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="No mic? Type what you would say and press Enter" />
          </form>
        )}
      </main>

      {logOpen && (
        <aside className={styles.log} aria-label="Activity">
          <div className={styles.panelHead}>
            <h2>Activity</h2>
            <button className={styles.close} onClick={() => setLogOpen(false)} aria-label="Close activity log">×</button>
          </div>
          {log.length === 0 && <p>Nothing yet.</p>}
          {log.map((l, i) => <p key={log.length - i}>{l}</p>)}
        </aside>
      )}

      {setupOpen && (
        <div className={styles.backdrop} onClick={() => setSetupOpen(false)}>
          <div className={styles.dialog} role="dialog" aria-label="Setup" onClick={(e) => e.stopPropagation()}>
            <button className={styles.close} onClick={() => setSetupOpen(false)} aria-label="Close setup">×</button>
            <h2>Setup</h2>
            <label className={styles.field}>
              <span>Course</span>
              <input value={course} onChange={(e) => setCourse(e.target.value)} />
            </label>
            <label className={styles.field}>
              <span>Slides (separate with a line ---)</span>
              <textarea rows={7} value={slidesText} onChange={(e) => setSlidesText(e.target.value)} />
            </label>
            <div className={styles.actions}>
              <button className={styles.primary} onClick={start} disabled={backend === "offline" || backend === "checking"}>
                {session ? "Start a new session" : "Start session"}
              </button>
            </div>
            <h3>Demo</h3>
            <p className={styles.muted}>These work without a session, handy during the pitch.</p>
            <div className={styles.actions}>
              <button onClick={() => { setSetupOpen(false); demoRaiseHand(); }}>Raise a hand</button>
              <button onClick={() => { setSetupOpen(false); demoShuffle(); }}>Shuffle moods</button>
            </div>
          </div>
        </div>
      )}

      {report && (
        <div className={styles.backdrop} onClick={() => setReport(null)}>
          <div className={styles.dialog} role="dialog" aria-label="Rehearsal report" onClick={(e) => e.stopPropagation()}>
            <button className={styles.close} onClick={() => setReport(null)} aria-label="Close report">×</button>
            <h2>How did it go?</h2>
            <p>{report.coach.summary}</p>
            <h3>Change these first</h3>
            <ol>{report.coach.top_changes.map((c, i) => <li key={i}>{c}</li>)}</ol>
            {report.fixes.map((f, i) => (
              <div key={i} className={styles.fix}>
                <h3>Lost {f.moment.lost_students.join(", ")} at chunk {f.moment.chunk_index}</h3>
                <p><b>{f.selection.chosen_agent}:</b> {f.selection.final_fix}</p>
                <p className={styles.muted}>{f.selection.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Meter({ label, value, tone }: { label: string; value: number; tone: "blue" | "pink" }) {
  return (
    <div className={styles.meter}>
      <span>{label}</span>
      <span className={styles.meterTrack}><i className={styles[tone]} style={{ width: `${value}%` }} /></span>
      <b>{value}</b>
    </div>
  );
}
