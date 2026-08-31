"""HTTP clients for the sandboxed mock services. No real provider is ever touched."""
import requests

from ..config import MOCK_API_KEY, MOCK_BANK_URL, MOCK_SOCIAL_URL

TIMEOUT = 5
HEADERS = {"X-Api-Key": MOCK_API_KEY}


def _post(url: str, payload: dict) -> dict:
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
        return {"ok": r.status_code == 200, "status": r.status_code, **r.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def revoke_sessions(service: str, user: str = "owner") -> dict:
    return _post(f"{MOCK_SOCIAL_URL}/api/{service}/revoke_sessions", {"user": user})


def rotate_password(service: str, user: str = "owner") -> dict:
    return _post(f"{MOCK_SOCIAL_URL}/api/{service}/rotate_password", {"user": user})


def bank_freeze(user: str = "owner") -> dict:
    return _post(f"{MOCK_BANK_URL}/api/freeze", {"user": user})


def bank_revoke_sessions(user: str = "owner") -> dict:
    return _post(f"{MOCK_BANK_URL}/api/revoke_sessions", {"user": user})


def bank_unfreeze(user: str = "owner") -> dict:
    return _post(f"{MOCK_BANK_URL}/api/unfreeze", {"user": user})


def restore_password(service: str, user: str = "owner") -> dict:
    return _post(f"{MOCK_SOCIAL_URL}/api/{service}/restore_password", {"user": user})