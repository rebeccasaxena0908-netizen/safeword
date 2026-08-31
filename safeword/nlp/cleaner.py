"""
M0 - Email segmentation.

Labels each LINE as body / signature / quoted_reply / forwarded_header /
disclaimer, then keeps only the body.

Why this runs before every other NLP stage: a forwarded panic mail carries the
whole thread. If the intent classifier reads quoted history it fires on the
wrong message, and signature blocks inject bank names straight into the NER
output as phantom entities.

TWO BACKENDS. A trained CRF (models/cleaner/crf.pkl) if present, else the rule
baseline below. Measured on the test split:

    metric              rules     CRF
    line accuracy       0.652    0.999
    macro-F1            0.563    0.999
    body exact match    0.152    0.995

The rules handle forwarded_header perfectly (F1 1.000) because those lines have
rigid syntax. They collapse on quoted_reply (0.343) and disclaimer (0.265
recall) because those require SEQUENCE modelling: a quoted block continues once
it starts, and a disclaimer is defined by position - trailing, after a
signature. Regex has no notion of "still inside the previous block"; a
linear-chain CRF models exactly that. The failure here is structural, not
lexical, which is a different diagnosis from M1 intent.

CAVEAT FOR THE REPORT. The CRF is evaluated on synthetic furniture drawn from a
template pool of six signatures, three quoted replies, one forwarded header and
two disclaimers. 0.995 is an upper bound; real signature variety is unbounded.
Evaluating against a public corpus such as Enron is future work.

Set SAFEWORD_USE_CLEANER_CRF=0 to force the rule baseline.
"""
import os
import pickle
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CRF_PATH = ROOT / "models" / "cleaner" / "crf.pkl"

QUOTE_PREFIX = re.compile(r"^\s*>")
ON_WROTE = re.compile(r"^\s*On .{5,80}\bwrote:\s*$", re.I)
FORWARD_HDR = re.compile(
    r"^\s*(-{2,}\s*Forwarded message\s*-{2,}|From:|Sent:|To:|Subject:|Date:|Cc:)", re.I
)
SIG_MARKER = re.compile(r"^\s*(--\s*$|Sent from my |Get Outlook for |Regards,|Best,|Thanks,|Sincerely,)", re.I)
DISCLAIMER = re.compile(r"(confidential|do not disclose|intended recipient|unsubscribe)", re.I)

LABELS = ("body", "quoted_reply", "forwarded_header", "signature", "disclaimer")

_crf = None
_crf_tried = False


def crf_enabled() -> bool:
    return os.getenv("SAFEWORD_USE_CLEANER_CRF", "1") != "0"


def _load_crf():
    """Lazy load, cached. Returns None if unavailable - rules then take over."""
    global _crf, _crf_tried
    if _crf_tried:
        return _crf
    _crf_tried = True
    if not crf_enabled() or not CRF_PATH.exists():
        return None
    try:
        with open(CRF_PATH, "rb") as fh:
            _crf = pickle.load(fh)
    except Exception as exc:
        print(f"  [cleaner] could not load CRF: {exc}")
        _crf = None
    return _crf


def line_features(lines, i):
    """
    Structural features, deliberately not lexical. The model should generalise
    to signature formats it has never seen rather than memorise "Sent from my
    iPhone". Must stay identical to scripts/train_cleaner.py.
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


def classify_lines(text: str) -> list[tuple[str, str]]:
    """Return [(label, line), ...]. CRF when available, rules otherwise."""
    lines = text.splitlines()
    if not lines:
        return []

    crf = _load_crf()
    if crf is not None:
        try:
            feats = [line_features(lines, i) for i in range(len(lines))]
            labels = crf.predict_single(feats)
            return list(zip(labels, lines))
        except Exception as exc:
            print(f"  [cleaner] CRF prediction failed, using rules: {exc}")

    return classify_lines_rules(text)


def classify_lines_rules(text: str) -> list[tuple[str, str]]:
    """
    Rule baseline. Kept for the ablation table.

    in_sig is sticky: once a signature starts, everything after it is
    signature. Real signatures are not interrupted by body text.
    """
    out, in_sig, in_fwd = [], False, False
    for line in text.splitlines():
        if in_sig:
            out.append(("signature", line))
            continue
        if QUOTE_PREFIX.match(line) or ON_WROTE.match(line):
            in_fwd = True
            out.append(("quoted_reply", line))
        elif FORWARD_HDR.match(line):
            in_fwd = True
            out.append(("forwarded_header", line))
        elif SIG_MARKER.match(line):
            in_sig = True
            out.append(("signature", line))
        elif DISCLAIMER.search(line):
            out.append(("disclaimer", line))
        elif in_fwd and line.strip() == "":
            out.append(("quoted_reply", line))
        else:
            in_fwd = False
            out.append(("body", line))
    return out


def clean(text: str) -> str:
    """Keep only the lines the sender actually wrote in this message."""
    kept = [ln for label, ln in classify_lines(text) if label == "body"]
    return "\n".join(kept).strip()


def clean_rules(text: str) -> str:
    """Force the rule path. For ablations."""
    kept = [ln for label, ln in classify_lines_rules(text) if label == "body"]
    return "\n".join(kept).strip()