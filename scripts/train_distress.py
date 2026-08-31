#!/usr/bin/env python3
"""
M3 - fine-tune DistilBERT for distress classification.

calm | worried | panic

Distress is a SECURITY SIGNAL in this system, not decoration. High distress
plus strong verification escalates to Tier 2 and skips optional confirmation
turns. A calm, grammatically perfect "please initiate lockdown" at 3am is
treated as suspicious, because that is what an attacker's message looks like.

Note the annotation rule from SCHEMA.md: distress labels the WRITING, not the
situation. A calmly worded theft report is calm.

Replaces safeword.nlp.nlu.classify_distress (baseline: acc 0.574, macro-F1 0.289).

    python scripts/train_distress.py --epochs 4
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.nlp.cleaner import clean
from safeword.nlp.nlu import DISTRESS

MODEL_NAME = "distilbert-base-uncased"
OUTDIR = ROOT / "models" / "distress"
LABELS = list(DISTRESS)          # ordered: calm, worried, panic
L2I = {l: i for i, l in enumerate(LABELS)}

BASELINE_ACC, BASELINE_MACRO = 0.574, 0.289


def device():
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


class DistressData(Dataset):
    def __init__(self, path, tok, max_len=96):
        rows = [json.loads(l) for l in open(path)]
        self.texts = [clean(r["text"]) for r in rows]
        self.labels = [L2I[r["distress"]] for r in rows]
        self.tok, self.max_len = tok, max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        enc = self.tok(self.texts[i], truncation=True, padding="max_length",
                       max_length=self.max_len, return_tensors="pt")
        return {"input_ids": enc["input_ids"][0],
                "attention_mask": enc["attention_mask"][0],
                "labels": torch.tensor(self.labels[i])}


def evaluate(model, loader, dev):
    model.eval()
    gold, pred = [], []
    with torch.no_grad():
        for b in loader:
            out = model(input_ids=b["input_ids"].to(dev),
                        attention_mask=b["attention_mask"].to(dev))
            pred += out.logits.argmax(-1).cpu().tolist()
            gold += b["labels"].tolist()
    return gold, pred


def scores(gold, pred):
    f1s = []
    for i in range(len(LABELS)):
        tp = sum(1 for g, p in zip(gold, pred) if g == i and p == i)
        fp = sum(1 for g, p in zip(gold, pred) if g != i and p == i)
        fn = sum(1 for g, p in zip(gold, pred) if g == i and p != i)
        if tp + fn:
            pr = tp / (tp + fp) if tp + fp else 0.0
            rc = tp / (tp + fn)
            f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    acc = sum(g == p for g, p in zip(gold, pred)) / len(gold)
    return acc, (sum(f1s) / len(f1s) if f1s else 0.0)


def report(gold, pred, title):
    print(f"\n{title}")
    print(f"  {'label':<24}{'P':>7}{'R':>7}{'F1':>7}{'n':>6}")
    for i, lab in enumerate(LABELS):
        tp = sum(1 for g, p in zip(gold, pred) if g == i and p == i)
        fp = sum(1 for g, p in zip(gold, pred) if g != i and p == i)
        fn = sum(1 for g, p in zip(gold, pred) if g == i and p != i)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        if tp + fn:
            print(f"  {lab:<24}{pr:>7.3f}{rc:>7.3f}{f1:>7.3f}{tp+fn:>6}")
    acc, macro = scores(gold, pred)
    print(f"  {'accuracy':<24}{acc:>7.3f}   macro-F1 {macro:.3f}")
    return acc, macro


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    a = ap.parse_args()

    torch.manual_seed(42)
    dev = device()
    print(f"device: {dev}")

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    tr = DataLoader(DistressData(ROOT / "corpus" / "train.jsonl", tok),
                    batch_size=a.batch, shuffle=True)
    dv = DataLoader(DistressData(ROOT / "corpus" / "dev.jsonl", tok), batch_size=32)
    te = DataLoader(DistressData(ROOT / "corpus" / "test.jsonl", tok), batch_size=32)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABELS)).to(dev)

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr)
    steps = len(tr) * a.epochs
    sched = get_linear_schedule_with_warmup(opt, int(steps * 0.1), steps)

    best_macro, best_state = -1.0, None
    for ep in range(1, a.epochs + 1):
        model.train()
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

        g, p = evaluate(model, dv, dev)
        acc, macro = scores(g, p)
        print(f"epoch {ep}  loss {total/len(tr):.4f}  dev acc {acc:.3f}  dev macro-F1 {macro:.3f}")

        # Select on DEV, never on test.
        if macro > best_macro:
            best_macro = macro
            best_state = {k: v.detach().cpu().clone()
                          for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    print(f"\nbest dev macro-F1: {best_macro:.3f}")

    g, p = evaluate(model, te, dev)
    acc, macro = report(g, p, "TEST - DistilBERT")
    print(f"\nbaseline for comparison:  accuracy {BASELINE_ACC:.3f}   macro-F1 {BASELINE_MACRO:.3f}")
    print(f"delta:                    {acc-BASELINE_ACC:+.3f}        {macro-BASELINE_MACRO:+.3f}")

    print("\nTop confusions")
    conf = Counter((LABELS[x], LABELS[y]) for x, y in zip(g, p) if x != y)
    for (gl, pl), n in conf.most_common(6):
        print(f"  {gl}  ->  {pl}   x{n}")

    # Distress is ORDINAL: calm < worried < panic. A calm/worried confusion is
    # a one-step error; calm/panic is two steps and flips the tier policy.
    # Plain accuracy treats both as equally wrong, which they are not.
    off_by_one = sum(1 for x, y in zip(g, p) if abs(x - y) == 1)
    off_by_two = sum(1 for x, y in zip(g, p) if abs(x - y) == 2)
    n = len(g)
    print("\nordinal error profile")
    print(f"  adjacent (1 step)       {off_by_one/n:>7.3f}   (calm<->worried, worried<->panic)")
    print(f"  extreme  (2 steps)      {off_by_two/n:>7.3f}   (calm<->panic, flips tier policy)")

    # The security-relevant direction: a genuine panic message read as calm
    # loses its escalation, so the victim waits through confirmation turns
    # they should have skipped.
    ip = L2I["panic"]
    panic_as_calm = sum(1 for x, y in zip(g, p) if x == ip and y == L2I["calm"])
    n_panic = sum(1 for x in g if x == ip)
    if n_panic:
        print(f"  panic read as calm      {panic_as_calm/n_panic:>7.3f}   "
              f"(loses escalation, n={n_panic})")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTDIR)
    tok.save_pretrained(OUTDIR)
    print(f"\nsaved -> {OUTDIR}")