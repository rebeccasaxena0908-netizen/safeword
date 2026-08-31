"""
Trained-model backends for the NLU functions.

Loads lazily and caches: the first call pays the model load, subsequent calls
are a forward pass. If a model directory is missing or the backend is disabled,
the loader returns None and nlu.py silently keeps using its rule baseline - so
the pipeline never breaks because a model has not been trained yet.

Two switches:

    SAFEWORD_USE_MODELS=0           force rules everywhere (whole-pipeline ablation)
    SAFEWORD_DISABLE=scope,distress disable named backends only

ON M2 SCOPE. Measured like-for-like on the current test split, the trained
scope model gives accuracy 0.929 vs 0.915 and COMMAND FIDELITY 0.928 vs 0.914,
while LOWERING macro-F1 from 0.814 to 0.718. Command fidelity is the
deliverable - whether the resolved action set exactly matches gold - so the
model is enabled. Two caveats belong in the report: the fidelity gain is
+0.013 on 54 test seeds and is within noise, and the 'except' class rests on a
single test seed. This is the fourth instance in this project of macro-F1
moving opposite to the deployment-critical metric.

Do not trust the hardcoded baselines in the train_*.py scripts for this
comparison; they were recorded against earlier, smaller corpora. Only
scripts/ablation.py measures both arms on the same data.

To reproduce:  SAFEWORD_DISABLE=scope python scripts/ablation.py
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = ROOT / "models"

BACKENDS = ("intent", "role", "distress", "scope")
DEFAULT_DISABLED = ""          # all trained backends live by default

_cache: dict[str, object] = {}
_torch = None


def models_enabled(name: str | None = None) -> bool:
    """True if the named backend should be used. No name = the global switch."""
    if os.getenv("SAFEWORD_USE_MODELS", "1") == "0":
        return False
    if name is None:
        return True
    raw = os.getenv("SAFEWORD_DISABLE", DEFAULT_DISABLED)
    disabled = {d.strip() for d in raw.split(",") if d.strip()}
    return name not in disabled


def _load(name: str):
    """Return (tokenizer, model) or None if unavailable or disabled."""
    if not models_enabled(name):
        return None
    if name in _cache:
        return _cache[name]

    path = MODEL_DIR / name
    if not path.exists():
        _cache[name] = None
        return None

    global _torch
    try:
        import torch
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer)
        _torch = torch
        tok = AutoTokenizer.from_pretrained(path)
        mdl = AutoModelForSequenceClassification.from_pretrained(path).eval()
        _cache[name] = (tok, mdl)
        return _cache[name]
    except Exception as exc:
        print(f"  [models] could not load {name}: {exc}")
        _cache[name] = None
        return None


def predict(name: str, text: str, labels: list[str]) -> tuple[str, float] | None:
    """Return (label, confidence) or None to fall back to the rule baseline."""
    loaded = _load(name)
    if loaded is None or not text.strip():
        return None
    tok, mdl = loaded
    enc = tok(text, truncation=True, max_length=96, return_tensors="pt")
    with _torch.no_grad():
        logits = mdl(**enc).logits[0]
        probs = _torch.softmax(logits, dim=-1)
        idx = int(probs.argmax())
    return labels[idx], round(float(probs[idx]), 3)


def status() -> dict[str, bool]:
    """Which backends are actually live right now. Useful in the demo."""
    return {n: (MODEL_DIR / n).exists() and models_enabled(n)
            for n in BACKENDS}


def reset_cache() -> None:
    """Drop loaded models. Needed when toggling switches inside one process."""
    _cache.clear()