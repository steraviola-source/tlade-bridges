#!/usr/bin/env python3
"""
TLADe Bridge Lite — Candle Push Only
Connects to TWS/IB Gateway, serves real-time candles on localhost.
Terminal on Netlify auto-detects and switches to live data.

Usage:
  pip install flask flask-cors ib_insync
  python tlade_bridge_lite.py

Requires: TWS or IB Gateway with API enabled on port 7496 (live) or 7497 (paper)
"""

import os, math, time, threading, asyncio
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Config ──
IB_HOST = os.environ.get('IB_HOST', '127.0.0.1')
IB_PORT = int(os.environ.get('IB_PORT', '7496'))
IB_CLIENT = int(os.environ.get('IB_CLIENT', '10'))
PORT = int(os.environ.get('BRIDGE_PORT', '5000'))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ── State ──
lock = threading.Lock()
bars = {'ES': None, 'NQ': None}
tickers = {'ES': None, 'NQ': None}
connected = False
contracts = {'ES': None, 'NQ': None}  # resolved active contracts
_ib_ref = None  # reference to IB instance for on-demand requests
_daily_cache = {}   # { 'ES': { 'date': '2026-03-30', 'data': [...] } }
_history_cache = {}  # { 'ES': { 'date': '2026-03-30', 'data': [...] } }

# ── IB Connection ──
def ib_loop():
    global connected, _ib_ref
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    from ib_insync import IB, Future

    while True:
        ib = IB()
        try:
            print(f'[IB] Connecting to {IB_HOST}:{IB_PORT}...')
            ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT, timeout=10)
            print('[IB] Connected')
            connected = True
            _ib_ref = ib

            for sym in ['ES', 'NQ']:
                fut = Future(symbol=sym, exchange='CME')
                details = ib.reqContractDetails(fut)
                active = sorted(
                    [c.contract for c in details
                     if c.contract.lastTradeDateOrContractMonth
                     and datetime.strptime(c.contract.lastTradeDateOrContractMonth, '%Y%m%d').date() >= datetime.today().date()],
                    key=lambda x: x.lastTradeDateOrContractMonth
                )
                if active:
                    c = active[0]
                    print(f'[IB] {sym}: {c.localSymbol}')
                    with lock:
                        contracts[sym] = c
                        bars[sym] = ib.reqHistoricalData(
                            c, endDateTime='', durationStr='2 W',
                            barSizeSetting='5 mins', whatToShow='TRADES',
                            useRTH=False, formatDate=1, keepUpToDate=True
                        )
                        tickers[sym] = ib.reqMktData(c, '', False, False)

            print('[IB] ES + NQ streaming')

            # Pre-fetch daily and history in IB thread (avoids threading issues from Flask)
            for sym in ['ES', 'NQ']:
                c = contracts.get(sym)
                if not c:
                    continue
                today = datetime.now().strftime('%Y-%m-%d')
                try:
                    daily_bars = ib.reqHistoricalData(
                        c, endDateTime='', durationStr='1 Y',
                        barSizeSetting='1 day', whatToShow='TRADES',
                        useRTH=True, formatDate=1, keepUpToDate=False
                    )
                    result = []
                    for bar in daily_bars:
                        try:
                            t = int(bar.date.timestamp()) if hasattr(bar.date, 'timestamp') else int(datetime.strptime(str(bar.date), '%Y-%m-%d').timestamp())
                            if t <= 0: continue
                            result.append({'t': t, 'o': bar.open, 'h': bar.high, 'l': bar.low, 'c': bar.close, 'v': int(bar.volume) if bar.volume else 0})
                        except: continue
                    _daily_cache[sym] = {'date': today, 'data': result}
                    print(f'[IB] Daily pre-fetched: {len(result)} bars for {sym}')
                except Exception as e:
                    print(f'[IB] Daily pre-fetch failed for {sym}: {e}')

                try:
                    hist_bars = ib.reqHistoricalData(
                        c, endDateTime='', durationStr='2 W',
                        barSizeSetting='5 mins', whatToShow='TRADES',
                        useRTH=False, formatDate=1, keepUpToDate=False
                    )
                    result = []
                    for bar in hist_bars:
                        try:
                            t = int(bar.date.timestamp())
                            if t <= 0: continue
                            result.append({'t': t, 'o': bar.open, 'h': bar.high, 'l': bar.low, 'c': bar.close, 'v': int(bar.volume) if bar.volume else 0})
                        except: continue
                    _history_cache[sym] = {'date': today, 'data': result}
                    print(f'[IB] History pre-fetched: {len(result)} bars for {sym} (2W 5min)')
                except Exception as e:
                    print(f'[IB] History pre-fetch failed for {sym}: {e}')

            # Track initial bar count to detect post-reconnect shrinkage
            initial_es_count = len(bars.get('ES') or [])
            while ib.isConnected():
                ib.sleep(2)
                # If bars shrank significantly (IB reconnect drops history), force re-subscribe
                current_es = len(bars.get('ES') or [])
                if initial_es_count > 100 and current_es < 100:
                    print(f'[IB] ⚠️ Bars shrank from {initial_es_count} to {current_es} — reconnecting to restore history')
                    break

        except Exception as e:
            print(f'[IB] Error: {e}')
        finally:
            connected = False
            _ib_ref = None
            try: ib.disconnect()
            except: pass
            print('[IB] Reconnecting in 15s...')
            time.sleep(15)

