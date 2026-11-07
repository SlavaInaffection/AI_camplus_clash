"use client";

// One animated student. Same drawing as tools/make_characters.py, but arms, head and
// props are live SVG groups whose transforms transition, so a state change (above all
// raising a hand) animates instead of swapping a picture.

import type { CSSProperties, ReactNode } from "react";
import { LOOKS, palette, type Accessory, type HairStyle, type Palette } from "../lib/characters";
import type { StudentStateName } from "../lib/types";
import styles from "./Student.module.css";

const INK = "#1d1b2b";
const WHITE = "#ffffff";
const BLUSH = "#ff8fa3";

// Both shoulders are fixed so the rotation origin never jumps between states.
const L = { x: 70, y: 150 };
const R = { x: 130, y: 150 };

interface ArmPose { angle: number; length: number }
interface Pose {
  tilt: number;
  left: ArmPose;
  right: ArmPose;
  rightOverHead?: boolean; // hand to chin / cheek: drawn over the face
  prop?: "notebook" | "phone" | "sweat" | "zzz";
  handsOnProp?: boolean;
}

const POSES: Record<StudentStateName, Pose> = {
  listening: { tilt: 0, left: { angle: 8, length: 46 }, right: { angle: -8, length: 46 } },
  taking_notes: { tilt: 4, left: { angle: -23, length: 30 }, right: { angle: 23, length: 30 }, prop: "notebook", handsOnProp: true },
  nodding: { tilt: -6, left: { angle: 8, length: 46 }, right: { angle: -8, length: 46 } },
  confused: { tilt: -8, left: { angle: 8, length: 46 }, right: { angle: 150, length: 34 }, rightOverHead: true },
  lost: { tilt: 5, left: { angle: 13, length: 46 }, right: { angle: -13, length: 46 }, prop: "sweat" },
  bored: { tilt: -10, left: { angle: 8, length: 46 }, right: { angle: 128, length: 30 }, rightOverHead: true },
  sleeping: { tilt: 16, left: { angle: 5, length: 46 }, right: { angle: -5, length: 46 }, prop: "zzz" },
  on_phone: { tilt: 8, left: { angle: -40, length: 31 }, right: { angle: 40, length: 31 }, prop: "phone", handsOnProp: true },
  excited: { tilt: -4, left: { angle: 140, length: 46 }, right: { angle: -140, length: 46 } },
  hand_raised: { tilt: -6, left: { angle: 10, length: 46 }, right: { angle: -158, length: 96 } },
};

const EASE = "cubic-bezier(.34,1.56,.64,1)"; // slight overshoot, feels alive
const T = `520ms ${EASE}`;

function Arm({ c, at, pose, wave }: { c: Palette; at: { x: number; y: number }; pose: ArmPose; wave?: boolean }) {
  const g: CSSProperties = {
    transform: `rotate(${pose.angle}deg)`,
    transformOrigin: `${at.x}px ${at.y}px`,
    transformBox: "view-box",
    transition: `transform ${T}`,
  };
  return (
    <g style={g}>
      <g className={wave ? styles.wave : undefined} style={{ transformOrigin: `${at.x}px ${at.y}px`, transformBox: "view-box" }}>
        <rect x={at.x - 8} y={at.y - 8} width={16} rx={8} fill={c.cloth}
          style={{ height: pose.length + 8, transition: `height ${T}` }} />
        <circle cx={at.x} r={8.5} fill={c.skin} style={{ cy: at.y + pose.length, transition: `cy ${T}` } as CSSProperties} />
      </g>
    </g>
  );
}

function handAt(at: { x: number; y: number }, pose: ArmPose) {
  const t = (pose.angle * Math.PI) / 180;
  return { x: at.x - Math.sin(t) * pose.length, y: at.y + Math.cos(t) * pose.length };
}

const CAP_TOP = "M47,90 C44,46 74,32 100,32 C126,32 156,46 153,90 C146,70 124,58 100,58 C76,58 54,70 47,90 Z";

