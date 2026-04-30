#!/usr/bin/env python3
"""
TLADe Bridge — NinjaTrader 8 receiver.

Receives ticks from the TLAdeBridge.cs indicator running inside NT8 and
exposes them to the TLADe terminal via the standard Bridge Protocol
(see ../../protocol/BRIDGE_SPEC.md).

Endpoints:
  POST /push_spot          — inbound: NT8 indicator pushes each tick here
  GET  /health             — terminal liveness probe
  GET  /ib_data?ticker=    — terminal pulls latest tick (live_price)

Run:
  pip install flask flask-cors
  python tlade_bridge_nt8.py

The NT8 indicator pushes ticks only (no bar history), so /ib_data returns
chart_data empty. The terminal falls back to its own candle source for
chart display, while spot updates flow live from NT8.
"""

from datetime import datetime
from threading import Lock

from flask import Flask, jsonify, request
from flask_cors import CORS

VERSION = "1.0.0"
PORT = 5000
HEARTBEAT_WINDOW_S = 15  # tick is "fresh" if received within this window

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

_lock = Lock()
_ticks = {}  # { "ES": {"price": float, "ts": str, "received_at": datetime}, ... }


def _normalize_ticker(raw: str) -> str:
    """Map any ticker variant to ES or NQ (per Bridge Protocol §Ticker Mapping)."""
    s = (raw or "").upper()
    return "NQ" if "NQ" in s or "NDX" in s else "ES"


def _is_fresh(received_at: datetime) -> bool:
    return (datetime.utcnow() - received_at).total_seconds() < HEARTBEAT_WINDOW_S


@app.route("/push_spot", methods=["POST"])
def push_spot():
    """Inbound endpoint — NT8 indicator posts each tick here."""
    data = request.get_json(silent=True)
    if not data or "ticker" not in data or "spot" not in data:
        return jsonify({"error": "invalid payload, expected {ticker, spot, ts}"}), 400
    try:
        price = float(data["spot"])
    except (TypeError, ValueError):
        return jsonify({"error": "spot must be numeric"}), 400

    ticker = _normalize_ticker(str(data["ticker"]))
    with _lock:
        _ticks[ticker] = {
            "price": price,
            "ts": data.get("ts") or datetime.utcnow().isoformat(),
            "received_at": datetime.utcnow(),
        }
    print(f"[TICK] {ticker} -> {price}")
    return jsonify({"ok": True, "ticker": ticker})


@app.route("/health", methods=["GET"])
def health():
    """Terminal liveness probe (Bridge Protocol §health)."""
    with _lock:
        any_fresh = any(_is_fresh(t["received_at"]) for t in _ticks.values())
        live_tickers = [k for k, t in _ticks.items() if _is_fresh(t["received_at"])]
    return jsonify({
        "status": "ok",
        "tlade_bridge": True,
        "ib_connected": any_fresh,
        "provider": "ninjatrader",
        "lite_mode": True,
        "version": VERSION,
        "live_tickers": live_tickers,
    })


@app.route("/ib_data", methods=["GET"])
def ib_data():
    """Real-time spot for the requested ticker (Bridge Protocol §ib_data).

    NT8 sends ticks only — chart_data is returned empty so the terminal
    falls back to its own candle source. live_price reflects the latest
    tick if it arrived within HEARTBEAT_WINDOW_S.
    """
    ticker = _normalize_ticker(request.args.get("ticker", "ES"))
    with _lock:
        t = _ticks.get(ticker)
        fresh = bool(t and _is_fresh(t["received_at"]))
        price = t["price"] if fresh else None
        ts = t["ts"] if fresh else None

    if not fresh:
        return jsonify({"error": f"no fresh tick for {ticker}"}), 404

    return jsonify({
        "chart_data": {
            "time": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        },
        "live_price": price,
        "last_price": price,
        "instrument": ticker,
        "ts": ts,
    })


if __name__ == "__main__":
    print(f"[TLADe NT8 Bridge] v{VERSION} listening on http://localhost:{PORT}")
    print("[TLADe NT8 Bridge] waiting for ticks from TLAdeBridge.cs (NT8 indicator)...")
    app.run(host="127.0.0.1", port=PORT, debug=False)
