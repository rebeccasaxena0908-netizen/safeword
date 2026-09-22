#!/usr/bin/env python3
"""
Smoke test: confirms the live profile validates and the bot's Gmail App
Password works over IMAP and SMTP. Reads no mail, sends nothing, acts on
nothing.

    python scripts/check_mail.py
"""
import smtplib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safeword.config import (BOT_APP_PASSWORD, BOT_EMAIL, IMAP_HOST, SMTP_HOST,
                             SMTP_PORT, load_live_profile)

print("== profile ==")
try:
    p = load_live_profile()
    print(f"  loaded   : {p['_source']}")
    for s in p["emergency_slots"]:
        print(f"  slot {s['slot']}   : {s['address']:<42} {s['slot_class']}")
except Exception as exc:
    sys.exit(f"  INVALID  : {exc}")

print("\n== bot mailbox ==")
print(f"  account  : {BOT_EMAIL}")
if not BOT_APP_PASSWORD or BOT_APP_PASSWORD.startswith("x"):
    sys.exit("  No app password in .env yet (SAFEWORD_BOT_APP_PASSWORD).")

try:
    from imapclient import IMAPClient
    with IMAPClient(IMAP_HOST, ssl=True) as s:
        s.login(BOT_EMAIL, BOT_APP_PASSWORD)
        n = s.select_folder("INBOX")[b"EXISTS"]
    print(f"  IMAP     : ok  ({n} messages in INBOX)")
except Exception as exc:
    print(f"  IMAP     : FAILED  {exc}")
    print("             Check: 2-Step Verification on, IMAP enabled in Gmail,")
    print("             app password pasted without spaces.")

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(BOT_EMAIL, BOT_APP_PASSWORD)
    print("  SMTP     : ok")
except Exception as exc:
    print(f"  SMTP     : FAILED  {exc}")