function hair(style: HairStyle, c: Palette): { back: ReactNode; front: ReactNode } {
  const h = c.hair, d = c.hairDark;
  const cap = <path d={CAP_TOP} fill={h} />;
  switch (style) {
    case "bob":
      return {
        back: <path d="M44,80 C40,40 72,30 100,30 C128,30 160,40 156,80 L158,124 Q150,132 140,124 L60,124 Q50,132 42,124 Z" fill={d} />,
        front: <>{cap}<path d="M50,84 C60,58 90,52 118,60 C104,62 88,70 80,84 Z" fill={d} /></>,
      };
    case "long":
      return {
        back: <path d="M42,84 C38,36 72,28 100,28 C128,28 162,36 158,84 L162,164 Q150,172 138,160 L62,160 Q50,172 38,164 Z" fill={d} />,
        front: <>{cap}<path d="M100,40 C84,52 70,66 62,84 C76,70 90,62 100,58 Z" fill={d} /></>,
      };
    case "ponytail":
      return {
        back: <><ellipse cx={156} cy={70} rx={16} ry={28} transform="rotate(25 156 70)" fill={d} /><circle cx={146} cy={52} r={8} fill={c.accent} /></>,
        front: cap,
      };
    case "bun":
      return {
        back: <circle cx={100} cy={30} r={20} fill={d} />,
        front: <>{cap}<path d="M58,78 C66,62 84,56 100,56 C116,56 134,62 142,78 C128,68 114,64 100,64 C86,64 72,68 58,78 Z" fill={d} /></>,
      };
    case "swoop":
      return {
        back: null,
        front: <><path d="M47,92 C42,44 74,30 104,32 C134,34 158,50 153,88 C140,74 128,70 116,68 C98,74 74,78 60,90 Z" fill={h} />
          <path d="M60,90 C72,72 96,64 120,66 C100,58 78,62 60,90 Z" fill={d} /></>,
      };
    case "short":
      return { back: null, front: <path d="M50,82 C48,46 74,36 100,36 C126,36 152,46 150,82 C140,68 122,62 100,62 C78,62 60,68 50,82 Z" fill={h} /> };
    case "messy":
      return { back: null, front: <path d="M47,90 C40,52 60,30 82,34 L88,22 L98,34 L110,20 L116,34 L130,26 L132,40 C152,48 158,66 153,90 C144,70 124,60 100,60 C76,60 54,70 47,90 Z" fill={h} /> };
    case "spiky":
      return { back: null, front: <path d="M47,90 L44,54 L60,58 L60,36 L76,46 L84,24 L96,42 L108,22 L118,42 L132,28 L136,48 L154,42 L153,90 C144,70 124,60 100,60 C76,60 54,70 47,90 Z" fill={h} /> };
    case "quiff":
      return { back: null, front: <path d="M48,86 C44,50 66,38 86,36 C88,18 120,12 134,28 C124,26 114,30 112,38 C138,42 156,58 152,86 C142,70 122,62 100,62 C78,62 58,70 48,86 Z" fill={h} /> };
    case "curly":
    case "curly_short": {
      const r = style === "curly" ? 14 : 11;
      const pts: [number, number][] = [[52, 76], [56, 56], [68, 42], [84, 34], [100, 31], [116, 34], [132, 42], [144, 56], [148, 76]];
      const back = style === "curly"
        ? <>{([[46, 100], [154, 100], [44, 120], [156, 120]] as const).map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r={15} fill={d} />)}</>
        : null;
      return {
        back,
        front: <>
          <path d="M50,86 C48,52 74,40 100,40 C126,40 152,52 150,86 C140,70 122,64 100,64 C78,64 60,70 50,86 Z" fill={h} />
          {pts.map(([x, y]) => <circle key={`a${x}`} cx={x} cy={y} r={r} fill={h} />)}
          {pts.filter((_, i) => i % 2 === 1).map(([x, y]) => <circle key={`b${x}`} cx={x} cy={y + 4} r={r - 6} fill={d} />)}
        </>,
      };
    }
    case "hood":
      return {
        back: <ellipse cx={100} cy={84} rx={64} ry={60} fill={c.clothDark} />,
        front: <><path d="M40,96 C36,40 70,22 100,22 C130,22 164,40 160,96 C156,62 132,44 100,44 C68,44 44,62 40,96 Z" fill={c.cloth} />
          <path d="M58,80 C70,58 92,54 112,58 C96,62 80,70 70,84 Z" fill={h} /></>,
      };
    case "cap":
      return {
        back: null,
        front: <><path d="M50,84 C48,62 60,48 76,48 L124,48 C140,48 152,62 150,84 C138,72 120,66 100,66 C80,66 62,72 50,84 Z" fill={h} />
          <path d="M50,64 C50,30 76,22 100,22 C124,22 150,30 150,64 Z" fill={c.clothDark} />
          <path d="M48,62 L152,62 Q170,64 176,72 Q150,74 48,70 Z" fill={c.shoe} />
          <circle cx={100} cy={24} r={5} fill={c.shoe} /></>,
      };
    case "beanie":
    case "beanie_long": {
      const long = style === "beanie_long";
      return {
        back: long ? <path d="M44,80 C40,40 72,30 100,30 C128,30 160,40 156,80 L160,170 Q152,180 140,172 L60,172 Q48,180 40,170 Z" fill={d} /> : null,
        front: <>
          <path d="M50,88 C46,70 54,60 64,58 L136,58 C146,60 154,70 150,88 C140,74 122,70 100,70 C78,70 60,74 50,88 Z" fill={h} />
          {long && <><path d="M50,72 C46,96 48,120 54,138 L62,136 C58,116 58,94 62,74 Z" fill={h} />
            <path d="M150,72 C154,96 152,120 146,138 L138,136 C142,116 142,94 138,74 Z" fill={h} /></>}
          <path d="M50,62 C48,26 76,16 100,16 C124,16 152,26 150,62 Z" fill={c.accent} />
          <rect x={46} y={54} width={108} height={16} rx={8} fill={c.clothDark} />
          <circle cx={100} cy={14} r={9} fill={c.accent} />
        </>,
      };
    }
  }
}

