"""
M1 intent, M1b reporter role, M2 slots, M3 distress.

Each classifier is a THIN WRAPPER that tries the trained model first and falls
back to a rule baseline if the model is unavailable. The rule versions are kept
under a _rules suffix - they are the comparison column in the ablation table
and must not be deleted.

    M1  -> DistilBERT           models/intent    (trained)
    M1b -> DistilBERT           models/role      (trained)
    M3  -> DistilBERT           models/distress  (trained)
    M2  -> gazetteer + scope classifier          (rules; closed vocabulary)

Set SAFEWORD_USE_MODELS=0 to force rule mode for the whole pipeline. That
switch is what makes the ablation reproducible: same code, same tests, one
variable changed.
"""

import re
from dataclasses import dataclass, field

from . import models

INTENTS = (
    "stolen_confirmed", "lost_uncertain", "partial_lockdown",
    "cancel_false_alarm", "status_query", "verification_response", "out_of_scope",
)
ROLES = ("owner", "proxy", "mere_mention")
DISTRESS = ("calm", "worried", "panic")
SCOPES = ("all", "only", "except")

STOLEN = re.compile(r"\b(stole|stolen|snatch|snatched|grabbed|robbed|chori|theft|mugged|pickpocket)\b", re.I)
LOST = re.compile(r"\b(lost|lose|losing|misplaced|can'?t find|cannot find|left my phone|kho gaya)\b", re.I)
CANCEL = re.compile(r"\b(false alarm|nevermind|never mind|cancel|stop|undo|found it|got it back|mil gaya|don'?t lock|do not lock)\b", re.I)
STATUS = re.compile(r"\b(status|what happened|did it work|is it done|update me)\b", re.I)
PAST_MENTION = re.compile(r"\b(last week|last month|yesterday|a while ago|article|news|reading about|happened to)\b", re.I)
FIRST_PERSON = re.compile(r"\b(my|i|me|mine|mera|meri)\b", re.I)
THIRD_PARTY = re.compile(r"\b(this is .{2,30}'s (friend|brother|sister|colleague)|on behalf of|he asked me|she asked me|his phone|her phone|uska phone)\b", re.I)
PANIC = re.compile(r"(!!|omg|help|now|immediately|asap|urgent|please hurry|jaldi|turant)", re.I)

TARGETS = {
    "telegram": ["telegram", "tg"],
    "whatsapp": ["whatsapp", "wa", "whats app"],
    "instagram": ["instagram", "insta", "ig"],
    "demobank": ["bank", "demobank", "account", "sbi", "hdfc", "icici", "chase"],
    # 'mail' alone matches "she asked me to mail you" - require a possessive
    "gmail": ["gmail", "my email", "my mail", "my e-mail", "the email", "email account"],
}
EXCEPT = re.compile(r"\b(except|apart from|other than|but not|leave out|chhod)\b", re.I)
# 'just' is far too weak on its own: "her phone JUST got snatched" is not a
# scope restriction.  ONLY must sit next to a target to count.
ONLY = re.compile(r"\b(only|nothing else|and nothing)\b", re.I)


@dataclass
class Understanding:
    intent: str = "out_of_scope"
    intent_confidence: float = 0.0
    role: str = "owner"
    distress: str = "calm"
    urgency: float = 0.0
    named_targets: list[str] = field(default_factory=list)
    scope: str = "all"          # all | only | except
    action_set: list[str] = field(default_factory=list)
    backend: str = "rules"      # which path produced this, for the ablation


def _find_targets(text: str) -> list[str]:
    """
    Gazetteer lookup over a CLOSED vocabulary of five services.

    Deliberately not a learned NER. The service names are five fixed strings;
    a gazetteer matches them essentially perfectly and a token-classification
    model would add complexity without accuracy. The semantics live in the
    scope operator, not in the entity names.
    """
    found = []
    low = text.lower()
    for canonical, aliases in TARGETS.items():
        if any(re.search(rf"\b{re.escape(a)}\b", low) for a in aliases):
            found.append(canonical)
    return found


# ---------------------------------------------------------------------------
# M1 - intent
# ---------------------------------------------------------------------------
def classify_intent(text: str) -> tuple[str, float]:
    """Trained DistilBERT if available, rule baseline otherwise."""
    hit = models.predict("intent", text, list(INTENTS))
    if hit is not None:
        return hit
    return classify_intent_rules(text)


