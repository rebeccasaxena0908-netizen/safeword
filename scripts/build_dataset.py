#!/usr/bin/env python3
"""
Step 4: split into train/dev/test and report composition.

THE LEAKAGE RULE. Every variant derived from one seed lands in the SAME split.
Splitting by message instead of by seed lets a paraphrase of a training example
appear in test, which inflates accuracy substantially and is the single most
common way student NLP projects report numbers they cannot reproduce. This
script groups on seed_id and will refuse to produce a split that violates it.

STATISTICAL POWER. Augmentation inflates message counts without adding
statistical power: a test class showing n=65 may rest on three underlying
situations, and its F1 is then an estimate over three samples. The final
section of this report exists so that is never invisible again.

The imposter set is written separately and is held out of all three splits -
it exists only to evaluate stylometry (M4b).

    python scripts/build_dataset.py
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "corpus" / "build"))
IN = ROOT / "corpus" / "raw" / "augmented.jsonl"
OUTDIR = ROOT / "corpus"

RATIOS = {"train": 0.70, "dev": 0.15, "test": 0.15}
MIN_TEST_SEEDS = 5


def main():
    if not IN.exists():
        sys.exit("Run expand_corpus.py then augment_corpus.py first.")

    rows = [json.loads(l) for l in open(IN)]
    by_seed = defaultdict(list)
    for r in rows:
        by_seed[r["seed_id"]].append(r)

    # Stratify seeds by intent so rare classes appear in every split.
    seeds_by_intent = defaultdict(list)
    for sid, group in by_seed.items():
        seeds_by_intent[group[0]["intent"]].append(sid)

    rng = random.Random(13)
    split_of = {}
    for intent, sids in seeds_by_intent.items():
        rng.shuffle(sids)
        n = len(sids)
        n_tr = max(1, round(n * RATIOS["train"]))
        n_dv = max(1, round(n * RATIOS["dev"])) if n >= 3 else 0
        for i, sid in enumerate(sids):
            split_of[sid] = ("train" if i < n_tr
                             else "dev" if i < n_tr + n_dv else "test")

    splits = defaultdict(list)
    for sid, group in by_seed.items():
        splits[split_of[sid]].extend(group)

    # Enforce the leakage rule rather than trusting it.
    seen = {}
    for name, rs in splits.items():
        for r in rs:
            prev = seen.setdefault(r["seed_id"], name)
            if prev != name:
                sys.exit(f"LEAK: seed {r['seed_id']} in both {prev} and {name}")

    OUTDIR.mkdir(exist_ok=True)
    for name, rs in splits.items():
        rng.shuffle(rs)
        with open(OUTDIR / f"{name}.jsonl", "w") as fh:
            for r in rs:
                fh.write(json.dumps(r) + "\n")

    import seeds as seedmod
    with open(OUTDIR / "imposters.jsonl", "w") as fh:
        for i, t in enumerate(seedmod.IMPOSTERS):
            fh.write(json.dumps({"text": t, "author": "imposter",
                                 "id": f"imp{i:03d}"}) + "\n")

    # ---- split sizes ----
    print(f"{'split':<8}{'msgs':>7}{'seeds':>8}")
    for name in ("train", "dev", "test"):
        sids = {r["seed_id"] for r in splits[name]}
        print(f"{name:<8}{len(splits[name]):>7}{len(sids):>8}")
    print(f"{'total':<8}{sum(len(v) for v in splits.values()):>7}"
          f"{len(by_seed):>8}")

    # ---- intent distribution ----
    print("\nintent distribution (train)")
    c = Counter(r["intent"] for r in splits["train"])
    for k, v in c.most_common():
        print(f"  {k:<22}{v:>6}  {v/len(splits['train']):>6.1%}")

    # ---- composition checks ----
    print("\ncomposition checks (target -> actual)")
    hn = sum(r["hard_negative"] for r in rows) / len(rows)
    pr = sum(r["role"] == "proxy" for r in rows) / len(rows)
    hi = sum(r["lang"] == "hi-en" for r in rows) / len(rows)
    fu = sum(r["aug"] == "furniture" or bool(r.get("furniture"))
             for r in rows) / len(rows)
    ex = sum(r["scope"] == "except" for r in rows)
    on = sum(r["scope"] == "only" for r in rows)
    for label, target, actual in [
            ("hard negatives", 0.25, hn), ("proxy role", 0.12, pr),
            ("code-mixed", 0.15, hi), ("with furniture", 0.30, fu)]:
        flag = "ok " if actual >= target * 0.9 else "LOW"
        print(f"  {flag} {label:<18}{target:>6.0%} -> {actual:>6.1%}")
    print(f"  {'ok ' if ex >= 60 else 'LOW'} scope=except         60 -> {ex}")
    print(f"  {'ok ' if on >= 60 else 'LOW'} scope=only           60 -> {on}")

    print(f"\nimposter set: {len(seedmod.IMPOSTERS)} (held out of all splits)")

    # ---- statistical power ----
    # Message counts are misleading: 65 messages can be 3 situations paraphrased.
    # Per-class F1 is only as trustworthy as the SEED count behind it.
    print("\nstatistical power (test split)")
    print(f"  {'intent':<24}{'seeds':>7}{'msgs':>7}")
    test_seeds = defaultdict(set)
    test_msgs = Counter()
    for r in splits["test"]:
        test_seeds[r["intent"]].add(r["seed_id"])
        test_msgs[r["intent"]] += 1
    for intent in sorted(test_seeds, key=lambda k: len(test_seeds[k])):
        n = len(test_seeds[intent])
        flag = "WEAK" if n < MIN_TEST_SEEDS else "    "
        print(f"  {flag} {intent:<19}{n:>7}{test_msgs[intent]:>7}")

    weak = [k for k, v in test_seeds.items() if len(v) < MIN_TEST_SEEDS]
    if weak:
        print(f"\n  {len(weak)} class(es) below {MIN_TEST_SEEDS} test seeds: "
              f"{', '.join(sorted(weak))}")
        print("  Their F1 estimates a handful of situations, not a distribution.")
        print("  Report seed counts alongside F1, or treat these as anecdotal.")

    print(f"\nfiles -> {OUTDIR}/")


if __name__ == "__main__":
    main()