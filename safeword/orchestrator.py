"""
S6 tier decision, S7 ordered execution, S8 report, S9 rollback.

The execution order is a dependency chain, not a preference. Email is locked
LAST because it is the master key: every service above will happily mail a
reset link to it. Locking it first would leave everything else reachable;
locking it last means that when the thief thinks to try recovery, there is
nothing left to recover and the inbox has just gone dark.
"""
import time
import uuid
from dataclasses import dataclass, field

from . import audit
from .actions import clients
from .nlp.cleaner import clean
from .nlp.nlu import understand
from .verify import gate, trust

STAGE_ORDER = ["sessions", "passwords", "bank", "email"]
EMAIL_SERVICES = {"gmail"}
BANK_SERVICES = {"demobank"}


@dataclass
class Incident:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tier: int = 0
    action_set: list[str] = field(default_factory=list)
    executed: list[dict] = field(default_factory=list)
    trust: float = 0.0
    state: str = "open"


def decide_tier(u, trust_score: float, policy: dict,
                verified_by_challenge: bool = False) -> tuple[int, str]:
    """S6 - graduated response. See the 'lost vs stolen' design note."""
    if u.intent == "lost_uncertain":
        return 1, "lost_uncertain defaults to soft revoke - a lost phone is usually locked and under a sofa"
    if trust_score < policy["tier1_trust_threshold"]:
        return 0, "trust below Tier 1 floor - challenge instead of acting"
    if u.role == "proxy":
        return policy["proxy_tier_cap"], "proxy sender capped until the owner confirms out of band"
    if u.intent == "stolen_confirmed" and trust_score >= policy["tier2_trust_threshold"] \
            and u.distress in ("worried", "panic"):
        if not verified_by_challenge:
            # HARD RULE: irreversible actions require an active knowledge
            # factor, never inference alone. Header authentication, slot
            # class and writing style are all PASSIVE signals that an
            # attacker sitting in a compromised mailbox partly inherits.
            # A challenge answer is the only thing they must actually know.
            return 1, "trust is high but unverified - passive signals alone never unlock Tier 2"
        return 2, "confirmed theft, challenge passed, elevated distress"
    if u.intent == "stolen_confirmed":
        # Theft is claimed but trust has not cleared the Tier 2 bar. Do NOT
        # silently settle for Tier 1 and do NOT stall doing nothing: run the
        # reversible half now (it costs the owner almost nothing if this turns
        # out to be an imposter) and challenge for the irreversible half.
        return 1, "theft claimed, trust below Tier 2 bar - soft actions now, challenge for the rest"
    return 1, "conditions for full lockdown not met"


def _execute_stage(inc: Incident, stage: str, dry_run: bool) -> list[dict]:
    results = []
    if stage == "sessions":
        targets = [s for s in inc.action_set if s not in BANK_SERVICES | EMAIL_SERVICES]
        for svc in targets:
            r = {"ok": True, "dry_run": True} if dry_run else clients.revoke_sessions(svc)
            results.append({"stage": stage, "service": svc, "action": "revoke_sessions", **r})
    elif stage == "passwords":
        targets = [s for s in inc.action_set if s not in BANK_SERVICES | EMAIL_SERVICES]
        for svc in targets:
            r = {"ok": True, "dry_run": True} if dry_run else clients.rotate_password(svc)
            results.append({"stage": stage, "service": svc, "action": "rotate_password", **r})
    elif stage == "bank":
        for svc in [s for s in inc.action_set if s in BANK_SERVICES]:
            r1 = {"ok": True, "dry_run": True} if dry_run else clients.bank_revoke_sessions()
            r2 = {"ok": True, "dry_run": True} if dry_run else clients.bank_freeze()
            results.append({"stage": stage, "service": svc, "action": "revoke_sessions", **r1})
            results.append({"stage": stage, "service": svc, "action": "freeze", **r2})
    elif stage == "email":
        for svc in [s for s in inc.action_set if s in EMAIL_SERVICES]:
            r1 = {"ok": True, "dry_run": True} if dry_run else clients.rotate_password(svc)
            r2 = {"ok": True, "dry_run": True} if dry_run else clients.revoke_sessions(svc)
            results.append({"stage": stage, "service": svc, "action": "rotate_password", **r1})
            results.append({"stage": stage, "service": svc, "action": "revoke_sessions", **r2})
    return results


