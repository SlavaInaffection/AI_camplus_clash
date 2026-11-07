"""Generate the Rehearsal Room students as clean, flat SVG files.

Style: chibi proportions (big head, small body), every student tinted in ONE hue
(skin, hair and clothes are shades of it), big round eyes, blush, soft floor shadow.
No strokes on the body, no <style>, no text, no filters: plain shapes that import
cleanly into Figma/Illustrator, Three.js (SVGLoader) or an <img>.

Output: frontend/characters/<id>-<name>-<state>.svg  +  index.json

Run:  python tools/make_characters.py
"""

import colorsys
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "characters"

STATES = ["listening", "taking_notes", "nodding", "confused", "lost",
          "bored", "sleeping", "on_phone", "excited", "hand_raised"]

INK = "#1d1b2b"
WHITE = "#ffffff"
BLUSH = "#ff8fa3"

# id, name, hue, hair style, accessories
STUDENTS = [
    (0, "Giulia", 205, "bob", []),
    (1, "Mateo", 18, "swoop", ["scarf"]),
    (2, "Sara", 150, "ponytail", ["glasses"]),
    (3, "Luca", 230, "messy", []),
    (4, "Amira", 330, "long", []),
    (5, "Paolo", 40, "short", []),
    (6, "Chen", 250, "hood", []),
    (7, "Elena", 280, "bun", ["glasses"]),
    (8, "Marco", 190, "cap", []),
    (9, "Fatima", 355, "curly", []),
    (10, "Tommaso", 95, "spiky", []),
    (11, "Sofia", 300, "beanie", ["headphones"]),
    (12, "Davide", 170, "curly_short", ["glasses"]),
    (13, "Nadia", 265, "long", ["thick_glasses"]),
    (14, "Riccardo", 28, "quiff", []),
]


def hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def palette(h):
    return {
        "skin": hsl(h, 60, 86), "skin_shade": hsl(h, 45, 77),
        "hair": hsl(h, 42, 42), "hair_dark": hsl(h, 45, 32),
        "cloth": hsl(h, 42, 60), "cloth_dark": hsl(h, 38, 48),
        "pants": hsl(h, 32, 40), "shoe": hsl(h, 30, 26),
        "accent": hsl((h + 40) % 360, 55, 62),
    }


# --- body parts -------------------------------------------------------------

def arm(c, sx, sy, angle, length=46):
    """An arm hanging from shoulder (sx, sy); angle 0 = straight down, positive swings left."""
    return (f'<g transform="rotate({angle} {sx} {sy})">'
            f'<rect x="{sx - 8}" y="{sy - 4}" width="16" height="{length}" rx="8" fill="{c["cloth"]}"/>'
            f'<circle cx="{sx}" cy="{sy + length}" r="8.5" fill="{c["skin"]}"/></g>')


def body(c):
    return (
        f'<rect x="76" y="184" width="20" height="38" rx="9" fill="{c["pants"]}"/>'
        f'<rect x="104" y="184" width="20" height="38" rx="9" fill="{c["pants"]}"/>'
        f'<ellipse cx="85" cy="223" rx="14" ry="7.5" fill="{c["shoe"]}"/>'
        f'<ellipse cx="115" cy="223" rx="14" ry="7.5" fill="{c["shoe"]}"/>'
        f'<path d="M62,192 C60,160 68,134 100,131 C132,134 140,160 138,192 Q100,200 62,192 Z" fill="{c["cloth"]}"/>'
        f'<path d="M62,192 Q100,200 138,192 L138,184 Q100,192 62,184 Z" fill="{c["cloth_dark"]}"/>'
        f'<path d="M88,134 Q100,146 112,134" fill="none" stroke="{c["cloth_dark"]}" stroke-width="4" stroke-linecap="round"/>'
    )


HEAD = (100, 86)  # centre; rx 52, ry 48


