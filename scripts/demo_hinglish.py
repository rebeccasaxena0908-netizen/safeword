#!/usr/bin/env python3
"""
The one-liner demo: the rule lexicon knows only the synonyms its author
listed. 'le gaya' and 'taken' are not among them, so a real theft is
silently ignored - no action at all, in the moment it matters most.

The control case matters as much as the misses. It shows the rules are not
broken, they are incomplete in a way that cannot be fixed by adding words:
you cannot enumerate a language.

    python scripts/demo_hinglish.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safeword.nlp import models
from safeword.nlp.nlu import understand, understand_rules

INV = ["telegram", "whatsapp", "instagram", "demobank", "gmail"]

CASES = [
    ("koi mera phone le gaya, sab lock kar do",
     "Hinglish: 'le gaya' means took away. Not in the lexicon."),
    ("her phone got taken and she is panicking",
     "English: 'taken' is the most natural phrasing. Not in the lexicon."),
    ("bike wale ne phone cheen liya",
     "Hinglish: 'cheen liya' means snatched. Not in the lexicon."),
    ("my phone was stolen",
     "CONTROL: 'stolen' IS in the lexicon - both get this right."),
]

# Warm the models first so the loading bars do not land inside the table.
if any(models.status().values()):
    print("loading models...", end=" ", flush=True)
    understand("warmup", INV)
    print("done\n")

W = 46
print(f"{'message':<{W}}{'RULES':<20}{'MODELS':<20}")
print("-" * (W + 42))

missed = 0
for text, note in CASES:
    r = understand_rules(text, INV).intent
    m = understand(text, INV).intent
    is_miss = r == "out_of_scope" and m != "out_of_scope"
    missed += is_miss
    print(f"{text[:W-2]:<{W}}{r:<20}{m:<20}{'  <-- MISSED' if is_miss else ''}")
    print(f"  {note}\n")

print("-" * (W + 42))
print(f"{missed} of {len(CASES)} genuine thefts produce NO ACTION under the rule baseline.")
print("Every unlisted paraphrase falls through to out_of_scope. This is why the")
print("system needs a learned model, not a longer keyword list.")