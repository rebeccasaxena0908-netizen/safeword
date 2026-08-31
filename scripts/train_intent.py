#!/usr/bin/env python3
"""
M1 - fine-tune DistilBERT for intent classification.

Replaces safeword.nlp.nlu.classify_intent, which stays in the codebase as the
baseline row in your ablation table.

Runs on Apple Silicon via the MPS backend. No CUDA anywhere.

    python scripts/train_intent.py                 # train and evaluate
    python scripts/train_intent.py --epochs 6
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from safeword.nlp.cleaner import clean
from safeword.nlp.nlu import INTENTS

MODEL_NAME = "distilbert-base-uncased"
OUTDIR = ROOT / "models" / "intent"
LABELS = list(INTENTS)
L2I = {l: i for i, l in enumerate(LABELS)}


def device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class IntentData(Dataset):
    def __init__(self, path, tok, max_len=96):
        rows = [json.loads(l) for l in open(path)]
        # Clean first. The model must see what the pipeline will actually
        # hand it at inference time, not the raw mail with signatures.
        self.texts = [clean(r["text"]) for r in rows]
        self.labels = [L2I[r["intent"]] for r in rows]
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


def report(gold, pred, title):
    print(f"\n{title}")
    print(f"  {'label':<24}{'P':>7}{'R':>7}{'F1':>7}{'n':>6}")
    f1s = []
    for i, lab in enumerate(LABELS):
        tp = sum(1 for g, p in zip(gold, pred) if g == i and p == i)
        fp = sum(1 for g, p in zip(gold, pred) if g != i and p == i)
        fn = sum(1 for g, p in zip(gold, pred) if g == i and p != i)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        if tp + fn:
            f1s.append(f1)
            print(f"  {lab:<24}{pr:>7.3f}{rc:>7.3f}{f1:>7.3f}{tp+fn:>6}")
    acc = sum(g == p for g, p in zip(gold, pred)) / len(gold)
    macro = sum(f1s) / len(f1s) if f1s else 0.0
    print(f"  {'accuracy':<24}{acc:>7.3f}   macro-F1 {macro:.3f}")
    return acc, macro


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    a = ap.parse_args()

    torch.manual_seed(42)
    dev = device()
    print(f"device: {dev}")

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    tr = DataLoader(IntentData(ROOT / "corpus" / "train.jsonl", tok),
                    batch_size=a.batch, shuffle=True)
    dv = DataLoader(IntentData(ROOT / "corpus" / "dev.jsonl", tok), batch_size=32)
    te = DataLoader(IntentData(ROOT / "corpus" / "test.jsonl", tok), batch_size=32)

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
        acc = sum(x == y for x, y in zip(g, p)) / len(g)
        f1s = []
        for i in range(len(LABELS)):
            tp = sum(1 for x, y in zip(g, p) if x == i and y == i)
            fp = sum(1 for x, y in zip(g, p) if x != i and y == i)
            fn = sum(1 for x, y in zip(g, p) if x == i and y != i)
            if tp + fn:
                pr = tp / (tp + fp) if tp + fp else 0.0
                rc = tp / (tp + fn)
                f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
        macro = sum(f1s) / len(f1s)
        print(f"epoch {ep}  loss {total/len(tr):.4f}  dev acc {acc:.3f}  dev macro-F1 {macro:.3f}")

        # Select on DEV, never on test. Selecting on test is how you end up
        # reporting a number you cannot reproduce.
        if macro > best_macro:
            best_macro = macro
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    print(f"\nbest dev macro-F1: {best_macro:.3f}")

    g, p = evaluate(model, te, dev)
    acc, macro = report(g, p, "TEST - DistilBERT")

    print("\nbaseline for comparison:  accuracy 0.413   macro-F1 0.358")
    print(f"delta:                    {acc-0.413:+.3f}        {macro-0.358:+.3f}")

    from collections import Counter
    print("\nTop confusions")
    conf = Counter((LABELS[x], LABELS[y]) for x, y in zip(g, p) if x != y)
    for (gl, pl), n in conf.most_common(6):
        print(f"  {gl}  ->  {pl}   x{n}")

        

    OUTDIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTDIR)
    tok.save_pretrained(OUTDIR)
    print(f"\nsaved -> {OUTDIR}")