def execute(inc: Incident, policy: dict, dry_run: bool = False,
            grace_override: int | None = None) -> Incident:
    """S7 - staged execution with the grace window between bank and email."""
    stages = STAGE_ORDER if inc.tier == 2 else ["sessions"]

    for stage in stages:
        if stage == "email":
            wait = grace_override if grace_override is not None else policy["grace_window_seconds"]
            audit.log(inc.id, "S7", "grace_window_open", seconds=wait,
                      note="a single reply here reverses everything")
            time.sleep(min(wait, 3))          # demo-friendly; real bot waits the full window
            audit.log(inc.id, "S7", "grace_window_closed")

        results = _execute_stage(inc, stage, dry_run)
        for r in results:
            inc.executed.append(r)
            audit.log(inc.id, "S7", f"{stage}:{r['action']}",
                      service=r["service"], ok=r.get("ok"))

    inc.state = "executed"
    return inc


def rollback(inc: Incident, dry_run: bool = False) -> Incident:
    """
    S9 - reverse what can be reversed.

    Cancellation is subject to the SAME verification as the original trigger.
    Otherwise an attacker who cannot trigger a lockdown can simply cancel
    yours, which is the cheaper attack.
    """
    for rec in reversed(inc.executed):
        svc, act = rec["service"], rec["action"]
        if svc in EMAIL_SERVICES and act == "rotate_password":
            audit.log(inc.id, "S9", "not_auto_reversible", service=svc,
                      note="recovery envelope is the only route back")
            continue
        if act == "freeze":
            r = {"ok": True} if dry_run else clients.bank_unfreeze()
        elif act == "rotate_password":
            r = {"ok": True} if dry_run else clients.restore_password(svc)
        else:
            continue
        audit.log(inc.id, "S9", f"reverse:{act}", service=svc, ok=r.get("ok"))
    inc.state = "rolled_back"
    return inc


def build_report(inc: Incident, u) -> str:
    """S8 - natural-language summary, sent to owner-secondary slots only."""
    if not inc.executed:
        return f"Incident {inc.id}: no action taken (tier {inc.tier})."
    lines = [f"Incident {inc.id} - tier {inc.tier} complete.", ""]
    for stage in STAGE_ORDER:
        done = [r for r in inc.executed if r["stage"] == stage]
        if done:
            svcs = sorted({f"{r['service']}:{r['action']}" for r in done})
            lines.append(f"  {stage:<10} {', '.join(svcs)}")
    lines += ["", f"Intent {u.intent} | role {u.role} | distress {u.distress} "
                  f"| trust {inc.trust}"]
    if any(r["service"] in EMAIL_SERVICES for r in inc.executed):
        lines.append("Recovery envelope (Shamir 3-of-5) sent to your five Emergency Accounts.")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Pending-challenge store.  An incident that needs verification stays open
# until the sender's next message, which is treated as the challenge answer.
# In production this lives in Redis keyed by the mail thread's Message-ID.
# ---------------------------------------------------------------------------
PENDING: dict[str, dict] = {}


def reset_state():
    """Test/demo helper: clear pending incidents and per-slot rate limits."""
    PENDING.clear()
    gate._attempts.clear()