# ── Endpoints ──
@app.route('/health')
def health():
    has_data = False
    with lock:
        has_data = bars['ES'] is not None and len(bars['ES']) > 0
    return jsonify({
        'status': 'ok',
        'tlade_bridge': True,
        'ib_connected': connected and has_data,
        'provider': 'ib',
        'lite_mode': True,
        'version': '1.1.0',
    })

@app.route('/ib_data')
def ib_data():
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    with lock:
        b = bars.get(sym)
        tk = tickers.get(sym)

        if not b or len(b) == 0:
            return jsonify({'error': f'No data for {sym}'}), 404

        times, opens, highs, lows, closes, volumes = [], [], [], [], [], []
        for bar in list(b):
            try:
                t = int(bar.date.timestamp())
                if t <= 0: continue
                times.append(t)
                opens.append(bar.open)
                highs.append(bar.high)
                lows.append(bar.low)
                closes.append(bar.close)
                volumes.append(int(bar.volume) if hasattr(bar, 'volume') and bar.volume else 0)
            except: continue

        if not times:
            return jsonify({'error': f'Empty data for {sym}'}), 404

        price = None
        if tk and hasattr(tk, 'last') and tk.last and not math.isnan(tk.last) and tk.last > 0:
            price = tk.last
        if price is None and closes:
            price = closes[-1]

    return jsonify({
        'chart_data': {'time': times, 'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes},
        'live_price': price,
        'instrument': sym,
    })


@app.route('/ib_daily')
def ib_daily():
    """1Y daily bars — served from pre-fetched cache (no on-demand IB calls)."""
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    if sym in _daily_cache and _daily_cache[sym].get('data'):
        return jsonify({'data': _daily_cache[sym]['data'], 'instrument': sym, 'cached': True})

    return jsonify({'error': 'Daily data not yet available — bridge is warming up'}), 503


@app.route('/ib_history')
def ib_history():
    """2W 5min bars — served from pre-fetched cache (no on-demand IB calls)."""
    ticker = request.args.get('ticker', 'ES').upper()
    sym = 'NQ' if 'NQ' in ticker else 'ES'

    if sym in _history_cache and _history_cache[sym].get('data'):
        return jsonify({'data': _history_cache[sym]['data'], 'instrument': sym, 'cached': True})

    return jsonify({'error': 'History data not yet available — bridge is warming up'}), 503

# ── Main ──
if __name__ == '__main__':
    print(f'''
  TLADe Bridge Lite
  TWS {IB_HOST}:{IB_PORT} → localhost:{PORT}
  Open your terminal on tradelikeadealer.com — it will auto-detect.
''')
    threading.Thread(target=ib_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)
