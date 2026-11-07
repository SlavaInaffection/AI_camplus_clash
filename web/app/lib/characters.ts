// Drawing config for the 15 students. Must match tools/make_characters.py.

export type HairStyle =
  | "bob" | "long" | "ponytail" | "bun" | "swoop" | "short" | "messy" | "spiky"
  | "quiff" | "curly" | "curly_short" | "hood" | "cap" | "beanie" | "beanie_long";
export type Accessory = "glasses" | "thick_glasses" | "scarf";

export interface Look {
  id: number;
  name: string;
  hue: number;
  hair: HairStyle;
  accessories: Accessory[];
}

export const LOOKS: Look[] = [
  { id: 0, name: "Giulia", hue: 205, hair: "bob", accessories: [] },
  { id: 1, name: "Mateo", hue: 18, hair: "swoop", accessories: ["scarf"] },
  { id: 2, name: "Sara", hue: 150, hair: "ponytail", accessories: ["glasses"] },
  { id: 3, name: "Luca", hue: 230, hair: "messy", accessories: [] },
  { id: 4, name: "Amira", hue: 330, hair: "long", accessories: [] },
  { id: 5, name: "Paolo", hue: 40, hair: "short", accessories: [] },
  { id: 6, name: "Chen", hue: 250, hair: "hood", accessories: [] },
  { id: 7, name: "Elena", hue: 280, hair: "bun", accessories: ["glasses"] },
  { id: 8, name: "Marco", hue: 190, hair: "cap", accessories: [] },
  { id: 9, name: "Fatima", hue: 355, hair: "curly", accessories: [] },
  { id: 10, name: "Tommaso", hue: 95, hair: "spiky", accessories: [] },
  { id: 11, name: "Sofia", hue: 300, hair: "beanie_long", accessories: [] },
  { id: 12, name: "Davide", hue: 170, hair: "curly_short", accessories: ["glasses"] },
  { id: 13, name: "Nadia", hue: 265, hair: "long", accessories: ["thick_glasses"] },
  { id: 14, name: "Riccardo", hue: 28, hair: "quiff", accessories: [] },
];

const hsl = (h: number, s: number, l: number) => `hsl(${h} ${s}% ${l}%)`;

export function palette(h: number) {
  return {
    skin: hsl(h, 60, 86), skinShade: hsl(h, 45, 77),
    hair: hsl(h, 42, 42), hairDark: hsl(h, 45, 32),
    cloth: hsl(h, 42, 60), clothDark: hsl(h, 38, 48),
    pants: hsl(h, 32, 40), shoe: hsl(h, 30, 26),
    accent: hsl((h + 40) % 360, 55, 62),
  };
}
export type Palette = ReturnType<typeof palette>;
