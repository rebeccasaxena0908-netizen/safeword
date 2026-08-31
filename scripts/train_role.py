#!/usr/bin/env python3
"""
M1b - fine-tune DistilBERT for reporter-role classification.

owner        - first person, the account holder reporting their own device
proxy        - a third party reporting on the owner's behalf
mere_mention - theft or loss discussed, but no action requested

This is the novel module: a pragmatics problem in reported speech, with a
direct security consequence. proxy messages route to the strictest
verification path and cap at Tier 1; mere_mention is the hard negative that
holds the false-trigger rate down.

Replaces safeword.nlp.nlu.classify_role (rule baseline: acc 0.584, macro-F1 0.472).

    python scripts/train_role.py --epochs 5
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
from safeword.nlp.nlu import ROLES

MODEL_NAME = "distilbert-base-uncased"
OUTDIR = ROOT / "models" / "role"
LABELS = list(ROLES)
L2I = {l: i for i, l in enumerate(LABELS)}

BASELINE_ACC, BASELINE_MACRO = 0.584, 0.472


def device():
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


class RoleData(Dataset):
    def __init__(self, path, tok, max_len=96):
        rows = [json.loads(l) for l in open(path)]
        self.texts = [clean(r["text"]) for r in rows]
        self.labels = [L2I[r["role"]] for r in rows]
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
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    a = ap.parse_args()

    torch.manual_seed(42)
    dev = device()
    print(f"device: {dev}")

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    tr = DataLoader(RoleData(ROOT / "corpus" / "train.jsonl", tok),
                    batch_size=a.batch, shuffle=True)
    dv = DataLoader(RoleData(ROOT / "corpus" / "dev.jsonl", tok), batch_size=32)
    te = DataLoader(RoleData(ROOT / "corpus" / "test.jsonl", tok), batch_size=32)

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

    # Security-relevant error: an owner misread as proxy is capped at Tier 1
    # and cannot complete a real lockdown. A proxy misread as owner skips the
    # strictest verification path. Both matter more than aggregate accuracy.
    o, px = L2I["owner"], L2I["proxy"]
    owner_as_proxy = sum(1 for x, y in zip(g, p) if x == o and y == px)
    proxy_as_owner = sum(1 for x, y in zip(g, p) if x == px and y == o)
    n_owner = sum(1 for x in g if x == o)
    n_proxy = sum(1 for x in g if x == px)
    print("\nsecurity-relevant errors")
    print(f"  owner read as proxy     {owner_as_proxy/n_owner:>7.3f}   "
          f"(real owner capped at Tier 1, n={n_owner})")
    print(f"  proxy read as owner     {proxy_as_owner/n_proxy:>7.3f}   "
          f"(skips strictest verification, n={n_proxy})")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTDIR)
    tok.save_pretrained(OUTDIR)
    print(f"\nsaved -> {OUTDIR}")