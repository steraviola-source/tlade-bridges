#!/usr/bin/env python3
"""
TLADe Bridge Template
=====================
Minimal skeleton for building a TLADe-compatible bridge.
Implement the TODO sections with your data feed's API.

Usage:
  pip install flask flask-cors
  python bridge_template.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Your state here ──
# connected = False
# bars = {'ES': [...], 'NQ': [...]}


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'tlade_bridge': True,
        'ib_connected': False,  # TODO: return True when your feed is connected
        'provider': 'your-provider-name',
        'lite_mode': True,
        'version': '0.1.0',
    })


@app.route('/ib_data')
def ib_data():
    """Real-time 5min candles. REQUIRED."""
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    # TODO: return your candle data
    # times  = [unix_seconds, ...]
    # opens  = [float, ...]
    # highs  = [float, ...]
    # lows   = [float, ...]
    # closes = [float, ...]
    # volumes = [int, ...]
    # price  = latest_trade_price

    return jsonify({
        'chart_data': {
            'time': [],    # TODO
            'open': [],    # TODO
            'high': [],    # TODO
            'low': [],     # TODO
            'close': [],   # TODO
            'volume': [],  # TODO
        },
        'live_price': 0,   # TODO
        'instrument': sym,
    })


@app.route('/ib_daily')
def ib_daily():
    """1Y daily bars. OPTIONAL — terminal falls back to Yahoo if missing."""
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    # TODO: return daily OHLCV bars
    # Each bar: { 't': unix_seconds, 'o': open, 'h': high, 'l': low, 'c': close, 'v': volume }

    return jsonify({
        'data': [],  # TODO
        'instrument': sym,
        'cached': False,
    })


@app.route('/ib_history')
def ib_history():
    """2W of 5min bars with real volume. OPTIONAL — used for VP/AVWAP."""
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    # TODO: return 2 weeks of 5min OHLCV bars
    # Same format as /ib_daily

    return jsonify({
        'data': [],  # TODO
        'instrument': sym,
        'cached': False,
    })


if __name__ == '__main__':
    print('''
  TLADe Bridge Template
  Implement the TODO sections with your data feed.
  Docs: https://github.com/steraviola-source/tlade-bridges/blob/main/protocol/BRIDGE_SPEC.md
''')
    app.run(host='0.0.0.0', port=5000, debug=False)
