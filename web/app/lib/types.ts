// Mirrors rehearsal/schemas.py and the /chunk contract in the repo README.

export const STATES = [
  "listening", "taking_notes", "nodding", "confused", "lost",
  "bored", "sleeping", "on_phone", "excited", "hand_raised",
] as const;
export type StudentStateName = (typeof STATES)[number];

export interface Persona {
  id: number;
  name: string;
  emoji: string;
  seat: [number, number]; // [row, col], row 0 = front
  situation: string;
  knowledge: string;
  loses_focus_when: string;
}

export interface StudentState {
  id: number;
  attention: number;
  confusion: number;
  state: StudentStateName;
  bubble: string;
  reason: string;
}

export interface Speaker {
  id: number;
  action: "raise_hand" | "interrupt" | "whisper_to_neighbour" | string;
  says: string;
  why: string;
}

export interface ChunkResult {
  chunk_index: number;
  slide_index: number | null;
  students: StudentState[];
  speakers: Speaker[];
  summary: string;
  class_attention: number;
  class_confusion: number;
}

export interface Slide {
  index: number;
  title: string;
  text: string;
}

export interface Session {
  id: string;
  course: string;
  slides: Slide[];
  students: StudentState[];
}

export interface Report {
  coach: { summary: string; strengths: string[]; top_changes: string[] };
  lost_moments: { chunk_index: number; lost_students: string[]; reasons: string[] }[];
  fixes: {
    moment: { chunk_index: number; lost_students: string[] };
    selection: { chosen_agent: string; final_fix: string; reasoning: string };
  }[];
}
