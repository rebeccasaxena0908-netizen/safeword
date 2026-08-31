#!/usr/bin/env python3
"""
Step 2 of corpus construction: expand each seed into register variants.

Two modes.

  --mode api       Uses the Anthropic API to paraphrase. Needs ANTHROPIC_API_KEY
                   in .env. Best quality, ~15-20 variants per seed.
  --mode template  No API needed. Applies deterministic register transforms.
                   Lower diversity, but free and reproducible - use it to get
                   the pipeline working, then re-run with --mode api.

Labels are NEVER changed by expansion. A paraphrase of a stolen_confirmed seed
is still stolen_confirmed. If a paraphrase would change the label, the prompt
is wrong - fix the prompt, do not relabel.

    python scripts/expand_corpus.py --mode template --per-seed 12
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "corpus" / "build"))

import seeds as seedmod

OUT = ROOT / "corpus" / "raw" / "expanded.jsonl"

# --- template mode -------------------------------------------------------
FILLERS = ["please", "asap", "urgently", "right now", "immediately", "quickly"]
OPENERS = ["", "hi, ", "hey ", "hello, ", "sir, ", "listen, "]
CLOSERS = ["", " thanks", " please help", " pls", " thank you", " help me"]


def template_variants(text: str, n: int, rng: random.Random) -> list[str]:
    out, seen = [], {text.lower()}
    tries = 0
    while len(out) < n and tries < n * 12:
        tries += 1
        t = text
        r = rng.random()
        if r < 0.35:
            t = rng.choice(OPENERS) + t
        if r > 0.55:
            t = t.rstrip(".!") + rng.choice(CLOSERS)
        if rng.random() < 0.3:
            words = t.split()
            if len(words) > 4:
                words.insert(rng.randrange(2, len(words)), rng.choice(FILLERS))
                t = " ".join(words)
        if rng.random() < 0.25:
            t = t.lower()
        if rng.random() < 0.15:
            t = t.replace(",", "").replace(".", "")
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


# --- api mode ------------------------------------------------------------
PROMPT = """You are helping build a labelled dataset of emergency emails for an NLP research project.

Rewrite the message below into {n} DIFFERENT variants. Keep the meaning and the
intent identical - only the wording, tone and register change.

Vary across: formal, terse, panicked with typos, polite, fragmentary, and
Hinglish (Hindi-English code-mixed, Latin script).

Hard rules:
- Do NOT change what is being asked for. A theft report stays a theft report.
- Do NOT add or remove named services (bank, instagram, email etc).
- Do NOT add or remove scope words like "except", "only", "especially".
- Keep each variant under 40 words.

Return ONLY a JSON array of strings. No preamble, no markdown fences.

Message: {text}"""


def api_variants(text: str, n: int) -> list[str]:
    import requests
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY not set in .env - use --mode template instead")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 2000,
              "messages": [{"role": "user", "content": PROMPT.format(n=n, text=text)}]},
        timeout=60)
    raw = "".join(b.get("text", "") for b in r.json().get("content", []))
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return [str(x) for x in json.loads(raw)][:n]
    except json.JSONDecodeError:
        print(f"  ! unparseable response for: {text[:40]}")
        return []


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["template", "api"], default="template")
    p.add_argument("--per-seed", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    rng = random.Random(a.seed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with open(OUT, "w") as fh:
        for i, s in enumerate(seedmod.S):
            seed_id = f"s{i:04d}"
            # the original always survives, labelled as the canonical variant
            fh.write(json.dumps({**s, "seed_id": seed_id, "variant": 0,
                                 "source": "seed"}) + "\n")
            written += 1

            # Messages with email furniture are expanded on the body only;
            # augment_corpus.py re-grafts furniture afterwards.
            if s["furniture"]:
                continue

            variants = (template_variants(s["text"], a.per_seed, rng)
                        if a.mode == "template"
                        else api_variants(s["text"], a.per_seed))
            for j, v in enumerate(variants, start=1):
                fh.write(json.dumps({**s, "text": v, "seed_id": seed_id,
                                     "variant": j, "source": a.mode}) + "\n")
                written += 1
            if a.mode == "api" and i % 10 == 0:
                print(f"  {i}/{len(seedmod.S)} seeds expanded")

    print(f"{written} messages -> {OUT}")