def handle_message(raw_body: str, from_address: str, profile: dict,
                   auth: dict | None = None, dry_run: bool = False,
                   grace_override: int | None = None):
    """Full S1-S8 path for one incoming message."""
    policy = profile["policy"]
    inventory = [s for group in profile["protected_services"].values() for s in group]
    addr = (from_address or "").strip().lower()
    pending = PENDING.get(addr)
    inc = Incident(id=pending["incident_id"]) if pending else Incident()

    audit.log(inc.id, "S1", "email_received", sender=from_address,
              turn="challenge_answer" if pending else "first")

    g = gate.check(from_address, profile, auth, policy["rate_limit_per_slot_per_hour"])
    if not g.allowed:
        audit.log(inc.id, "S2", "discarded", reason=g.reason)
        inc.state = "discarded"
        return inc, None, "Discarded at the sender gate. No reply sent."
    audit.log(inc.id, "S2", "sender_accepted", slot=g.slot["slot"],
              slot_class=g.slot["slot_class"], header_trust=g.header_trust)

    body = clean(raw_body)
    audit.log(inc.id, "S3", "cleaned", chars_in=len(raw_body), chars_out=len(body))

    if pending:
        # This message is an answer to an outstanding challenge question, not a
        # fresh report. Reuse the understanding from the triggering message.
        u = pending["understanding"]
        challenge = pending["challenge"]
        semantic = trust.semantic_match(body, challenge["answer"])
        audit.log(inc.id, "S5", "challenge_answered", challenge=challenge["id"],
                  semantic=semantic, round=pending["round"])
        # Carry the stylometry score forward rather than recomputing it here.
        # A three-word answer like "bruno, nani's dog" carries almost no
        # authorship signal - length alone dominates the feature distance and
        # the legitimate owner gets scored as an imposter. Authorship is
        # judged on the message the person actually composed.
        carried_stylo = pending.get("stylometry")
    else:
        u = understand(body, inventory)
        audit.log(inc.id, "S4", "understood", intent=u.intent, role=u.role,
                  distress=u.distress, scope=u.scope, targets=u.action_set)

        if u.intent == "out_of_scope" or u.role == "mere_mention":
            audit.log(inc.id, "S4", "terminated", reason="no action requested")
            inc.state = "no_action"
            return inc, u, "No action: message does not request a lockdown."

        if u.intent == "cancel_false_alarm":
            PENDING.pop(addr, None)
            audit.log(inc.id, "S9", "cancelled_by_sender")
            inc.state = "cancelled"
            return inc, u, "Cancelled. Nothing was locked."

        semantic = None      # the panic mail is not an answer to anything yet
        challenge = None
        carried_stylo = None

    if u.role == "proxy":
        stylo = None                      # a friend's style is not the owner's
    elif carried_stylo is not None:
        stylo = carried_stylo             # scored on the triggering message
    else:
        stylo = trust.stylometry_score(body, profile.get("writing_samples", []))

    inc.trust = trust.fuse(semantic, stylo, g.header_trust, g.slot["slot_class"])
    audit.log(inc.id, "S5", "trust_scored", semantic=semantic, stylometry=stylo,
              header=g.header_trust, trust=inc.trust)

    challenge_passed = (semantic is not None
                        and semantic >= policy.get("semantic_pass_threshold", 0.40))
    inc.tier, why = decide_tier(u, inc.trust, policy,
                                verified_by_challenge=challenge_passed)
    audit.log(inc.id, "S6", "tier_decided", tier=inc.tier, rationale=why)

    if inc.tier == 0:
        rounds = (pending["round"] + 1) if pending else 1
        if rounds > policy["max_challenge_rounds"]:
            PENDING.pop(addr, None)
            audit.log(inc.id, "S5", "incident_frozen",
                      reason="two consecutive challenge failures",
                      note="alert sent to owner-secondary slots, no action taken")
            inc.state = "frozen"
            return inc, u, ("Verification failed twice. Incident frozen, nothing "
                            "was locked, and the owner has been alerted.")
        nxt = profile["challenges"][min(rounds - 1, len(profile["challenges"]) - 1)]
        PENDING[addr] = {"incident_id": inc.id, "understanding": u,
                         "challenge": nxt, "round": rounds, "stylometry": stylo}
        inc.state = "challenge_required"
        audit.log(inc.id, "S5", "challenge_issued", challenge=nxt["id"], round=rounds)
        return inc, u, f"Verification needed. {nxt['question']}"

    inc.action_set = u.action_set
    execute(inc, policy, dry_run=dry_run, grace_override=grace_override)
    report = build_report(inc, u)

    # Theft was claimed but Tier 2 did not fire - whatever the reason (low
    # trust, or high trust that is merely passive). Keep the incident open
    # and challenge for the irreversible half.
    if inc.tier == 1 and u.intent == "stolen_confirmed" and not challenge_passed:
        rounds = (pending["round"] + 1) if pending else 1
        if rounds <= policy["max_challenge_rounds"]:
            nxt = profile["challenges"][min(rounds - 1, len(profile["challenges"]) - 1)]
            PENDING[addr] = {"incident_id": inc.id, "understanding": u,
                             "challenge": nxt, "round": rounds, "stylometry": stylo}
            inc.state = "tier1_done_awaiting_verification"
            audit.log(inc.id, "S5", "escalation_challenge_issued",
                      challenge=nxt["id"], round=rounds)
            return inc, u, (report + "\n\nSessions are already revoked. To also rotate "
                            f"passwords, freeze the bank and lock the mailbox:\n{nxt['question']}")
        PENDING.pop(addr, None)
        inc.state = "verification_exhausted"
        audit.log(inc.id, "S5", "verification_exhausted",
                  note="Tier 1 stands, Tier 2 refused, owner alerted")
        return inc, u, (report + "\n\nVerification failed twice. Sessions stay revoked, "
                        "but nothing irreversible was done. The owner has been alerted.")

    PENDING.pop(addr, None)
    audit.log(inc.id, "S8", "report_sent")
    return inc, u, report