// --- faces ------------------------------------------------------------------

type EyeKind = "neutral" | "down" | "side" | "wide" | "sparkle" | "half" | "closed" | "happy";

function Eye({ cx, cy, kind, c }: { cx: number; cy: number; kind: EyeKind; c: Palette }) {
  if (kind === "closed")
    return <path d={`M${cx - 9},${cy} Q${cx},${cy + 7} ${cx + 9},${cy}`} fill="none" stroke={INK} strokeWidth={3.2} strokeLinecap="round" />;
  if (kind === "happy")
    return <path d={`M${cx - 9},${cy + 3} Q${cx},${cy - 8} ${cx + 9},${cy + 3}`} fill="none" stroke={INK} strokeWidth={3.4} strokeLinecap="round" />;
  const [ox, oy, pr, ry] = ({ neutral: [0, 1, 5, 11], down: [0, 5, 5, 11], side: [4, -1, 5, 11], wide: [0, 0, 3.2, 12.5], sparkle: [0, 0, 6.5, 12], half: [0, 4, 5, 11] } as const)[kind];
  return (
    <g className={styles.blink} style={{ transformOrigin: `${cx}px ${cy}px`, transformBox: "view-box" }}>
      <ellipse cx={cx} cy={cy} rx={10} ry={ry} fill={WHITE} />
      <circle cx={cx + ox} cy={cy + oy} r={pr} fill={INK} />
      <circle cx={cx + ox + 1.8} cy={cy + oy - 2} r={1.7} fill={WHITE} />
      {kind === "sparkle" && <circle cx={cx - 2} cy={cy + 2.5} r={1.2} fill={WHITE} />}
      {kind === "half" && <>
        <path d={`M${cx - 11},${cy - 12} L${cx + 11},${cy - 12} L${cx + 11},${cy} Q${cx},${cy - 2} ${cx - 11},${cy} Z`} fill={c.skin} />
        <path d={`M${cx - 10},${cy} Q${cx},${cy - 2} ${cx + 10},${cy}`} fill="none" stroke={INK} strokeWidth={2.6} strokeLinecap="round" />
      </>}
    </g>
  );
}

