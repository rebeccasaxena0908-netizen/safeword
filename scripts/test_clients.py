"""Check the action clients can reach both mock services."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safeword.actions import clients

print("revoke telegram  :", clients.revoke_sessions("telegram"))
print("rotate instagram :", clients.rotate_password("instagram"))
print("bank freeze      :", clients.bank_freeze())
print("bank unfreeze    :", clients.bank_unfreeze())