"""Composition report on the hand-written seeds."""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "corpus" / "build"))

import seeds

S = seeds.S
print(f"seeds: {len(S)}  |  imposters: {len(seeds.IMPOSTERS)}\n")
for f in ("intent", "role", "distress", "scope", "lang"):
    print(f"{f:9}", dict(Counter(s[f] for s in S)))
print(f"\nhard negatives : {sum(s['hard_negative'] for s in S)}"
      f"  ({sum(s['hard_negative'] for s in S)/len(S):.0%})")
print(f"with furniture : {sum(1 for s in S if s['furniture'])}")