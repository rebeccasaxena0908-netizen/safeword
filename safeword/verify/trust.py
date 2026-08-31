"""
S5 - Verification. Signals fused into one trust score.

Three signals were designed: semantic challenge matching, stylometric
authorship verification, and mail header authentication. Only two are live.

STYLOMETRY IS DISABLED FOLLOWING MEASUREMENT. Evaluated against the held-out
imposter set (scripts/eval_stylometry.py), the character n-gram baseline
achieved ROC-AUC 0.546 - indistinguishable from chance - with imposters
scoring HIGHER on average than genuine owner messages (0.786 vs 0.766). No
threshold achieved FAR<=0.01 at any tolerable false-reject rate.

Two causes, both data-side rather than method-side:

  1. Eight enrolled writing samples. The design called for 50-100. A 3-gram
     profile built from eight short informal texts is dominated by common
     trigrams that formal imposter prose matches just as well.

  2. Augmentation destroys the signal stylometry depends on. Typo injection,
     casing corruption and code-mixing were added to make the intent models
     robust; they also remove any stable authorial style from the evaluation
     population. Genuine scores spread from 0.041 to 1.000.

The function is kept, tested and callable so the result is reproducible and
so it can be re-enabled once the enrolment corpus is large enough. Its weight
in the fusion is zero and fuse() drops the term entirely.

This does not weaken the security model. decide_tier() already refuses Tier 2
without an answered challenge question, so no irreversible action ever rested
on stylometry. Removing a signal that carries no information changes the
operating behaviour not at all - which is itself the argument for measuring
signals before trusting them.

    semantic  -> token overlap now; sentence-transformers all-MiniLM-L6-v2
                 with tau from the ROC/EER sweep is the planned upgrade
    stylometry-> disabled, see above
    header    -> SPF/DKIM/DMARC, a feature and never a verdict
"""
import math
import os
import re

# W_STYLO is 0.0 by measurement, not by oversight. See the module docstring.
# Set SAFEWORD_ENABLE_STYLOMETRY=1 to restore it for a comparison run.
W_SEMANTIC, W_HEADER, W_SLOT = 0.60, 0.20, 0.20
W_STYLO = 0.0

STYLOMETRY_AUC = 0.546          # measured, held-out imposter set, n=10
SLOT_WEIGHT = {"owner_secondary": 1.0, "trusted_contact": 0.6}


def stylometry_enabled() -> bool:
    return os.getenv("SAFEWORD_ENABLE_STYLOMETRY", "0") == "1"


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2}


def semantic_match(answer: str, expected: str) -> float:
    """
    S5a - does the answer mean the same thing as the enrolled one?

    STUB for sentence-transformers cosine similarity. Token overlap already
    tolerates the paraphrase a stressed person produces: "bruno, nani's dog"
    matches "my grandmother's dog was called Bruno" where exact-string
    matching would reject it.
    """
    a, b = _tokens(answer), _tokens(expected)
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b) + 0.35 * (len(a & b) > 0), 3)


def _char_ngrams(text: str, n: int = 3) -> dict[str, int]:
    t = re.sub(r"\s+", " ", text.lower())
    counts: dict[str, int] = {}
    for i in range(max(0, len(t) - n + 1)):
        g = t[i:i + n]
        counts[g] = counts.get(g, 0) + 1
    return counts


def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def stylometry_score(text: str, corpus: list[str]) -> float | None:
    """
    M4b - character 3-gram profile cosine, calibrated per user.

    DISABLED BY DEFAULT: measured ROC-AUC 0.546 against the held-out imposter
    set. Kept callable so scripts/eval_stylometry.py reproduces the negative
    result, and so the module can be re-enabled once enrolment reaches the
    50-100 samples the design assumed.

    Returns None - not a neutral 0.5 - whenever it cannot produce a
    meaningful score. A fabricated neutral value still moves the fused total;
    an absent term is honest and fuse() renormalises around it.
    """
    if not stylometry_enabled():
        return None
    if not corpus or not text.strip():
        return None

    profile = _char_ngrams(" ".join(corpus))
    raw = _cosine(_char_ngrams(text), profile)

    # Per-user calibration. Raw n-gram cosine on short informal text is low in
    # absolute terms for everyone, so the reference point is how well the
    # owner's own held-out messages score against the rest of their corpus.
    loo = []
    for i, sample in enumerate(corpus):
        rest = _char_ngrams(" ".join(corpus[:i] + corpus[i + 1:]))
        loo.append(_cosine(_char_ngrams(sample), rest))
    reference = sum(loo) / len(loo) if loo else 1.0
    return round(min(1.0, raw / reference) if reference else 0.0, 3)


def fuse(semantic: float | None, stylo: float | None, header: float,
         slot_class: str) -> float:
    """
    Combine whatever signals are present, renormalising the weights over them.

    Any signal may be absent:

      semantic is None on the FIRST message of an incident - the panic mail is
      not an answer to a challenge question, so scoring it against one would
      return ~0 and wrongly sink the trust score of a genuine victim. It
      becomes available only on the challenge turn.

      stylo is None for proxy senders (a friend's writing style is not the
      owner's) and, currently, for everyone (W_STYLO is 0.0 by measurement).

    Note that a high fused score never authorises irreversible action on its
    own. decide_tier() requires an answered challenge regardless, because
    every other signal here is passive - inherited by an attacker sitting in a
    compromised mailbox - while a challenge answer is something they must know.
    """
    parts = [(W_HEADER, header), (W_SLOT, SLOT_WEIGHT.get(slot_class, 0.5))]
    if semantic is not None:
        parts.append((W_SEMANTIC, semantic))
    if stylo is not None and W_STYLO > 0:
        parts.append((W_STYLO, stylo))
    total = sum(w for w, _ in parts)
    return round(min(1.0, sum(w * v for w, v in parts) / total), 3)