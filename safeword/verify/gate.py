"""
S2 - Sender gate.

The cheapest filter runs first, before any model is loaded. A set-membership
test against five addresses costs microseconds and discards the overwhelming
majority of traffic before you pay for a transformer forward pass.
"""
import time
from collections import defaultdict

_attempts: dict[str, list[float]] = defaultdict(list)


class GateResult:
    def __init__(self, allowed, reason="", slot=None, header_trust=0.0):
        self.allowed = allowed
        self.reason = reason
        self.slot = slot or {}
        self.header_trust = header_trust

    def __repr__(self):
        return f"<GateResult allowed={self.allowed} reason={self.reason!r}>"


def score_headers(spf: str = "none", dkim: str = "none", dmarc: str = "none") -> float:
    """
    Header authentication is a FEATURE, never a verdict.

    A DKIM failure does not reject the message: a real friend on a badly
    configured mail server must still be able to save you. It lowers the
    score and routes to stricter linguistic verification instead.
    """
    weights = {"pass": 1.0, "neutral": 0.5, "none": 0.4, "softfail": 0.2, "fail": 0.0}
    vals = [weights.get(str(v).lower(), 0.3) for v in (spf, dkim, dmarc)]
    return round(sum(vals) / len(vals), 3)


def check(from_address: str, profile: dict, auth: dict | None = None,
          rate_limit: int = 3) -> GateResult:
    addr = (from_address or "").strip().lower()
    slot = profile["slot_index"].get(addr)

    if slot is None:
        # No reply, ever. Replying confirms the address is watched.
        return GateResult(False, "not_in_emergency_slots")

    now = time.time()
    _attempts[addr] = [t for t in _attempts[addr] if now - t < 3600]
    if len(_attempts[addr]) >= rate_limit:
        return GateResult(False, "rate_limited", slot)
    _attempts[addr].append(now)

    auth = auth or {}
    return GateResult(True, "ok", slot, score_headers(
        auth.get("spf", "none"), auth.get("dkim", "none"), auth.get("dmarc", "none")))