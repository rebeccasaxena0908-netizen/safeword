#!/usr/bin/env python3
"""
Offline incident simulator - no Gmail, no network beyond the mock services.
This is what you develop and demo against; the live bot is the same code with
an IMAP listener in front.

Start both mock services first, or every action reports ok=False:
    python mockservices/bank/app.py     (port 5001)
    python mockservices/social/app.py   (port 5002)

    python scripts/simulate.py
    python scripts/simulate.py --dry-run          # no calls to mock services
    python scripts/simulate.py --rules            # force the rule baseline
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCENARIOS = [
    ("stranger@nowhere.com", "freeze everything now",
     "Unknown sender - dies at the gate, no reply sent"),

    ("your.work.email@example.com",
     "my friend's phone got stolen last week, so annoying",
     "Mere mention -> no action. The hard negative that holds FTR down."),

    ("your.work.email@example.com",
     "koi mera phone le gaya, sab lock kar do",
     "Hinglish theft -> the rule lexicon misses 'le gaya' entirely. "
     "Run with --rules to see it classified out_of_scope."),

    ("your.work.email@example.com", "I lost my phone somewhere",
     "KNOWN REGRESSION -> should be Tier 1, model says out_of_scope. "
     "Cost of cutting FTR 0.372->0.166 with hard negatives; rules get this right."),

    ("close.friend@example.com",
     "Hi, this is Rebecca's friend - her phone just got snatched, she asked me to mail you",
     "Proxy sender -> capped at Tier 1 until the owner confirms out of band"),

    ("your.work.email@example.com",
     "my phone was stolen, lock everything except my email",
     "SCOPE=except -> one token removes gmail from the action set"),
]

CHALLENGE_FLOW = [
    ("your.work.email@example.com",
     "omg someone grabbed my phone at the metro station!! lock everything NOW",
     "Turn 1 -> trust hits 1.0 and STILL caps at Tier 1. "
     "Passive signals never unlock irreversible actions."),

    ("your.work.email@example.com", "bruno, nani's dog",
     "Turn 2 -> paraphrased answer clears the challenge. Tier 2 fires: "
     "sessions -> passwords -> bank -> EMAIL LAST."),
]


def run(sender, text, label, profile, dry_run, keep_state=False):
    from safeword.orchestrator import handle_message, reset_state
    if not keep_state:
        reset_state()
    print("\n" + "=" * 78)
    print(f"  {label}")
    print(f"  from: {sender}")
    print(f"  text: {text[:70]}")
    print("-" * 78)
    inc, u, report = handle_message(
        text, sender, profile,
        auth={"spf": "pass", "dkim": "pass", "dmarc": "pass"},
        dry_run=dry_run, grace_override=0)
    print("-" * 78)
    print(report)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="skip calls to the mock services")
    p.add_argument("--rules", action="store_true",
                   help="force rule baselines instead of trained models")
    a = p.parse_args()

    # Must be set before safeword.nlp.models is imported anywhere.
    if a.rules:
        os.environ["SAFEWORD_USE_MODELS"] = "0"

    from safeword.config import load_profile
    from safeword.nlp import models
    from safeword.orchestrator import reset_state

    profile = load_profile()

    # Warm the models up front so the loading bars do not interleave with the
    # first scenario's audit output during a live demo.
    live = models.status()
    backend = "RULE BASELINE" if not any(live.values()) else "TRAINED MODELS"
    print(f"backend: {backend}   " +
          ", ".join(f"{k}={'model' if v else 'rules'}" for k, v in live.items()))
    if any(live.values()):
        print("warming models...", end=" ", flush=True)
        for name, labels in [("intent", ["a"]), ("role", ["a"]),
                             ("distress", ["a"]), ("scope", ["a"])]:
            models.predict(name, "warmup", labels * 8)
        print("ready")

    if not a.dry_run:
        import requests
        for name, url in [("bank", "http://127.0.0.1:5001/api/state"),
                          ("social", "http://127.0.0.1:5002/")]:
            try:
                requests.get(url, timeout=2)
            except Exception:
                print(f"\n  WARNING: mock {name} service is not running at {url}")
                print(f"  Every action will report ok=False. Start it with:")
                print(f"    python mockservices/{name}/app.py")

    for sender, text, label in SCENARIOS:
        run(sender, text, label, profile, a.dry_run)
    reset_state()
    for sender, text, label in CHALLENGE_FLOW:
        run(sender, text, label, profile, a.dry_run, keep_state=True)

    print("\nAudit trail: logs/audit.jsonl")