"""Loads secrets from .env and the user profile from config/."""
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

PROFILE_EXAMPLE = ROOT / "config" / "profile.yaml"        # committed; tests + simulator
PROFILE_LOCAL = ROOT / "config" / "profile.local.yaml"    # gitignored; live bot


def load_profile(path: Path | None = None) -> dict:
    """Load and validate a profile. Defaults to the committed example."""
    path = Path(path) if path else PROFILE_EXAMPLE
    with open(path) as fh:
        profile = yaml.safe_load(fh)

    slots = profile.get("emergency_slots", [])
    if len(slots) != 5:
        raise ValueError(
            f"{path.name} must define exactly 5 emergency_slots, found {len(slots)}. "
            "The five-slot cap is a security property, not a default."
        )

    addresses = [s["address"].strip().lower() for s in slots]
    if len(set(addresses)) != 5:
        raise ValueError(f"{path.name}: emergency_slots contains a duplicate address.")

    # The phone's own mailbox can never be a trigger: if the phone is stolen,
    # the thief can send from it - and use it to trigger or cancel a lockdown.
    primary = str(profile.get("owner_primary_email", "")).strip().lower()
    if primary and primary in addresses:
        raise ValueError(
            f"{primary} is the mailbox on the protected phone and cannot be an "
            "emergency slot - a thief holding the phone could send from it."
        )

    # The bot must never be able to trigger itself.
    bot = str(profile.get("bot_email", BOT_EMAIL)).strip().lower()
    if bot in addresses:
        raise ValueError(f"{bot} is the bot's own inbox and cannot be an emergency slot.")

    if not any(s["slot_class"] == "owner_secondary" for s in slots):
        raise ValueError(
            "At least one slot must be owner_secondary - reports and the recovery "
            "envelope are sent only to those addresses."
        )

    profile["slot_index"] = {s["address"].strip().lower(): s for s in slots}
    profile["_source"] = path.name
    return profile


def load_live_profile() -> dict:
    """The live bot's profile: the real local file if present, else the example."""
    return load_profile(PROFILE_LOCAL if PROFILE_LOCAL.exists() else PROFILE_EXAMPLE)