def head(c):
    return (f'<ellipse cx="100" cy="132" rx="16" ry="6" fill="{c["skin_shade"]}"/>'
            f'<ellipse cx="100" cy="86" rx="52" ry="48" fill="{c["skin"]}"/>'
            f'<ellipse cx="48" cy="92" rx="7" ry="10" fill="{c["skin"]}"/>'
            f'<ellipse cx="152" cy="92" rx="7" ry="10" fill="{c["skin"]}"/>')


CAP_TOP = "M47,90 C44,46 74,32 100,32 C126,32 156,46 153,90 C146,70 124,58 100,58 C76,58 54,70 47,90 Z"


def hair(style, c):
    """Returns (behind_head, in_front_of_head)."""
    h, d = c["hair"], c["hair_dark"]
    back, front = "", f'<path d="{CAP_TOP}" fill="{h}"/>'
    if style == "bob":
        back = f'<path d="M44,80 C40,40 72,30 100,30 C128,30 160,40 156,80 L158,124 Q150,132 140,124 L60,124 Q50,132 42,124 Z" fill="{d}"/>'
        front += f'<path d="M50,84 C60,58 90,52 118,60 C104,62 88,70 80,84 Z" fill="{d}"/>'
    elif style == "long":
        back = f'<path d="M42,84 C38,36 72,28 100,28 C128,28 162,36 158,84 L162,164 Q150,172 138,160 L62,160 Q50,172 38,164 Z" fill="{d}"/>'
        front += f'<path d="M100,40 C84,52 70,66 62,84 C76,70 90,62 100,58 Z" fill="{d}"/>'
    elif style == "ponytail":
        back = (f'<ellipse cx="156" cy="70" rx="16" ry="28" transform="rotate(25 156 70)" fill="{d}"/>'
                f'<circle cx="146" cy="52" r="8" fill="{c["accent"]}"/>')
    elif style == "bun":
        back = f'<circle cx="100" cy="30" r="20" fill="{d}"/>'
        front += f'<path d="M58,78 C66,62 84,56 100,56 C116,56 134,62 142,78 C128,68 114,64 100,64 C86,64 72,68 58,78 Z" fill="{d}"/>'
    elif style == "swoop":
        front = (f'<path d="M47,92 C42,44 74,30 104,32 C134,34 158,50 153,88 C140,74 128,70 116,68 C98,74 74,78 60,90 Z" fill="{h}"/>'
                 f'<path d="M60,90 C72,72 96,64 120,66 C100,58 78,62 60,90 Z" fill="{d}"/>')
    elif style == "short":
        front = f'<path d="M50,82 C48,46 74,36 100,36 C126,36 152,46 150,82 C140,68 122,62 100,62 C78,62 60,68 50,82 Z" fill="{h}"/>'
    elif style == "messy":
        front = (f'<path d="M47,90 C40,52 60,30 82,34 L88,22 L98,34 L110,20 L116,34 L130,26 L132,40 C152,48 158,66 153,90 '
                 f'C144,70 124,60 100,60 C76,60 54,70 47,90 Z" fill="{h}"/>')
    elif style == "spiky":
        front = (f'<path d="M47,90 L44,54 L60,58 L60,36 L76,46 L84,24 L96,42 L108,22 L118,42 L132,28 L136,48 L154,42 L153,90 '
                 f'C144,70 124,60 100,60 C76,60 54,70 47,90 Z" fill="{h}"/>')
    elif style == "quiff":
        front = (f'<path d="M48,86 C44,50 66,38 86,36 C88,18 120,12 134,28 C124,26 114,30 112,38 C138,42 156,58 152,86 '
                 f'C142,70 122,62 100,62 C78,62 58,70 48,86 Z" fill="{h}"/>')
    elif style in ("curly", "curly_short"):
        r = 14 if style == "curly" else 11
        pts = [(52, 76), (56, 56), (68, 42), (84, 34), (100, 31), (116, 34), (132, 42), (144, 56), (148, 76)]
        if style == "curly":
            back = "".join(f'<circle cx="{x}" cy="{y}" r="15" fill="{d}"/>' for x, y in [(46, 100), (154, 100), (44, 120), (156, 120)])
        front = (f'<path d="M50,86 C48,52 74,40 100,40 C126,40 152,52 150,86 C140,70 122,64 100,64 C78,64 60,70 50,86 Z" fill="{h}"/>'
                 + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{h}"/>' for x, y in pts)
                 + "".join(f'<circle cx="{x}" cy="{y + 4}" r="{r - 6}" fill="{d}"/>' for x, y in pts[1::2]))
    elif style == "hood":
        back = f'<ellipse cx="100" cy="84" rx="64" ry="60" fill="{c["cloth_dark"]}"/>'
        front = (f'<path d="M40,96 C36,40 70,22 100,22 C130,22 164,40 160,96 C156,62 132,44 100,44 C68,44 44,62 40,96 Z" fill="{c["cloth"]}"/>'
                 f'<path d="M58,80 C70,58 92,54 112,58 C96,62 80,70 70,84 Z" fill="{h}"/>')
    elif style == "cap":
        front = (f'<path d="M50,84 C48,62 60,48 76,48 L124,48 C140,48 152,62 150,84 C138,72 120,66 100,66 C80,66 62,72 50,84 Z" fill="{h}"/>'
                 f'<path d="M50,64 C50,30 76,22 100,22 C124,22 150,30 150,64 Z" fill="{c["cloth_dark"]}"/>'
                 f'<path d="M48,62 L152,62 Q170,64 176,72 Q150,74 48,70 Z" fill="{c["shoe"]}"/>'
                 f'<circle cx="100" cy="24" r="5" fill="{c["shoe"]}"/>')
    elif style == "beanie":
        front = (f'<path d="M50,88 C46,70 54,60 64,58 L136,58 C146,60 154,70 150,88 C140,74 122,70 100,70 C78,70 60,74 50,88 Z" fill="{h}"/>'
                 f'<path d="M50,62 C48,26 76,16 100,16 C124,16 152,26 150,62 Z" fill="{c["accent"]}"/>'
                 f'<rect x="46" y="54" width="108" height="16" rx="8" fill="{c["cloth_dark"]}"/>'
                 f'<circle cx="100" cy="14" r="9" fill="{c["accent"]}"/>')
    return back, front