const MOUTHS: Record<string, ReactNode> = {
  smile: <path d="M92,111 Q100,118 108,111" fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />,
  flat: <path d="M93,113 L107,113" stroke={INK} strokeWidth={3} strokeLinecap="round" />,
  o: <ellipse cx={100} cy={114} rx={3.6} ry={4.6} fill={INK} />,
  open: <><path d="M89,108 Q100,126 111,108 Z" fill="#7a2638" /><path d="M94,117 Q100,122 106,117 Q100,114 94,117 Z" fill="#ff8a9b" /></>,
  squiggle: <path d="M90,114 q5,-5 10,0 t10,0" fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />,
  small: <path d="M96,112 Q100,115 104,112" fill="none" stroke={INK} strokeWidth={3} strokeLinecap="round" />,
};

type Brow = [number, number, number, number];
const FACES: Record<StudentStateName, { eyes: EyeKind; brows: [Brow, Brow]; mouth: keyof typeof MOUTHS; blush: boolean }> = {
  listening: { eyes: "neutral", brows: [[70, 74, 88, 72], [112, 72, 130, 74]], mouth: "smile", blush: true },
  taking_notes: { eyes: "down", brows: [[70, 76, 88, 75], [112, 75, 130, 76]], mouth: "small", blush: true },
  nodding: { eyes: "happy", brows: [[70, 72, 88, 70], [112, 70, 130, 72]], mouth: "smile", blush: true },
  confused: { eyes: "side", brows: [[70, 70, 88, 64], [112, 76, 130, 74]], mouth: "squiggle", blush: false },
  lost: { eyes: "wide", brows: [[70, 70, 88, 66], [112, 66, 130, 70]], mouth: "o", blush: false },
  bored: { eyes: "half", brows: [[70, 78, 88, 78], [112, 78, 130, 78]], mouth: "flat", blush: false },
  sleeping: { eyes: "closed", brows: [[70, 78, 88, 78], [112, 78, 130, 78]], mouth: "o", blush: true },
  on_phone: { eyes: "down", brows: [[70, 76, 88, 76], [112, 76, 130, 76]], mouth: "flat", blush: false },
  excited: { eyes: "sparkle", brows: [[70, 68, 88, 66], [112, 66, 130, 68]], mouth: "open", blush: true },
  hand_raised: { eyes: "neutral", brows: [[70, 68, 88, 66], [112, 66, 130, 68]], mouth: "open", blush: true },
};

function Face({ state, c }: { state: StudentStateName; c: Palette }) {
  const f = FACES[state];
  return (
    <g key={state} className={styles.pop}>
      <Eye cx={80} cy={93} kind={f.eyes} c={c} />
      <Eye cx={120} cy={93} kind={f.eyes} c={c} />
      {f.brows.map(([x1, y1, x2, y2], i) => (
        <path key={i} d={`M${x1},${y1} L${x2},${y2}`} stroke={c.hairDark} strokeWidth={4.5} strokeLinecap="round" />
      ))}
      {MOUTHS[f.mouth]}
      {f.blush && <>
        <ellipse cx={66} cy={108} rx={8} ry={4.5} fill={BLUSH} opacity={0.55} />
        <ellipse cx={134} cy={108} rx={8} ry={4.5} fill={BLUSH} opacity={0.55} />
      </>}
    </g>
  );
}

function Glasses({ acc, c }: { acc: Accessory[]; c: Palette }) {
  const g = acc.find((a) => a === "glasses" || a === "thick_glasses");
  if (!g) return null;
  const w = g === "thick_glasses" ? 4.5 : 3;
  return <>
    <circle cx={80} cy={93} r={15} fill="none" stroke={c.hairDark} strokeWidth={w} />
    <circle cx={120} cy={93} r={15} fill="none" stroke={c.hairDark} strokeWidth={w} />
    <path d="M95,92 Q100,88 105,92" fill="none" stroke={c.hairDark} strokeWidth={w} strokeLinecap="round" />
  </>;
}

