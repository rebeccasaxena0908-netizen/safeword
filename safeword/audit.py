"""Append-only incident log. Every decision and every action lands here."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import LOG_DIR

LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "audit.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(incident_id: str, stage: str, event: str, **fields) -> dict:
    record = {"ts": _now(), "incident": incident_id, "stage": stage, "event": event}
    record.update(fields)
    with open(LOG_PATH, "a") as fh:
        fh.write(json.dumps(record) + "\n")
    print(f"  [{stage:<6}] {event}" + (f"  {fields}" if fields else ""))
    return record


def read_incident(incident_id: str) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out = []
    with open(LOG_PATH) as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("incident") == incident_id:
                out.append(rec)
    return out