#!/usr/bin/env python3
"""
Measure the rule-based baselines on the test split.

Run this NOW, before training anything. These numbers are the comparison
column in your ablation table, and you cannot reconstruct them later once the
rules are replaced.

    python scripts/eval_baseline.py
    python scripts/eval_baseline.py --split dev
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.nlp.cleaner import clean
from safeword.nlp.nlu import (classify_distress, classify_intent, classify_role,
                              extract_slots, resolve_action_set)

INVENTORY = ["telegram", "whatsapp", "instagram", "demobank", "gmail"]


def prf(gold, pred, labels):
    """Per-class precision / recall / F1 plus macro and accuracy."""
    rows, f1s = [], []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        rows.append((lab, pr, rc, f1, tp + fn))
        if tp + fn:
            f1s.append(f1)
    acc = sum(g == p for g, p in zip(gold, pred)) / len(gold)
    return rows, acc, (sum(f1s) / len(f1s) if f1s else 0.0)


def report(title, gold, pred, labels):
    rows, acc, macro = prf(gold, pred, labels)
    print(f"\n{title}")
    print(f"  {'label':<24}{'P':>7}{'R':>7}{'F1':>7}{'n':>6}")
    for lab, p, r, f, n in rows:
        print(f"  {lab:<24}{p:>7.3f}{r:>7.3f}{f:>7.3f}{n:>6}")
    print(f"  {'accuracy':<24}{acc:>7.3f}   macro-F1 {macro:.3f}")
    return acc, macro


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    a = ap.parse_args()

    path = ROOT / "corpus" / f"{a.split}.jsonl"
    if not path.exists():
        sys.exit("Run scripts/build_dataset.py first.")
    rows = [json.loads(l) for l in open(path)]
    print(f"Evaluating rule-based baselines on {a.split} ({len(rows)} messages)")

    # M0 feeds everything else, so evaluate the pipeline as the models will see it
    texts = [clean(r["text"]) for r in rows]

    g_int = [r["intent"] for r in rows]
    p_int = [classify_intent(t)[0] for t in texts]
    report("M1 intent", g_int, p_int, sorted(set(g_int) | set(p_int)))

    g_role = [r["role"] for r in rows]
    p_role = [classify_role(t) for t in texts]
    report("M1b reporter role", g_role, p_role, ["owner", "proxy", "mere_mention"])

    g_dis = [r["distress"] for r in rows]
    p_dis = [classify_distress(t)[0] for t in texts]
    report("M3 distress", g_dis, p_dis, ["calm", "worried", "panic"])

    g_sc = [r["scope"] for r in rows]
    p_sc = [extract_slots(t)[1] for t in texts]
    report("M2 scope", g_sc, p_sc, ["all", "only", "except"])

    # --- system-level: the metrics that actually matter ---
    print("\nsystem-level")
    exact = 0
    for r, t in zip(rows, texts):
        named, scope = extract_slots(t)
        pred_set = set(resolve_action_set(named, scope, INVENTORY))
        gold_set = set(resolve_action_set(r["targets"], r["scope"], INVENTORY))
        exact += pred_set == gold_set
    print(f"  command fidelity        {exact/len(rows):>7.3f}"
          "   (action set exactly matches gold)")

    ACTIONABLE = {"stolen_confirmed", "lost_uncertain", "partial_lockdown"}
    neg = [(r, p) for r, p in zip(rows, p_int) if r["hard_negative"]]
    ftr = sum(1 for r, p in neg if p in ACTIONABLE) / len(neg) if neg else 0.0
    pos = [(r, p) for r, p in zip(rows, p_int)
           if r["intent"] == "stolen_confirmed"]
    mer = sum(1 for r, p in pos if p not in ACTIONABLE) / len(pos) if pos else 0.0
    print(f"  false trigger rate      {ftr:>7.3f}   (target ~0, n={len(neg)})")
    print(f"  missed emergency rate   {mer:>7.3f}   (n={len(pos)})")

    print("\nTop confusions (M1)")
    conf = Counter((g, p) for g, p in zip(g_int, p_int) if g != p)
    for (g, p), n in conf.most_common(6):
        print(f"  {g}  ->  {p}   x{n}")