"""Loads secrets from .env and the user profile from config/profile.yaml."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


BOT_EMAIL = env("SAFEWORD_BOT_EMAIL", "rebecca.saxena.0908@gmail.com")
BOT_APP_PASSWORD = env("SAFEWORD_BOT_APP_PASSWORD")
IMAP_HOST = env("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "587"))

MOCK_BANK_URL = env("MOCK_BANK_URL", "http://127.0.0.1:5001")
MOCK_SOCIAL_URL = env("MOCK_SOCIAL_URL", "http://127.0.0.1:5002")
MOCK_API_KEY = env("MOCK_API_KEY", "safeword-sandbox-key")

LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"


def load_profile(path: Path | None = None) -> dict:
    path = path or ROOT / "config" / "profile.yaml"
    with open(path) as fh:
        profile = yaml.safe_load(fh)

    slots = profile.get("emergency_slots", [])
    if len(slots) != 5:
        raise ValueError(
            f"profile.yaml must define exactly 5 emergency_slots, found {len(slots)}. "
            "The five-slot cap is a security property, not a default."
        )
    profile["slot_index"] = {s["address"].lower(): s for s in slots}
    return profile