def classify_intent_rules(text: str) -> tuple[str, float]:
    """
    Rule baseline. Kept for the ablation table.

    Order matters: cancel wins over everything, because the cost of ignoring a
    cancellation is locking the real owner out of their own life.
    """
    if CANCEL.search(text):
        return "cancel_false_alarm", 0.80
    if STATUS.search(text) and not STOLEN.search(text):
        return "status_query", 0.70
    if PAST_MENTION.search(text) and not PANIC.search(text):
        return "out_of_scope", 0.65
    if STOLEN.search(text):
        return "stolen_confirmed", 0.85
    if LOST.search(text):
        return "lost_uncertain", 0.75
    return "out_of_scope", 0.50


# ---------------------------------------------------------------------------
# M1b - reporter role
# ---------------------------------------------------------------------------
def classify_role(text: str) -> str:
    """Trained DistilBERT if available, rule baseline otherwise."""
    hit = models.predict("role", text, list(ROLES))
    if hit is not None:
        return hit[0]
    return classify_role_rules(text)


def classify_role_rules(text: str) -> str:
    """Rule baseline. Kept for the ablation table."""
    if THIRD_PARTY.search(text):
        return "proxy"
    if PAST_MENTION.search(text) and not PANIC.search(text):
        return "mere_mention"
    if FIRST_PERSON.search(text):
        return "owner"
    return "proxy"


# ---------------------------------------------------------------------------
# M3 - distress
# ---------------------------------------------------------------------------
def classify_distress(text: str) -> tuple[str, float]:
    """Trained DistilBERT if available, rule baseline otherwise."""
    hit = models.predict("distress", text, list(DISTRESS))
    if hit is not None:
        return hit
    return classify_distress_rules(text)


def classify_distress_rules(text: str) -> tuple[str, float]:
    """Rule baseline. Kept for the ablation table."""
    hits = len(PANIC.findall(text))
    caps = sum(1 for w in text.split() if len(w) > 2 and w.isupper())
    score = min(1.0, 0.22 * hits + 0.12 * caps + (0.25 if "!" in text else 0.0))
    if score >= 0.6:
        return "panic", score
    if score >= 0.25:
        return "worried", score
    return "calm", score


# ---------------------------------------------------------------------------
# M2 - slots and scope
# ---------------------------------------------------------------------------
def extract_slots(text: str) -> tuple[list[str], str]:
    """
    Named targets from the gazetteer, plus the scope operator.

    Scope uses the trained classifier when models/scope exists; otherwise the
    rule version, which already scores 0.946 because scope is triggered by a
    small closed set of words.
    """
    targets = _find_targets(text)
    hit = models.predict("scope", text, list(SCOPES))
    if hit is not None:
        scope = hit[0]
        # A scope restriction with nothing named cannot be resolved, so it
        # degrades to 'all' rather than silently emptying the action set.
        if scope in ("only", "except") and not targets:
            scope = "all"
        return targets, scope
    return extract_slots_rules(text)


def extract_slots_rules(text: str) -> tuple[list[str], str]:
    """Rule baseline. Kept for the ablation table."""
    targets = _find_targets(text)
    if EXCEPT.search(text):
        return targets, "except"
    if ONLY.search(text) and targets:
        return targets, "only"
    return targets, "all"


def resolve_action_set(named: list[str], scope: str, inventory: list[str]) -> list[str]:
    """
    SCOPE resolution - the demo-worthy bit.
    'lock everything except my email'    -> inventory minus gmail
    'lock everything especially my email'-> full inventory
    'only instagram'                     -> [instagram]
    """
    if scope == "only" and named:
        return [t for t in named if t in inventory]
    if scope == "except" and named:
        return [t for t in inventory if t not in named]
    return list(inventory)


# ---------------------------------------------------------------------------
# Orchestrator entry point
# ---------------------------------------------------------------------------
def understand(text: str, inventory: list[str]) -> Understanding:
    intent, conf = classify_intent(text)
    role = classify_role(text)
    distress, urgency = classify_distress(text)
    named, scope = extract_slots(text)

    live = models.status()
    backend = ("models" if all(live.values())
               else "rules" if not any(live.values())
               else "mixed")

    return Understanding(
        intent=intent, intent_confidence=conf, role=role,
        distress=distress, urgency=urgency,
        named_targets=named, scope=scope,
        action_set=resolve_action_set(named, scope, inventory),
        backend=backend,
    )


def understand_rules(text: str, inventory: list[str]) -> Understanding:
    """Force the rule path regardless of which models exist. For ablations."""
    intent, conf = classify_intent_rules(text)
    role = classify_role_rules(text)
    distress, urgency = classify_distress_rules(text)
    named, scope = extract_slots_rules(text)
    return Understanding(
        intent=intent, intent_confidence=conf, role=role,
        distress=distress, urgency=urgency,
        named_targets=named, scope=scope,
        action_set=resolve_action_set(named, scope, inventory),
        backend="rules",
    )