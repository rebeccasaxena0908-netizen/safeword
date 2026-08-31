#!/usr/bin/env python3
"""
The ablation table. Runs the SAME pipeline twice on the same test split -
once forced to rules, once with whatever models are enabled - and reports
both per-module and system-level metrics side by side.

This is the single command that produces the results section.

Two things it is designed to make visible:

  1. SEED COUNTS alongside message counts. A class showing n=104 may rest on
     five underlying situations; its F1 estimates five samples, not 104.

  2. SYSTEM METRICS separate from macro-F1. False trigger rate, missed
     emergency rate and command fidelity carry asymmetric cost, and macro-F1
     averages that away. M2 scope is the case in point: the trained model
     raises macro-F1 by +0.228 while LOWERING command fidelity, because it
     over-predicts 'except' (precision 0.394) and an over-predicted 'except'
     silently omits services from a real lockdown.

    python scripts/ablation.py
    python scripts/ablation.py --split dev
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.nlp import models
from safeword.nlp.cleaner import clean
from safeword.nlp.nlu import (DISTRESS, INTENTS, ROLES, SCOPES,
                              classify_distress, classify_distress_rules,
                              classify_intent, classify_intent_rules,
                              classify_role, classify_role_rules,
                              extract_slots, extract_slots_rules,
                              resolve_action_set)

INVENTORY = ["telegram", "whatsapp", "instagram", "demobank", "gmail"]
ACTIONABLE = {"stolen_confirmed", "lost_uncertain", "partial_lockdown"}


def macro_f1(gold, pred, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        if tp + fn:
            pr = tp / (tp + fp) if tp + fp else 0.0
            rc = tp / (tp + fn)
            f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    acc = sum(g == p for g, p in zip(gold, pred)) / len(gold)
    return acc, (sum(f1s) / len(f1s) if f1s else 0.0)


def per_class(gold, pred, labels, seeds_by_label):
    out = []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        if not (tp + fn):
            continue
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn)
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        out.append((lab, pr, rc, f1, tp + fn, len(seeds_by_label.get(lab, set()))))
    return out


def run(texts, rows, use_rules: bool):
    """Return every prediction stream for one backend configuration."""
    if use_rules:
        intent = [classify_intent_rules(t)[0] for t in texts]
        role = [classify_role_rules(t) for t in texts]
        distress = [classify_distress_rules(t)[0] for t in texts]
        slots = [extract_slots_rules(t) for t in texts]
    else:
        intent = [classify_intent(t)[0] for t in texts]
        role = [classify_role(t) for t in texts]
        distress = [classify_distress(t)[0] for t in texts]
        slots = [extract_slots(t) for t in texts]

    fidelity = 0
    for r, (named, scope) in zip(rows, slots):
        pred_set = set(resolve_action_set(named, scope, INVENTORY))
        gold_set = set(resolve_action_set(r["targets"], r["scope"], INVENTORY))
        fidelity += pred_set == gold_set

    neg = [(r, p) for r, p in zip(rows, intent) if r["hard_negative"]]
    pos = [(r, p) for r, p in zip(rows, intent)
           if r["intent"] == "stolen_confirmed"]
    ftr = sum(1 for _, p in neg if p in ACTIONABLE) / len(neg) if neg else 0.0
    mer = sum(1 for _, p in pos if p not in ACTIONABLE) / len(pos) if pos else 0.0

    return {
        "intent": intent, "role": role, "distress": distress,
        "scope": [s for _, s in slots],
        "fidelity": fidelity / len(rows),
        "ftr": ftr, "mer": mer,
        "n_neg": len(neg), "n_pos": len(pos),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    a = ap.parse_args()

    path = ROOT / "corpus" / f"{a.split}.jsonl"
    if not path.exists():
        sys.exit("Run scripts/build_dataset.py first.")
    rows = [json.loads(l) for l in open(path)]
    texts = [clean(r["text"]) for r in rows]
    n_seeds = len({r["seed_id"] for r in rows})

    live = models.status()
    print(f"SafeWord ablation - {a.split} split, "
          f"{len(rows)} messages, {n_seeds} seeds")
    print("backends enabled:", ", ".join(
        f"{k}={'model' if v else 'rules'}" for k, v in live.items()))

    R = run(texts, rows, use_rules=True)
    M = run(texts, rows, use_rules=False)

    tasks = [
        ("M1  intent", "intent", list(INTENTS)),
        ("M1b role", "role", list(ROLES)),
        ("M3  distress", "distress", list(DISTRESS)),
        ("M2  scope", "scope", list(SCOPES)),
    ]

    # ---- headline table ----
    W = 72
    print("\n" + "=" * W)
    print(f"{'module':<16}{'rules acc':>11}{'rules F1':>11}"
          f"{'model acc':>11}{'model F1':>11}{'delta F1':>11}")
    print("-" * W)
    for title, key, labels in tasks:
        gold = [r[key] for r in rows]
        ra, rf = macro_f1(gold, R[key], labels)
        ma, mf = macro_f1(gold, M[key], labels)
        print(f"{title:<16}{ra:>11.3f}{rf:>11.3f}"
              f"{ma:>11.3f}{mf:>11.3f}{mf - rf:>+11.3f}")
    print("=" * W)

    # ---- system level ----
    print("\nsystem-level  (a false positive locks the real owner out)")
    print(f"  {'metric':<26}{'rules':>10}{'models':>10}{'delta':>10}")
    for label, key, note in [
            ("false trigger rate", "ftr", f"n={R['n_neg']}"),
            ("missed emergency rate", "mer", f"n={R['n_pos']}"),
            ("command fidelity", "fidelity", "")]:
        print(f"  {label:<26}{R[key]:>10.3f}{M[key]:>10.3f}"
              f"{M[key] - R[key]:>+10.3f}   {note}")

    # ---- per class, with seed counts ----
    seeds = defaultdict(lambda: defaultdict(set))
    for r in rows:
        for key in ("intent", "role", "distress", "scope"):
            seeds[key][r[key]].add(r["seed_id"])

    for title, key, labels in tasks:
        gold = [r[key] for r in rows]
        print(f"\n{title} - per class (deployed backend)")
        print(f"  {'label':<24}{'P':>8}{'R':>8}{'F1':>8}{'msgs':>8}{'seeds':>8}")
        for lab, pr, rc, f1, n, ns in per_class(gold, M[key], labels, seeds[key]):
            flag = "  WEAK" if ns < 5 else ""
            print(f"  {lab:<24}{pr:>8.3f}{rc:>8.3f}{f1:>8.3f}"
                  f"{n:>8}{ns:>8}{flag}")

    # ---- confusions on the weakest module ----
    worst = min(tasks, key=lambda t: macro_f1([r[t[1]] for r in rows],
                                              M[t[1]], t[2])[1])
    title, key, _ = worst
    print(f"\ntop confusions - {title} (weakest module)")
    conf = Counter((g, p) for g, p in zip([r[key] for r in rows], M[key])
                   if g != p)
    for (g, p), n in conf.most_common(5):
        print(f"  {g}  ->  {p}   x{n}")

    print("\nWEAK marks a class with fewer than 5 distinct situations in this")
    print("split. Its F1 estimates a handful of samples, not a distribution.")