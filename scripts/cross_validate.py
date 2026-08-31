#!/usr/bin/env python3
"""
K-fold cross-validation over SEEDS, not messages.

WHY THIS EXISTS. The single 70/15/15 split leaves 54 seeds in test, and
per-class F1 rests on between 5 and 17 distinct situations. A number computed
from five situations is an anecdote with a decimal point. Cross-validation
uses every seed as test exactly once, so each class is evaluated on ALL its
seeds across folds, and the fold-to-fold standard deviation shows how much
the single-split number could have moved by luck of the partition.

The leakage rule still holds inside every fold: all variants of one seed go to
the same side. Folds are built over seed ids and assigned round-robin within
each label, so a class with only five seeds still lands one in each of five
folds rather than clustering by chance.

Reports mean +/- std across folds for both backends. That is the table that
belongs in the results section - a single split cannot support the claims.

    python scripts/cross_validate.py --task intent --folds 5
    python scripts/cross_validate.py --task intent --folds 5 --model
"""
import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.nlp.cleaner import clean_rules
from safeword.nlp.nlu import (DISTRESS, INTENTS, ROLES, SCOPES,
                              classify_distress_rules, classify_intent_rules,
                              classify_role_rules, extract_slots_rules)

TASKS = {
    "intent": (list(INTENTS), lambda t: classify_intent_rules(t)[0]),
    "role": (list(ROLES), classify_role_rules),
    "distress": (list(DISTRESS), lambda t: classify_distress_rules(t)[0]),
    "scope": (list(SCOPES), lambda t: extract_slots_rules(t)[1]),
}


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
    acc = sum(g == p for g, p in zip(gold, pred)) / len(gold) if gold else 0.0
    return acc, (sum(f1s) / len(f1s) if f1s else 0.0)


def per_class_f1(gold, pred, lab):
    tp = sum(1 for g, p in zip(gold, pred) if g == lab and p == lab)
    fp = sum(1 for g, p in zip(gold, pred) if g != lab and p == lab)
    fn = sum(1 for g, p in zip(gold, pred) if g == lab and p != lab)
    if not (tp + fn):
        return None
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn)
    return 2 * pr * rc / (pr + rc) if pr + rc else 0.0


def build_folds(rows, task, k, seed=13):
    """Stratified k-fold over seed ids. Every variant of a seed stays together."""
    import random
    by_seed = defaultdict(list)
    for r in rows:
        by_seed[r["seed_id"]].append(r)

    seeds_by_label = defaultdict(list)
    for sid, group in by_seed.items():
        seeds_by_label[group[0][task]].append(sid)

    rng = random.Random(seed)
    fold_of = {}
    for label, sids in seeds_by_label.items():
        rng.shuffle(sids)
        for i, sid in enumerate(sids):
            fold_of[sid] = i % k

    folds = [[] for _ in range(k)]
    for sid, group in by_seed.items():
        folds[fold_of[sid]].extend(group)
    return folds, by_seed