def accessories(items, c):
    out = ""
    for a in items:
        if a in ("glasses", "thick_glasses"):
            w = 4.5 if a == "thick_glasses" else 3
            out += (f'<circle cx="80" cy="93" r="15" fill="none" stroke="{c["hair_dark"]}" stroke-width="{w}"/>'
                    f'<circle cx="120" cy="93" r="15" fill="none" stroke="{c["hair_dark"]}" stroke-width="{w}"/>'
                    f'<path d="M95,92 Q100,88 105,92" fill="none" stroke="{c["hair_dark"]}" stroke-width="{w}" stroke-linecap="round"/>')
    return out


def neckwear(items, c):
    out = ""
    if "scarf" in items:
        out += (f'<path d="M70,136 Q100,152 130,136 L130,146 Q100,162 70,146 Z" fill="{c["accent"]}"/>'
                f'<rect x="112" y="142" width="14" height="30" rx="6" fill="{c["accent"]}"/>')
    if "headphones" in items:
        out += (f'<path d="M72,146 Q100,168 128,146" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
                f'<rect x="62" y="138" width="16" height="20" rx="7" fill="{INK}"/>'
                f'<rect x="122" y="138" width="16" height="20" rx="7" fill="{INK}"/>')
    return out


# --- faces ------------------------------------------------------------------