function Prop({ kind, c }: { kind: Pose["prop"]; c: Palette }) {
  switch (kind) {
    case "notebook":
      return <g className={styles.fadeIn}>
        <rect x={78} y={158} width={44} height={30} rx={4} fill={WHITE} />
        <path d="M84,166 L116,166 M84,173 L116,173 M84,180 L106,180" stroke={c.clothDark} strokeWidth={2} strokeLinecap="round" />
        <rect x={114} y={150} width={5} height={24} rx={2.5} transform="rotate(30 116 162)" fill={c.accent} />
      </g>;
    case "phone":
      return <g className={styles.fadeIn}>
        <rect x={89} y={152} width={22} height={34} rx={5} fill={INK} />
        <rect x={92} y={156} width={16} height={25} rx={2.5} fill="#8fd3ff" />
      </g>;
    case "sweat":
      return <path className={styles.drip} d="M150,58 Q158,70 154,76 Q148,80 145,74 Q144,68 150,58 Z" fill="#9fd8ff" />;
    case "zzz":
      return <g className={styles.zzz}>
        <path d="M148,40 L160,40 L148,52 L160,52" fill="none" stroke={c.clothDark} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
        <path d="M164,20 L174,20 L164,30 L174,30" fill="none" stroke={c.clothDark} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" />
      </g>;
    default:
      return null;
  }
}

export interface StudentProps {
  id: number;
  state: StudentStateName;
  /** Make the raised hand wave (while the student is talking). */
  waving?: boolean;
  className?: string;
}

export default function Student({ id, state, waving, className }: StudentProps) {
  const look = LOOKS[id];
  const c = palette(look.hue);
  const pose = POSES[state];
  const { back, front } = hair(look.hair, c);
  const headStyle: CSSProperties = {
    transform: `rotate(${pose.tilt}deg)`, transformOrigin: "100px 132px", transformBox: "view-box", transition: `transform ${T}`,
  };
  const leftHand = handAt(L, pose.left);
  const rightHand = handAt(R, pose.right);
  const rightArm = <Arm c={c} at={R} pose={pose.right} wave={state === "hand_raised" && waving} />;

  return (
    <svg viewBox="0 0 200 240" className={`${styles.student} ${styles[state] ?? ""} ${className ?? ""}`}
      role="img" aria-label={`${look.name}, ${state.replace("_", " ")}`}>
      <ellipse cx={100} cy={228} rx={58} ry={8} fill={INK} opacity={0.1} />
      <g className={styles.body}>
        <g style={headStyle}>{back}</g>
        {/* legs + torso */}
        <rect x={76} y={184} width={20} height={38} rx={9} fill={c.pants} />
        <rect x={104} y={184} width={20} height={38} rx={9} fill={c.pants} />
        <ellipse cx={85} cy={223} rx={14} ry={7.5} fill={c.shoe} />
        <ellipse cx={115} cy={223} rx={14} ry={7.5} fill={c.shoe} />
        <rect x={89} y={116} width={22} height={30} rx={10} fill={c.skinShade} />
        <path d="M58,192 C55,170 56,150 68,142 C78,137 88,136 100,136 C112,136 122,137 132,142 C144,150 145,170 142,192 Q100,200 58,192 Z" fill={c.cloth} />
        <path d="M58,192 Q100,200 142,192 L142,184 Q100,192 58,184 Z" fill={c.clothDark} />
        <path d="M86,138 Q100,150 114,138" fill="none" stroke={c.clothDark} strokeWidth={4} strokeLinecap="round" />
        {look.accessories.includes("scarf") && <>
          <path d="M70,136 Q100,152 130,136 L130,146 Q100,162 70,146 Z" fill={c.accent} />
          <rect x={112} y={142} width={14} height={30} rx={6} fill={c.accent} />
        </>}
        <Arm c={c} at={L} pose={pose.left} />
        {!pose.rightOverHead && rightArm}
        {pose.handsOnProp && <>
          <Prop kind={pose.prop} c={c} />
          <circle cx={leftHand.x} cy={leftHand.y} r={8.5} fill={c.skin} />
          <circle cx={rightHand.x} cy={rightHand.y} r={8.5} fill={c.skin} />
        </>}
        {/* head */}
        <g style={headStyle}>
          <g className={styles.head}>
            <ellipse cx={100} cy={86} rx={52} ry={48} fill={c.skin} />
            <ellipse cx={48} cy={92} rx={7} ry={10} fill={c.skin} />
            <ellipse cx={152} cy={92} rx={7} ry={10} fill={c.skin} />
            {front}
            <Face state={state} c={c} />
            <Glasses acc={look.accessories} c={c} />
          </g>
        </g>
        {pose.rightOverHead && rightArm}
        {!pose.handsOnProp && <Prop kind={pose.prop} c={c} />}
      </g>
    </svg>
  );
}