def train_and_predict(train_rows, test_rows, task, labels, epochs, fold_no):
    """Fine-tune DistilBERT on this fold's training portion and predict test."""
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              get_linear_schedule_with_warmup)

    dev = (torch.device("mps") if torch.backends.mps.is_available()
           else torch.device("cpu"))
    l2i = {l: i for i, l in enumerate(labels)}
    tok = AutoTokenizer.from_pretrained("distilbert-base-uncased")

    class D(Dataset):
        def __init__(self, rows):
            # clean_rules, not clean: the CRF is trained on the same corpus,
            # so using it here would leak M0's training data into the folds.
            self.t = [clean_rules(r["text"]) for r in rows]
            self.y = [l2i[r[task]] for r in rows]

        def __len__(self):
            return len(self.t)

        def __getitem__(self, i):
            e = tok(self.t[i], truncation=True, padding="max_length",
                    max_length=96, return_tensors="pt")
            return {"input_ids": e["input_ids"][0],
                    "attention_mask": e["attention_mask"][0],
                    "labels": torch.tensor(self.y[i])}

    tr = DataLoader(D(train_rows), batch_size=16, shuffle=True)
    te = DataLoader(D(test_rows), batch_size=32)

    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=len(labels)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-5)
    steps = len(tr) * epochs
    sched = get_linear_schedule_with_warmup(opt, int(steps * 0.1), steps)

    model.train()
    for ep in range(epochs):
        t0 = time.time()
        total = 0.0
        for b in tr:
            opt.zero_grad()
            out = model(input_ids=b["input_ids"].to(dev),
                        attention_mask=b["attention_mask"].to(dev),
                        labels=b["labels"].to(dev))
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            total += out.loss.item()
        print(f"    fold {fold_no} epoch {ep+1}/{epochs}  "
              f"loss {total/len(tr):.4f}  {time.time()-t0:.0f}s", flush=True)

    model.eval()
    pred = []
    with torch.no_grad():
        for b in te:
            out = model(input_ids=b["input_ids"].to(dev),
                        attention_mask=b["attention_mask"].to(dev))
            pred += out.logits.argmax(-1).cpu().tolist()
    return [labels[i] for i in pred]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="intent", choices=list(TASKS))
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--model", action="store_true",
                    help="train DistilBERT per fold (slow) instead of rules only")
    ap.add_argument("--epochs", type=int, default=3)
    a = ap.parse_args()

    labels, rule_fn = TASKS[a.task]

    # Pool every split back together - cross-validation makes its own folds.
    rows = []
    for name in ("train", "dev", "test"):
        path = ROOT / "corpus" / f"{name}.jsonl"
        if path.exists():
            rows += [json.loads(l) for l in open(path)]
    if not rows:
        sys.exit("Run scripts/build_dataset.py first.")

    folds, by_seed = build_folds(rows, a.task, a.folds)
    print(f"{a.task}: {len(rows)} messages, {len(by_seed)} seeds, {a.folds} folds")
    print("fold sizes (msgs/seeds):", ", ".join(
        f"{len(f)}/{len({r['seed_id'] for r in f})}" for f in folds))
    if a.model:
        print(f"training DistilBERT per fold, {a.epochs} epochs - "
              f"expect a few minutes each\n")
    else:
        print("rule baseline only (add --model to also cross-validate DistilBERT)\n")

    started = time.time()
    rule_acc, rule_f1 = [], []
    model_acc, model_f1 = [], []
    per_class = defaultdict(lambda: {"rules": [], "model": []})

    for i, fold in enumerate(folds):
        train_rows = [r for j, f in enumerate(folds) if j != i for r in f]
        gold = [r[a.task] for r in fold]
        texts = [clean_rules(r["text"]) for r in fold]

        rp = [rule_fn(t) for t in texts]
        acc, f1 = macro_f1(gold, rp, labels)
        rule_acc.append(acc)
        rule_f1.append(f1)
        for lab in labels:
            v = per_class_f1(gold, rp, lab)
            if v is not None:
                per_class[lab]["rules"].append(v)

        line = f"fold {i+1}  rules acc {acc:.3f}  F1 {f1:.3f}"

        if a.model:
            mp = train_and_predict(train_rows, fold, a.task, labels,
                                   a.epochs, i + 1)
            macc, mf1 = macro_f1(gold, mp, labels)
            model_acc.append(macc)
            model_f1.append(mf1)
            for lab in labels:
                v = per_class_f1(gold, mp, lab)
                if v is not None:
                    per_class[lab]["model"].append(v)
            line += f"   |   model acc {macc:.3f}  F1 {mf1:.3f}"

        print(line, flush=True)

    def ms(xs):
        return (statistics.fmean(xs),
                statistics.stdev(xs) if len(xs) > 1 else 0.0)

    print("\n" + "=" * 58)
    print(f"{a.task} - {a.folds}-fold cross-validation over seeds")
    print("-" * 58)
    m, s = ms(rule_acc)
    print(f"  rules  accuracy   {m:.3f} +/- {s:.3f}")
    m, s = ms(rule_f1)
    print(f"  rules  macro-F1   {m:.3f} +/- {s:.3f}")
    if a.model:
        m, s = ms(model_acc)
        print(f"  model  accuracy   {m:.3f} +/- {s:.3f}")
        m, s = ms(model_f1)
        print(f"  model  macro-F1   {m:.3f} +/- {s:.3f}")
    print("=" * 58)

    print(f"\nper-class F1 across folds{' (model)' if a.model else ' (rules)'}")
    print(f"  {'label':<24}{'mean':>8}{'std':>8}{'folds':>7}")
    key = "model" if a.model else "rules"
    for lab in labels:
        vals = per_class[lab][key]
        if not vals:
            continue
        m, s = ms(vals)
        flag = "  UNSTABLE" if s > 0.15 else ""
        print(f"  {lab:<24}{m:>8.3f}{s:>8.3f}{len(vals):>7}{flag}")

    print(f"\nelapsed {time.time() - started:.0f}s")
    print("\nStd across folds is how much the single-split number could have")
    print("moved by luck of the partition. UNSTABLE marks std > 0.15 - report")
    print("those as a range, never as a point estimate.")