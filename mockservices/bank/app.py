"""
Aravali Bank (sandbox) - the demo bank.

No real bank will let a student project drive their session APIs, and a tool
that did would functionally be an account-takeover kit. This service exposes
the same SHAPE of API a real bank would: sessions, freeze, transactions.
Swapping the base URL is the only change a real integration would need.

Run:  python mockservices/bank/app.py     ->  http://127.0.0.1:5001
"""
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
API_KEY = os.getenv("MOCK_API_KEY", "safeword-sandbox-key")


def seed():
    now = datetime.now()
    return {
        "owner": "Rebecca Saxena",
        "account_no": "AVB 4417 8802 3391",
        "balance": 184320.55,
        "frozen": False,
        "cards_blocked": False,
        "sessions": [
            {"id": "s1", "device": "iPhone 14 - Ghaziabad", "ip": "103.21.44.9",
             "since": (now - timedelta(hours=6)).strftime("%d %b, %H:%M"), "current": False},
            {"id": "s2", "device": "MacBook Air M2 - home wifi", "ip": "192.168.1.14",
             "since": (now - timedelta(days=2)).strftime("%d %b, %H:%M"), "current": True},
            {"id": "s3", "device": "Chrome on Windows - unknown", "ip": "45.118.8.201",
             "since": (now - timedelta(minutes=11)).strftime("%d %b, %H:%M"), "current": False},
        ],
        "transactions": [
            {"desc": "Salary credit", "amount": 92000.00, "when": "01 Aug"},
            {"desc": "Blinkit", "amount": -1284.00, "when": "03 Aug"},
            {"desc": "Metro card top-up", "amount": -500.00, "when": "04 Aug"},
        ],
        "events": [],
    }


STATE = seed()


def note(text):
    STATE["events"].insert(0, {"at": datetime.now().strftime("%H:%M:%S"), "text": text})
    STATE["events"] = STATE["events"][:8]


def authorised():
    return request.headers.get("X-Api-Key") == API_KEY


@app.route("/")
def dashboard():
    return render_template("dashboard.html", s=STATE)


@app.route("/api/state")
def state():
    return jsonify(STATE)


@app.route("/api/revoke_sessions", methods=["POST"])
def revoke_sessions():
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    killed = len(STATE["sessions"])
    STATE["sessions"] = []
    note(f"All {killed} sessions revoked by SafeWord")
    return jsonify({"revoked": killed, "sessions_remaining": 0})


@app.route("/api/freeze", methods=["POST"])
def freeze():
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    STATE["frozen"] = True
    STATE["cards_blocked"] = True
    note("Account frozen, cards blocked")
    return jsonify({"frozen": True, "cards_blocked": True})


@app.route("/api/unfreeze", methods=["POST"])
def unfreeze():
    if not authorised():
        return jsonify({"error": "bad api key"}), 401
    STATE["frozen"] = False
    STATE["cards_blocked"] = False
    note("Freeze lifted (rollback)")
    return jsonify({"frozen": False})


@app.route("/api/reset", methods=["POST", "GET"])
def reset():
    global STATE
    STATE = seed()
    note("Sandbox reset")
    return jsonify({"reset": True})


if __name__ == "__main__":
    app.run(port=5001, debug=False)