def eye(cx, cy, kind, c):
    if kind == "closed":
        return f'<path d="M{cx - 9},{cy} Q{cx},{cy + 7} {cx + 9},{cy}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>'
    if kind == "happy":
        return f'<path d="M{cx - 9},{cy + 3} Q{cx},{cy - 8} {cx + 9},{cy + 3}" fill="none" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>'
    ox, oy, pr, ry = {"neutral": (0, 1, 5, 11), "down": (0, 5, 5, 11), "side": (4, -1, 5, 11),
                      "wide": (0, 0, 3.2, 12.5), "sparkle": (0, 0, 6.5, 12), "half": (0, 4, 5, 11)}[kind]
    s = (f'<ellipse cx="{cx}" cy="{cy}" rx="10" ry="{ry}" fill="{WHITE}"/>'
         f'<circle cx="{cx + ox}" cy="{cy + oy}" r="{pr}" fill="{INK}"/>'
         f'<circle cx="{cx + ox + 1.8}" cy="{cy + oy - 2}" r="1.7" fill="{WHITE}"/>')
    if kind == "sparkle":
        s += f'<circle cx="{cx - 2}" cy="{cy + 2.5}" r="1.2" fill="{WHITE}"/>'
    if kind == "half":
        s += (f'<path d="M{cx - 11},{cy - 12} L{cx + 11},{cy - 12} L{cx + 11},{cy} Q{cx},{cy - 2} {cx - 11},{cy} Z" fill="{c["skin"]}"/>'
              f'<path d="M{cx - 10},{cy} Q{cx},{cy - 2} {cx + 10},{cy}" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>')
    return s


def brow(x1, y1, x2, y2, c):
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{c["hair_dark"]}" stroke-width="4.5" stroke-linecap="round"/>'


def mouth(kind):
    return {
        "smile": f'<path d="M92,111 Q100,118 108,111" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "flat": f'<path d="M93,113 L107,113" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "o": f'<ellipse cx="100" cy="114" rx="3.6" ry="4.6" fill="{INK}"/>',
        "open": f'<path d="M89,108 Q100,126 111,108 Z" fill="#7a2638"/><path d="M94,117 Q100,122 106,117 Q100,114 94,117 Z" fill="#ff8a9b"/>',
        "squiggle": f'<path d="M90,114 q5,-5 10,0 t10,0" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "small": f'<path d="M96,112 Q100,115 104,112" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
    }[kind]


FACES = {  # eyes, brows (left, right), mouth, blush
    "listening": ("neutral", ((70, 74, 88, 72), (112, 72, 130, 74)), "smile", True),
    "taking_notes": ("down", ((70, 76, 88, 75), (112, 75, 130, 76)), "small", True),
    "nodding": ("happy", ((70, 72, 88, 70), (112, 70, 130, 72)), "smile", True),
    "confused": ("side", ((70, 70, 88, 64), (112, 76, 130, 74)), "squiggle", False),
    "lost": ("wide", ((70, 70, 88, 66), (112, 66, 130, 70)), "o", False),
    "bored": ("half", ((70, 78, 88, 78), (112, 78, 130, 78)), "flat", False),
    "sleeping": ("closed", ((70, 78, 88, 78), (112, 78, 130, 78)), "o", True),
    "on_phone": ("down", ((70, 76, 88, 76), (112, 76, 130, 76)), "flat", False),
    "excited": ("sparkle", ((70, 68, 88, 66), (112, 66, 130, 68)), "open", True),
    "hand_raised": ("neutral", ((70, 68, 88, 66), (112, 66, 130, 68)), "open", True),
}


def face(state, c):
    e, (bl, br), m, blush = FACES[state]
    s = eye(80, 93, e, c) + eye(120, 93, e, c) + brow(*bl, c) + brow(*br, c) + mouth(m)
    if blush:
        s += (f'<ellipse cx="66" cy="108" rx="8" ry="4.5" fill="{BLUSH}" opacity="0.55"/>'
              f'<ellipse cx="134" cy="108" rx="8" ry="4.5" fill="{BLUSH}" opacity="0.55"/>')
    return s


# --- poses ------------------------------------------------------------------

