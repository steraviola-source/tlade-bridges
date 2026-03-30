# TLADe Bridge — Rithmic (R|Protocol)

**Status: Community Wanted**

Direct connection to Rithmic R|Protocol API for real-time CME futures data.

## Why This Matters

Rithmic powers ~60% of retail futures trading (AMP, Tradovate, Optimus, etc.). A direct R|Protocol bridge would serve the largest segment of futures traders.

## What's Needed

A bridge that implements the [TLADe Bridge Protocol](../../protocol/BRIDGE_SPEC.md):
- `/health` — connection status
- `/ib_data?ticker=ES` — real-time 5min candles with volume
- `/ib_daily?ticker=ES` — 1Y daily bars (optional)
- `/ib_history?ticker=ES` — 2W 5min history (optional)

## Known Challenges

- R|Protocol requires credentials and a funded account
- The `pyrithmic` Python library connects but Paper Trading environments don't stream CME tick data via API
- Live credentials needed for development and testing

## Alternative

If you use Rithmic through NinjaTrader 8, the [NinjaTrader bridge](../ninjatrader/) already works — it's feed-agnostic and supports Rithmic, CQG, and Kinetick through NT8.

## Contributing

If you have a live Rithmic account and Python/C++ experience, we'd love your help. Open an issue to discuss the approach before starting.
