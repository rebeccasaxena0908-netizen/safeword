"""
Mock social / messaging / mail provider.

One service standing in for Telegram, WhatsApp, Instagram and Gmail, exposing
the two operations a real provider's security page offers: revoke all
sessions, and rotate the password.

Run:  python mockservices/social/app.py    ->  http://127.0.0.1:5002
"""
import os
import secrets
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)
API_KEY = os.getenv("MOCK_API_KEY", "safeword-sandbox-key")
SERVICES = ["telegram", "whatsapp", "instagram", "gmail"]


def seed():
    return {
        svc: {
            "sessions": [
                {"device": "iPhone 14", "where": "Ghaziabad"},
                {"device": "MacBook Air M2", "where": "home wifi"},
            ],
            "password": "originalPassw0rd",
            "password_rotated": False,
            "log": [],
        }
        for svc in SERVICES
    }


STATE = seed()


def authorised():
    return request.headers.get("X-Api-Key") == API_KEY


def note(svc, text):
    STATE[svc]["log"].insert(0, f"{datetime.now().strftime('%H:%M:%S')}  {text}")


@app.route("/")
def index():
    return jsonify({svc: {"sessions": len(d["sessions"]),
                          "password_rotated": d["password_rotated"],
                          "log": d["log"][:3]} for svc, d in STATE.items()})


@app.route("/api/<svc>/revoke_sessions", methods=["POST"])
def revoke(svc):
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    if svc not in STATE:
        return jsonify({"error": "unknown service"}), 404
    n = len(STATE[svc]["sessions"])
    STATE[svc]["sessions"] = []
    note(svc, f"revoked {n} sessions")
    return jsonify({"service": svc, "revoked": n})


@app.route("/api/<svc>/rotate_password", methods=["POST"])
def rotate(svc):
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    if svc not in STATE:
        return jsonify({"error": "unknown service"}), 404
    STATE[svc]["password"] = secrets.token_urlsafe(18)
    STATE[svc]["password_rotated"] = True
    note(svc, "password rotated to high-entropy value")
    return jsonify({"service": svc, "rotated": True})


@app.route("/api/<svc>/restore_password", methods=["POST"])
def restore(svc):
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    STATE[svc]["password"] = "originalPassw0rd"
    STATE[svc]["password_rotated"] = False
    note(svc, "password restored (rollback)")
    return jsonify({"service": svc, "restored": True})


@app.route("/api/reset", methods=["POST", "GET"])
def reset():
    global STATE
    STATE = seed()
    return jsonify({"reset": True})


if __name__ == "__main__":
    app.run(port=5002, debug=False)