POSES = {  # head tilt, arms behind head, arms in front, prop
    "listening": (0, [(64, 142, 9), (136, 142, -9)], [], None),
    "taking_notes": (4, [], [(66, 144, -40, 36), (134, 144, 40, 36)], "notebook"),
    "nodding": (-6, [(64, 142, 9), (136, 142, -9)], [], None),
    "confused": (-8, [(64, 142, 9)], [(136, 142, 150, 34)], None),
    "lost": (5, [(64, 142, 14), (136, 142, -14)], [], "sweat"),
    "bored": (-10, [(64, 142, 9)], [(136, 142, 128, 30)], None),
    "sleeping": (16, [(64, 142, 6), (136, 142, -6)], [], "zzz"),
    "on_phone": (8, [], [(66, 144, -40, 34), (134, 144, 40, 34)], "phone"),
    "excited": (-4, [(64, 140, 140), (136, 140, -140)], [], None),
    "hand_raised": (-6, [(64, 142, 12), (138, 140, -158, 96)], [], None),
}


def prop(kind, c):
    if kind == "notebook":
        return (f'<rect x="78" y="158" width="44" height="30" rx="4" fill="{WHITE}"/>'
                f'<path d="M84,166 L116,166 M84,173 L116,173 M84,180 L106,180" stroke="{c["cloth_dark"]}" stroke-width="2" stroke-linecap="round"/>'
                f'<rect x="114" y="150" width="5" height="24" rx="2.5" transform="rotate(30 116 162)" fill="{c["accent"]}"/>')
    if kind == "phone":
        return (f'<rect x="89" y="152" width="22" height="34" rx="5" fill="{INK}"/>'
                f'<rect x="92" y="156" width="16" height="25" rx="2.5" fill="#8fd3ff"/>')
    if kind == "sweat":
        return f'<path d="M150,58 Q158,70 154,76 Q148,80 145,74 Q144,68 150,58 Z" fill="#9fd8ff"/>'
    if kind == "zzz":
        return (f'<path d="M148,40 L160,40 L148,52 L160,52" fill="none" stroke="{c["cloth_dark"]}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="M164,20 L174,20 L164,30 L174,30" fill="none" stroke="{c["cloth_dark"]}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
    return ""


def character(student, state):
    sid, name, hue, style, acc = student
    c = palette(hue)
    tilt, behind, front, p = POSES[state]
    hair_back, hair_front = hair(style, c)
    arms_behind = "".join(arm(c, *a) for a in behind)
    arms_front = "".join(arm(c, *a) for a in front)
    head_group = (f'<g transform="rotate({tilt} 100 132)">{hair_back}{head(c)}{hair_front}'
                  f'{face(state, c)}{accessories(acc, c)}</g>')
    # bored / confused: the hand goes to the chin or head, so draw it over the head
    over_head = state in ("bored", "confused")
    parts = [
        f'<ellipse cx="100" cy="228" rx="58" ry="8" fill="{INK}" opacity="0.10"/>',
        arms_behind,
        body(c),
        neckwear(acc, c),
        "" if over_head else arms_front,
        prop(p, c) if p in ("notebook", "phone") else "",
        head_group,
        arms_front if over_head else "",
        prop(p, c) if p in ("sweat", "zzz") else "",
    ]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240" '
            f'role="img" aria-label="{name}, {state.replace("_", " ")}">' + "".join(parts) + "</svg>")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = {"viewBox": "0 0 200 240", "states": STATES, "students": []}
    for st in STUDENTS:
        files = {}
        for state in STATES:
            fn = f"{st[0]:02d}-{st[1].lower()}-{state}.svg"
            (OUT / fn).write_text(character(st, state))
            files[state] = f"characters/{fn}"
        index["students"].append({"id": st[0], "name": st[1], "hue": st[2], "color": palette(st[2])["cloth"], "files": files})
    (OUT / "index.json").write_text(json.dumps(index, indent=2))
    print(f"wrote {len(STUDENTS) * len(STATES)} SVGs to {OUT}")


if __name__ == "__main__":
    main()
