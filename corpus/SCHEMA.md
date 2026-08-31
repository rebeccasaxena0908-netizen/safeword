# SafeWord corpus — annotation guidelines v1

Every seed message carries five annotations. Two annotators label independently; disagreements are resolved by discussion and the rule that settled it gets written into this file. Report Cohen's κ before and after resolution.

---

## 1. `intent` — what is being asked for

| Label | Definition | Example |
| --- | --- | --- |
| `stolen_confirmed` | The sender asserts the device was taken by a person. An adversary plausibly holds it, unlocked. | "someone snatched my phone at the metro" |
| `lost_uncertain` | The device is missing but no adversary is asserted. Probably locked, probably under a sofa. | "I can't find my phone anywhere" |
| `partial_lockdown` | A specific, bounded action is requested — not a full emergency. | "just log me out of instagram everywhere" |
| `cancel_false_alarm` | Reverse or stop an incident, or a report retracted. | "false alarm, it was in my bag" |
| `status_query` | Asking what the system did or is doing. | "did the lockdown go through?" |
| `verification_response` | An answer to a challenge question, nothing else. | "bruno, my nani's dog" |
| `out_of_scope` | Everything else, including theft discussed with no request. | "reading an article about phone theft" |

**Decision rules for the hard cases**

- Theft asserted *and* cancelled in the same message → `cancel_false_alarm`. Cancellation always wins; the cost of ignoring a cancellation is locking out the real owner.
- "lost" used loosely where context makes theft clear ("lost my phone to a guy on a bike") → `stolen_confirmed`. Annotate the *situation*, not the verb.
- Theft asserted about someone who is not the account owner → `out_of_scope`, and `role = mere_mention`.
- A request naming targets *and* asserting theft → `stolen_confirmed`, with the targets captured in slots. `partial_lockdown` is only for requests with no emergency framing.

## 2. `role` — who is speaking, about whom

| Label | Definition |
| --- | --- |
| `owner` | First person. The account owner reporting their own device. |
| `proxy` | A third party reporting on the owner's behalf, at the owner's request or otherwise. |
| `mere_mention` | Theft or loss is discussed, but the message is not a request to act. |

**Decision rules**

- `proxy` requires the *sender* to be someone other than the owner. "my wife's phone was stolen" from the owner's own mailbox is `mere_mention`, not `proxy` — nobody is asking to lock the owner's accounts.
- Reported speech ("she asked me to email you") is the clearest proxy marker. Absence of first-person possessives is weak evidence, not proof.
- `mere_mention` is the most important class in the corpus. Under-sample it and precision collapses. Target at least 20% of the corpus.

## 3. `distress` — register, not content

| Label | Markers |
| --- | --- |
| `calm` | Complete sentences, correct punctuation, no urgency terms. |
| `worried` | Some urgency, hedging, mild disfluency. |
| `panic` | Repeated punctuation, capitals, urgency terms, fragmentary syntax, typos. |

Annotate the *writing*, not the situation. A calmly worded theft report is `calm` — and that combination is a useful adversarial signal, because a composed, well-formed emergency message at 3 a.m. is what an attacker's message looks like.

## 4. `slots` — targets and scope

Entity types: `BANK`, `SOCIAL_APP`, `MESSAGING_APP`, `EMAIL_PROVIDER`, `ACTION`, `SCOPE`, `LOCATION`, `TIME_REF`.

`scope` takes one of three values:

| Value | Trigger | Effect on the action set |
| --- | --- | --- |
| `all` | Default. No restriction expressed. | Full protected inventory |
| `only` | "only", "just X and nothing else" | Named targets only |
| `except` | "except", "apart from", "but not" | Inventory minus named targets |

**The critical distinction.** "lock everything except my email" and "lock everything, especially my email" differ by one token and produce opposite action sets. Both phrasings must appear in the corpus, in quantity, or the model will never learn the difference. Aim for at least 60 examples of each.

## 5. `is_hard_negative` — boolean

Set true for any message that mentions theft, loss, or account security but must produce **no action**. News articles, past events, other people's phones, hypotheticals, jokes, phishing mail, security newsletters.

These carry the false-trigger rate. Target 25% of the corpus.

---

## Composition targets

| Dimension | Target |
| --- | --- |
| Total after expansion and augmentation | ~6,000 |
| Seeds written by hand | ~400 |
| `mere_mention` + hard negatives | ≥ 25% |
| `proxy` role | ≥ 12% |
| Code-mixed (Hinglish) | ≥ 15% |
| Carrying email furniture (signature, quoted reply, forward) | ≥ 30% |
| Adversarial imposter set (for stylometry) | 200, held out entirely |

## Leakage rule

All variants derived from one seed must land in the same split. Splitting by message instead of by seed inflates your accuracy by a wide margin and is the single most common way student NLP projects report numbers they can't reproduce. `build_dataset.py` enforces this by grouping on `seed_id`.