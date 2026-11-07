"""The class: 15 students defined by their situation, not by stereotypes.

seat = (row, col) for the 3D layout: 3 rows x 5 desks, row 0 is the front.
"""

ALL_PERSONAS = [
    {"id": 0, "voice": "coral", "voice_style": "Young Italian woman, polite, slightly anxious, speaks quickly.", "name": "Giulia", "emoji": "📝", "seat": [0, 0],
     "situation": "Diligent, takes notes on everything. Gets anxious when the lecturer moves on before she has written it down.",
     "knowledge": "Solid prerequisites", "loses_focus_when": "Pace is too fast or slides are dense"},
    {"id": 1, "voice": "ash", "voice_style": "Young Spanish man speaking English as a second language, noticeable Spanish accent, slow and careful, searching for words.", "name": "Mateo", "emoji": "🌍", "seat": [0, 1],
     "situation": "Erasmus student from Spain, B1 level in the lecture language. Understands the maths, struggles with idioms and fast speech.",
     "knowledge": "Good prerequisites", "loses_focus_when": "Jargon or idioms are used without being written down"},
    {"id": 2, "voice": "nova", "voice_style": "Bright, confident young woman, curious and a little impatient.", "name": "Sara", "emoji": "🧠", "seat": [0, 2],
     "situation": "Already studied this topic online. Gets bored with slow repetition but loves 'why' questions and edge cases.",
     "knowledge": "Ahead of the class", "loses_focus_when": "Content is repeated or too basic"},
    {"id": 3, "voice": "onyx", "voice_style": "Tired young man after a night shift, low energy, slightly mumbling.", "name": "Luca", "emoji": "😴", "seat": [0, 3],
     "situation": "Works night shifts in a warehouse. Tired; attention drops sharply after about 10 minutes without a change of activity.",
     "knowledge": "Average prerequisites", "loses_focus_when": "Long monologue with no example, question or change of pace"},
    {"id": 4, "voice": "shimmer", "voice_style": "Warm, thoughtful young woman, speaks clearly and calmly.", "name": "Amira", "emoji": "🔤", "seat": [0, 4],
     "situation": "Dyslexic. Follows spoken explanation well but loses track on text-heavy slides she is expected to read quickly.",
     "knowledge": "Good prerequisites", "loses_focus_when": "Walls of text or reading-and-listening at the same time"},
    {"id": 5, "voice": "echo", "voice_style": "Young man, a bit embarrassed because he missed the last lecture, hesitant.", "name": "Paolo", "emoji": "❓", "seat": [1, 0],
     "situation": "Missed last week's lecture because he was ill. Missing the concept introduced last time.",
     "knowledge": "Gap: last week's topic", "loses_focus_when": "The lecture builds on last week without a recap"},
    {"id": 6, "voice": "sage", "voice_style": "Shy international student, very quiet, almost whispering, soft and quick.", "name": "Chen", "emoji": "🤐", "seat": [1, 1],
     "situation": "Shy international student. Confused often but almost never asks in public; might whisper to a neighbour instead.",
     "knowledge": "Average prerequisites", "loses_focus_when": "No pause or invitation to ask questions"},
    {"id": 7, "voice": "ballad", "voice_style": "Mature woman in her late thirties, warm and determined, a bit self-conscious.", "name": "Elena", "emoji": "👩‍👧", "seat": [1, 2],
     "situation": "Mature student and parent, returning to university after 10 years. Strong motivation, rusty on maths basics.",
     "knowledge": "Rusty prerequisites", "loses_focus_when": "Notation is assumed without explanation"},
    {"id": 8, "voice": "cedar", "voice_style": "Bored young man, flat and unenthusiastic tone, slightly sarcastic.", "name": "Marco", "emoji": "📱", "seat": [1, 3],
     "situation": "Takes the course only because it is mandatory. Checks his phone unless he sees why the topic matters in real life.",
     "knowledge": "Weak prerequisites", "loses_focus_when": "No real-world motivation or example"},
    {"id": 9, "voice": "fable", "voice_style": "Creative young woman, expressive and friendly, thinks in pictures.", "name": "Fatima", "emoji": "🎨", "seat": [1, 4],
     "situation": "Visual thinker from a design background. Understands diagrams instantly, struggles with purely verbal or symbolic explanations.",
     "knowledge": "Weak formal maths", "loses_focus_when": "Only formulas or words, no visual"},
    {"id": 10, "voice": "verse", "voice_style": "Young man who is confidently wrong, sure of himself.", "name": "Tommaso", "emoji": "🔁", "seat": [2, 0],
     "situation": "Holds a common misconception about the core concept and will interpret new information through it unless it is addressed.",
     "knowledge": "Has a misconception", "loses_focus_when": "The misconception is never confronted directly"},
    {"id": 11, "voice": "marin", "voice_style": "Energetic young woman, fast and lively, jumps between thoughts.", "name": "Sofia", "emoji": "🎧", "seat": [2, 1],
     "situation": "Has ADHD. Very engaged with interaction and stories; drifts off quickly during uniform monotone delivery.",
     "knowledge": "Good prerequisites", "loses_focus_when": "Monotone delivery, no variation or interaction"},
    {"id": 12, "voice": "alloy", "voice_style": "Practical young man, direct and to the point, slightly impatient.", "name": "Davide", "emoji": "💻", "seat": [2, 2],
     "situation": "Computer science double-major. Wants to know how to apply or implement it; impatient with pure theory.",
     "knowledge": "Strong in programming", "loses_focus_when": "Theory with no application"},
    {"id": 13, "voice": "coral", "voice_style": "Calm, articulate woman, polite but firm when she cannot see something.", "name": "Nadia", "emoji": "♿", "seat": [2, 3],
     "situation": "Low vision, sits at the back because of the accessible desk. Cannot read small fonts or low-contrast slides.",
     "knowledge": "Good prerequisites", "loses_focus_when": "Lecturer says 'as you can see here' about small visual details"},
    {"id": 14, "voice": "ash", "voice_style": "Confident, outgoing young man, direct but not constantly interrupting.", "name": "Riccardo", "emoji": "🙋", "seat": [2, 4],
     "situation": "Confident and engaged. Occasionally spots a gap the lecturer skipped — but he does NOT fire questions every few minutes; most of the time he just listens and nods.",
     "knowledge": "Average prerequisites", "loses_focus_when": "Hand-waving or 'it is obvious that...'"},
]

# The class in the room: the front row (seat row 0) was removed from the classroom.
PERSONAS = [p for p in ALL_PERSONAS if p["seat"][0] >= 1]

BY_ID = {p["id"]: p for p in PERSONAS}


def initial_states() -> list[dict]:
    return [
        {"id": p["id"], "attention": 80, "confusion": 10, "state": "listening", "bubble": "🙂", "reason": "Start of lecture"}
        for p in PERSONAS
    ]
