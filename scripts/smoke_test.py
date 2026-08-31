"""Quick sanity check on the gate and trust modules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safeword.config import load_profile
from safeword.verify import gate, trust

p = load_profile()

print("== S2 sender gate ==")
print("  unknown sender :", gate.check("stranger@nowhere.com", p).allowed)
print("  enrolled slot  :", gate.check("family.member@example.com", p).allowed)
print("  dkim fail score:", gate.score_headers("pass", "fail", "none"))

print("\n== S5a semantic match ==")
expected = "my grandmother's dog was called Bruno"
print("  paraphrase :", trust.semantic_match("bruno, nani's dog", expected))
print("  wrong      :", trust.semantic_match("i dont remember", expected))

print("\n== S5b stylometry ==")
c = p["writing_samples"]
print("  owner panic:", trust.stylometry_score(
    "omg someone grabbed my phone!! lock everything NOW", c))
print("  imposter   :", trust.stylometry_score(
    "Dear Sir/Madam, I hereby request immediate account lockdown.", c))
print("  no corpus  :", trust.stylometry_score("anything", []))

print("\n== fusion ==")
print("  all signals:", trust.fuse(0.68, 0.9, 1.0, "owner_secondary"))
print("  proxy      :", trust.fuse(0.68, None, 1.0, "trusted_contact"))
print("  first msg  :", trust.fuse(None, 0.9, 1.0, "owner_secondary"))