#!/usr/bin/env python3
"""
Step 3: augmentation. Typos, casing corruption, and email furniture grafting.

The typo model matters more than it looks. Random character swaps are not what
panicked typing produces - real errors are adjacent-key hits, doubled letters,
dropped letters and missing apostrophes. Training on unrealistic noise buys
you nothing on the messages the system will actually see.

Furniture grafting is the M0 training signal: it takes clean bodies and wraps
them in signatures, quoted replies and forward headers, recording where the
body ends so the cleaner has line-level labels.

    python scripts/augment_corpus.py --typo-rate 0.12 --furniture-rate 0.30
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "corpus" / "raw" / "expanded.jsonl"
OUT = ROOT / "corpus" / "raw" / "augmented.jsonl"

# QWERTY adjacency - what a thumb actually hits by mistake
ADJ = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu", "z": "asx",
}

SIGNATURES = [
    "\n\n--\nSent from my iPhone",
    "\n\nSent from my Galaxy",
    "\n\nGet Outlook for Android",
    "\n\nRegards,\nRebecca",
    "\n\nBest,\nRebecca Saxena\n+91 98765 43210",
    "\n\nThanks,\nR",
]
QUOTES = [
    "\n\n> On Tue, 12 Aug 2025, Rebecca wrote:\n> are we still meeting at 6\n> let me know",
    "\n\n> hey did you get my last message\n> call me when free",
    "\n\nOn Mon, 4 Aug 2025 at 19:22, A Sharma wrote:\n> attaching the file\n> regards",
]
FORWARDS = [
    "---------- Forwarded message ----------\nFrom: Rebecca Saxena <r@example.com>\nDate: Tue, 12 Aug 2025\nSubject: help\nTo: bot@example.com\n\n",
]
DISCLAIMERS = [
    "\n\nThis email and any attachments are confidential and intended solely for the addressee.",
    "\n\nPlease consider the environment before printing this email.",
]


def inject_typos(text: str, rate: float, rng: random.Random) -> str:
    chars = list(text)
    n = max(1, int(len(chars) * rate))
    for _ in range(n):
        i = rng.randrange(len(chars))
        c = chars[i].lower()
        r = rng.random()
        if r < 0.45 and c in ADJ:
            chars[i] = rng.choice(ADJ[c])          # adjacent key
        elif r < 0.65:
            chars[i] = chars[i] + chars[i]         # doubled letter
        elif r < 0.85:
            chars[i] = ""                          # dropped letter
        elif i + 1 < len(chars):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]   # transposition
    out = "".join(chars)
    if rng.random() < 0.5:
        out = out.replace("'", "")                 # missing apostrophes
    return out


def graft_furniture(text: str, rng: random.Random) -> tuple[str, dict]:
    """
    Wrap a clean body in email furniture and return line-level M0 labels.

    Labels are built by splitting the ASSEMBLED text, not by accumulating
    counts alongside it. The earlier version tracked labels separately and
    drifted out of alignment whenever a blank separator line appeared, which
    made train_cleaner.py silently discard 97% of the corpus and left only
    two of five label classes in the data.
    """
    segments = []          # (label, text_block) in final order

    if rng.random() < 0.4:
        segments.append(("forwarded_header", rng.choice(FORWARDS).rstrip("\n")))
    segments.append(("body", text))
    if rng.random() < 0.6:
        segments.append(("signature", rng.choice(SIGNATURES).strip("\n")))
    if rng.random() < 0.35:
        segments.append(("quoted_reply", rng.choice(QUOTES).strip("\n")))
    if rng.random() < 0.2:
        segments.append(("disclaimer", rng.choice(DISCLAIMERS).strip("\n")))

    # Assemble with a blank line between blocks, labelling the separator with
    # the block it precedes - a blank line before a signature reads as part of
    # the signature block, which is what a human annotator would say too.
    lines, labels = [], []
    for idx, (label, block) in enumerate(segments):
        if idx > 0:
            lines.append("")
            labels.append(label)
        for ln in block.split("\n"):
            lines.append(ln)
            labels.append(label)

    assert len(lines) == len(labels), "furniture grafting misaligned"
    return "\n".join(lines), {"m0_labels": labels}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--typo-rate", type=float, default=0.12)
    p.add_argument("--typo-share", type=float, default=0.35,
                   help="fraction of messages that get a typo copy")
    p.add_argument("--furniture-rate", type=float, default=0.30)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    if not IN.exists():
        sys.exit("Run scripts/expand_corpus.py first.")

    rng = random.Random(a.seed)
    rows = [json.loads(l) for l in open(IN)]
    out = []

    for r in rows:
        out.append({**r, "aug": "none", "m0_labels": None})

        # typo copy - keeps the same seed_id so it cannot leak across splits
        if rng.random() < a.typo_share and not r.get("furniture"):
            out.append({**r, "text": inject_typos(r["text"], a.typo_rate, rng),
                        "aug": f"typo{int(a.typo_rate*100)}", "m0_labels": None})

        # furniture copy - the M0 training signal
        if rng.random() < a.furniture_rate and not r.get("furniture"):
            wrapped, meta = graft_furniture(r["text"], rng)
            out.append({**r, "text": wrapped, "aug": "furniture", **meta})

    with open(OUT, "w") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")

    from collections import Counter
    print(f"{len(rows)} -> {len(out)} messages")
    print(" ", dict(Counter(r["aug"] for r in out)))
    print(f"  -> {OUT}")