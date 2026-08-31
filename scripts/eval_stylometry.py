#!/usr/bin/env python3
"""
M4b - evaluate the stylometry baseline against the held-out imposter set.

THE THREAT MODEL. An attacker who has compromised one of the five Emergency
Accounts passes the sender gate, passes SPF/DKIM, and knows the owner's name.
Every passive signal is inherited. The only things they cannot fake are the
challenge answer and the owner's writing style. This module measures the
second one.

The imposter set was written in week 2 and held out of every train/dev/test
split precisely so it could be used here without contamination.

Reports ROC-AUC, Equal Error Rate, and a threshold sweep - the numbers needed
to choose tau defensibly rather than by eye.

    python scripts/eval_stylometry.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.config import load_profile
from safeword.nlp.cleaner import clean
from safeword.verify.trust import stylometry_score


def roc_auc(pos_scores, neg_scores):
    """
    Probability that a random genuine message scores above a random imposter.
    Computed directly from pairwise comparisons - no sklearn needed, and the
    definition is clearer this way.
    """
    wins = ties = 0
    for p in pos_scores:
        for n in neg_scores:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    total = len(pos_scores) * len(neg_scores)
    return (wins + 0.5 * ties) / total if total else 0.0


def sweep(pos_scores, neg_scores, steps=41):
    """FAR/FRR at every threshold, plus the equal error rate."""
    rows = []
    for i in range(steps):
        tau = i / (steps - 1)
        # False accept: an imposter scoring at or above tau gets through.
        far = sum(1 for s in neg_scores if s >= tau) / len(neg_scores)
        # False reject: a genuine owner scoring below tau is challenged again.
        frr = sum(1 for s in pos_scores if s < tau) / len(pos_scores)
        rows.append((tau, far, frr))
    eer = min(rows, key=lambda r: abs(r[1] - r[2]))
    return rows, eer


if __name__ == "__main__":
    profile = load_profile()
    corpus = profile.get("writing_samples", [])
    if not corpus:
        sys.exit("No writing_samples in config/profile.yaml - nothing to compare against.")

    imp_path = ROOT / "corpus" / "imposters.jsonl"
    if not imp_path.exists():
        sys.exit("Run scripts/build_dataset.py first to write the imposter set.")
    imposters = [json.loads(l)["text"] for l in open(imp_path)]

    # Genuine messages: owner-authored, first-person, from the test split.
    # Excluding proxy and mere_mention - a friend's writing style is not the
    # owner's, so scoring those here would measure the wrong thing.
    test = [json.loads(l) for l in open(ROOT / "corpus" / "test.jsonl")]
    genuine = [clean(r["text"]) for r in test if r["role"] == "owner"][:300]

    pos = [s for s in (stylometry_score(t, corpus) for t in genuine) if s is not None]
    neg = [s for s in (stylometry_score(t, corpus) for t in imposters) if s is not None]

    print(f"enrolled writing samples : {len(corpus)}")
    print(f"genuine owner messages   : {len(pos)}")
    print(f"held-out imposters       : {len(neg)}")

    print(f"\nscore distribution")
    print(f"  {'':<12}{'min':>8}{'mean':>8}{'max':>8}")
    print(f"  {'genuine':<12}{min(pos):>8.3f}{sum(pos)/len(pos):>8.3f}{max(pos):>8.3f}")
    print(f"  {'imposter':<12}{min(neg):>8.3f}{sum(neg)/len(neg):>8.3f}{max(neg):>8.3f}")

    auc = roc_auc(pos, neg)
    rows, (eer_tau, eer_far, eer_frr) = sweep(pos, neg)
    print(f"\nROC-AUC                  : {auc:.3f}"
          "   (0.5 = no signal, 1.0 = perfect separation)")
    print(f"Equal error rate         : {(eer_far + eer_frr) / 2:.3f} at tau={eer_tau:.2f}")

    print("\nthreshold sweep")
    print(f"  {'tau':>6}{'FAR':>9}{'FRR':>9}   FAR = imposter accepted, "
          "FRR = owner challenged again")
    for tau, far, frr in rows[::4]:
        mark = "  <-- EER" if abs(tau - eer_tau) < 1e-9 else ""
        print(f"  {tau:>6.2f}{far:>9.3f}{frr:>9.3f}{mark}")

    # Operating point. The costs are asymmetric in BOTH directions here, which
    # is why this is not simply "minimise FAR": a false accept lets an attacker
    # in a compromised mailbox reach Tier 2, but a false reject means a genuine
    # victim is stuck answering challenge questions during a real theft.
    # Stylometry is one of four fused signals and never decides alone, so the
    # sensible operating point is where FAR is near zero without FRR climbing
    # past roughly a fifth.
    usable = [r for r in rows if r[1] <= 0.01 and r[2] <= 0.25]
    print("\noperating point")
    if usable:
        tau, far, frr = min(usable, key=lambda r: r[2])
        print(f"  tau={tau:.2f}  FAR={far:.3f}  FRR={frr:.3f}")
        print("  Lowest owner-friction threshold that still admits ~no imposters.")
    else:
        print("  No threshold achieves FAR<=0.01 with FRR<=0.25.")
        print("  The baseline does not separate these populations well enough")
        print("  to carry weight on its own - report it as a limitation and")
        print("  rely on the challenge answer as the active factor.")

    print(f"\nNOTE: {len(neg)} imposters is a small evaluation set. Treat AUC as")
    print("indicative. Expanding the imposter set is future work.")