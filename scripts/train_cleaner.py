#!/usr/bin/env python3
"""
M0 - CRF line classifier for email segmentation.

Labels each LINE of a raw email as body / signature / quoted_reply /
forwarded_header / disclaimer, then keeps only the body.

Why a CRF rather than a transformer: the task is sequential in a way that is
almost entirely structural. Once a signature block starts it continues to the
end; quoted regions are contiguous; a disclaimer is defined by trailing
position. A linear-chain CRF models exactly that transition structure, trains
in seconds on CPU, and needs no GPU. Sentence semantics barely matter - "Sent
from my iPhone" is a signature because of where it sits and what shape it has,
not what it means.

Training data comes from augment_corpus.py, which grafts real furniture onto
clean bodies and records line-level labels in the m0_labels field.

CAVEAT. Furniture is drawn from a template pool of six signatures, three quoted
replies, one forwarded header and two disclaimers. Near-perfect CRF scores are
an upper bound; real signature variety is unbounded. Evaluating against a
public corpus such as Enron is future work.

    pip install sklearn-crfsuite
    python scripts/train_cleaner.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTDIR = ROOT / "models" / "cleaner"
LABELS = ["body", "signature", "quoted_reply", "forwarded_header", "disclaimer"]


def line_features(lines, i):
    """
    Structural features, deliberately not lexical - the model should generalise
    to signature formats it has never seen rather than memorise "Sent from my
    iPhone".

    MUST stay byte-identical to line_features in safeword/nlp/cleaner.py. A
    feature-set mismatch between training and inference produces garbage
    predictions with no error message.
    """
    ln = lines[i]
    stripped = ln.strip()
    lower = stripped.lower()

    f = {
        "bias": 1.0,
        "position": min(i, 10),
        "rel_position": round(i / max(1, len(lines) - 1), 1),
        "from_end": min(len(lines) - 1 - i, 10),
        "empty": not stripped,
        "len_bucket": min(len(stripped) // 20, 5),
        "starts_gt": stripped.startswith(">"),
        "starts_dash": stripped.startswith("--"),
        "ends_colon": stripped.endswith(":"),
        "has_at": "@" in stripped,
        "has_digit": any(c.isdigit() for c in stripped),
        "has_url": "http" in lower or "www." in lower,
        "all_caps": stripped.isupper() and len(stripped) > 3,
        "title_case": stripped[:1].isupper() if stripped else False,
        "comma_end": stripped.endswith(","),
        "word_count": min(len(stripped.split()), 12),
        "header_kw": any(lower.startswith(k) for k in
                         ("from:", "to:", "sent:", "subject:", "date:", "cc:")),
        "sig_kw": any(k in lower for k in
                      ("sent from", "regards", "best,", "thanks,", "sincerely",
                       "get outlook")),
        "quote_kw": "wrote:" in lower or "forwarded message" in lower,
        "legal_kw": any(k in lower for k in
                        ("confidential", "intended recipient", "unsubscribe",
                         "do not disclose")),
    }
    # Neighbour context. Signature and quote blocks are contiguous, so what
    # came immediately before is highly predictive.
    for offset, tag in ((-1, "prev"), (1, "next")):
        j = i + offset
        if 0 <= j < len(lines):
            s = lines[j].strip().lower()
            f[f"{tag}_empty"] = not s
            f[f"{tag}_gt"] = s.startswith(">")
            f[f"{tag}_dash"] = s.startswith("--")
            f[f"{tag}_header"] = any(s.startswith(k) for k in
                                     ("from:", "to:", "sent:", "subject:"))
        else:
            f[f"{tag}_boundary"] = True
    return f


def load(path):
    """Only messages carrying m0_labels are usable - those are the grafted ones."""
    X, Y, raw = [], [], []
    for line in open(path):
        r = json.loads(line)
        labels = r.get("m0_labels")
        if not labels:
            continue
        lines = r["text"].split("\n")
        if len(lines) != len(labels):
            continue          # grafting misaligned; skip rather than guess
        X.append([line_features(lines, i) for i in range(len(lines))])
        Y.append([l if l in LABELS else "body" for l in labels])
        raw.append(lines)
    return X, Y, raw


def evaluate(y_true, y_pred):
    flat_t = [l for seq in y_true for l in seq]
    flat_p = [l for seq in y_pred for l in seq]
    print(f"\n  {'label':<20}{'P':>8}{'R':>8}{'F1':>8}{'n':>8}")
    f1s = []
    for lab in LABELS:
        tp = sum(1 for t, p in zip(flat_t, flat_p) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(flat_t, flat_p) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(flat_t, flat_p) if t == lab and p != lab)
        if not (tp + fn):
            continue
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn)
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        f1s.append(f1)
        print(f"  {lab:<20}{pr:>8.3f}{rc:>8.3f}{f1:>8.3f}{tp+fn:>8}")
    acc = sum(t == p for t, p in zip(flat_t, flat_p)) / len(flat_t)
    macro = sum(f1s) / len(f1s) if f1s else 0.0
    print(f"  {'line accuracy':<20}{acc:>8.3f}   macro-F1 {macro:.3f}")
    return acc, macro


def body_exact_match(X_raw, y_true, y_pred):
    """
    The metric that matters: does the EXTRACTED BODY TEXT match?

    An earlier version compared line lists directly, which counted a
    disagreement on a blank separator line as a failure and reported rules at
    0.152 against the CRF's 0.995. That gap was almost entirely whitespace
    labelling: clean() joins and strips, so a blank line assigned to the wrong
    block changes nothing downstream. Comparing the joined, stripped text -
    what the intent and NER stages actually receive - gives the real figure.
    """
    ok = 0
    for lines, t, p in zip(X_raw, y_true, y_pred):
        text_t = "\n".join(l for l, lab in zip(lines, t) if lab == "body").strip()
        text_p = "\n".join(l for l, lab in zip(lines, p) if lab == "body").strip()
        ok += text_t == text_p
    return ok / len(X_raw)


if __name__ == "__main__":
    try:
        import sklearn_crfsuite
    except ImportError:
        sys.exit("pip install sklearn-crfsuite")

    # IMPORTANT: import the RULES function explicitly, not classify_lines.
    # cleaner.classify_lines now dispatches to the CRF when models/cleaner
    # exists, so calling it here would compare the CRF against itself and
    # report a flat +0.000 delta that looks like a legitimate null result.
    from safeword.nlp.cleaner import classify_lines_rules

    Xtr, Ytr, _ = load(ROOT / "corpus" / "train.jsonl")
    Xte, Yte, raw_te = load(ROOT / "corpus" / "test.jsonl")
    if not Xtr:
        sys.exit("No m0_labels found. Re-run scripts/augment_corpus.py.")

    print(f"train: {len(Xtr)} messages, {sum(len(x) for x in Xtr)} lines")
    print(f"test : {len(Xte)} messages, {sum(len(x) for x in Xte)} lines")
    print("label distribution:", dict(Counter(l for seq in Ytr for l in seq)))

    # ---- rule baseline ----
    rule_pred = []
    for lines, truth in zip(raw_te, Yte):
        pred = [lab for lab, _ in classify_lines_rules("\n".join(lines))]
        # splitlines() drops a trailing empty line that split("\n") keeps;
        # pad so the sequences align for scoring.
        pred = pred[:len(truth)] + ["body"] * max(0, len(truth) - len(pred))
        rule_pred.append(pred)

    print("\nRULE BASELINE")
    r_acc, r_f1 = evaluate(Yte, rule_pred)
    r_body = body_exact_match(raw_te, Yte, rule_pred)
    print(f"  body exact match    {r_body:.3f}")

    # ---- CRF ----
    crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.1,
                               max_iterations=120, all_possible_transitions=True)
    crf.fit(Xtr, Ytr)
    crf_pred = crf.predict(Xte)

    print("\nCRF")
    c_acc, c_f1 = evaluate(Yte, crf_pred)
    c_body = body_exact_match(raw_te, Yte, crf_pred)
    print(f"  body exact match    {c_body:.3f}")

    # ---- comparison ----
    print("\n" + "=" * 54)
    print(f"{'metric':<22}{'rules':>10}{'CRF':>10}{'delta':>11}")
    print("-" * 54)
    print(f"{'line accuracy':<22}{r_acc:>10.3f}{c_acc:>10.3f}{c_acc-r_acc:>+11.3f}")
    print(f"{'macro-F1':<22}{r_f1:>10.3f}{c_f1:>10.3f}{c_f1-r_f1:>+11.3f}")
    print(f"{'body exact match':<22}{r_body:>10.3f}{c_body:>10.3f}"
          f"{c_body-r_body:>+11.3f}")
    print("=" * 54)

    # ---- where they actually disagree ----
    diffs = []
    for lines, t, p in zip(raw_te, Yte, crf_pred):
        rp = [lab for lab, _ in classify_lines_rules("\n".join(lines))]
        rp = rp[:len(t)] + ["body"] * max(0, len(t) - len(rp))
        crf_text = "\n".join(l for l, lab in zip(lines, p) if lab == "body").strip()
        rule_text = "\n".join(l for l, lab in zip(lines, rp) if lab == "body").strip()
        if crf_text != rule_text:
            diffs.append((lines, rule_text, crf_text))

    print(f"\n{len(diffs)} of {len(raw_te)} messages yield a different body")
    for lines, rt, ct in diffs[:2]:
        print(f"\n  rules kept: {rt[:100]!r}")
        print(f"  CRF kept  : {ct[:100]!r}")

    print("\nBody exact match is the deliverable - it is the text the intent")
    print("and NER stages actually receive. Line accuracy counts blank-line")
    print("labelling, which does not survive clean()'s join and strip.")

    import pickle
    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(OUTDIR / "crf.pkl", "wb") as fh:
        pickle.dump(crf, fh)
    print(f"\nsaved -> {OUTDIR / 'crf.pkl'}")