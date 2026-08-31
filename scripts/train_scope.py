#!/usr/bin/env python3
"""
M2 - scope classification: all | only | except.

Framed as sentence classification rather than token-level NER, deliberately.
The action set is determined by two things: WHICH services are named, and
WHETHER the sentence includes or excludes them. Service names are a closed
vocabulary of five strings - a gazetteer handles them at ~100% and a model
would add nothing. The scope operator is the part that carries the semantics,
and it is where "lock everything EXCEPT my email" and "lock everything,
ESPECIALLY my email" diverge into opposite action sets.

HEADROOM WARNING. The rule baseline scores 0.946 on scope and 0.946 on
command fidelity, because scope is triggered by a small closed set of words
that rules match reliably. This model may not beat it. That is a real result:
it shows which sub-problems need learned models and which do not, and it is
worth reporting either way.

    python scripts/train_scope.py --epochs 4
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
from safeword.nlp.nlu import _find_targets, resolve_action_set

MODEL_NAME = "distilbert-base-uncased"
OUTDIR = ROOT / "models" / "scope"
LABELS = ["all", "only", "except"]
L2I = {l: i for i, l in enumerate(LABELS)}
INVENTORY = ["telegram", "whatsapp", "instagram", "demobank", "gmail"]

BASELINE_ACC, BASELINE_MACRO, BASELINE_FIDELITY = 0.946, 0.486, 0.946


def device():
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


class ScopeData(Dataset):
    def __init__(self, path, tok, max_len=96):
        self.rows = [json.loads(l) for l in open(path)]
        self.texts = [clean(r["text"]) for r in self.rows]
        self.labels = [L2I[r["scope"]] for r in self.rows]
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
    tr_ds = ScopeData(ROOT / "corpus" / "train.jsonl", tok)
    te_ds = ScopeData(ROOT / "corpus" / "test.jsonl", tok)
    tr = DataLoader(tr_ds, batch_size=a.batch, shuffle=True)
    dv = DataLoader(ScopeData(ROOT / "corpus" / "dev.jsonl", tok), batch_size=32)
    te = DataLoader(te_ds, batch_size=32)

    print("train scope distribution:",
          dict(Counter(LABELS[i] for i in tr_ds.labels)))

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
        if macro > best_macro:
            best_macro = macro
            best_state = {k: v.detach().cpu().clone()
                          for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    print(f"\nbest dev macro-F1: {best_macro:.3f}")

    g, p = evaluate(model, te, dev)
    acc, macro = report(g, p, "TEST - DistilBERT scope")
    print(f"\nbaseline for comparison:  accuracy {BASELINE_ACC:.3f}   macro-F1 {BASELINE_MACRO:.3f}")
    print(f"delta:                    {acc-BASELINE_ACC:+.3f}        {macro-BASELINE_MACRO:+.3f}")

    print("\nTop confusions")
    conf = Counter((LABELS[x], LABELS[y]) for x, y in zip(g, p) if x != y)
    for (gl, pl), n in conf.most_common(6):
        print(f"  {gl}  ->  {pl}   x{n}")

    # COMMAND FIDELITY. Scope accuracy is not the deliverable - the action set
    # is. Combine the predicted scope with the gazetteer-extracted targets and
    # check whether the resulting set of services exactly matches gold.
    exact = 0
    for r, t, q in zip(te_ds.rows, te_ds.texts, p):
        named = _find_targets(t)
        pred_set = set(resolve_action_set(named, LABELS[q], INVENTORY))
        gold_set = set(resolve_action_set(r["targets"], r["scope"], INVENTORY))
        exact += pred_set == gold_set
    fidelity = exact / len(te_ds.rows)
    print(f"\ncommand fidelity          {fidelity:>7.3f}   "
          f"(baseline {BASELINE_FIDELITY:.3f}, delta {fidelity-BASELINE_FIDELITY:+.3f})")

    # The demo case: one token inverts the action set.
    print("\nthe inversion pair")
    for s in ["my phone was stolen, lock everything except my email",
              "my phone was stolen, lock everything, especially my email"]:
        enc = tok(s, truncation=True, max_length=96, return_tensors="pt")
        with torch.no_grad():
            q = model(**{k: v.to(dev) for k, v in enc.items()}).logits.argmax(-1).item()
        acts = resolve_action_set(_find_targets(s), LABELS[q], INVENTORY)
        print(f"  scope={LABELS[q]:<7} {sorted(acts)}")
        print(f"           {s}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUTDIR)
    tok.save_pretrained(OUTDIR)
    print(f"\nsaved -> {OUTDIR}")