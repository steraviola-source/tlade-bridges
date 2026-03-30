# TLADe Bridge — CQG

**Status: Community Wanted**

Direct connection to CQG API for real-time CME futures data.

## Why This Matters

CQG powers ~25-30% of retail futures trading, including brokers like AMP (CQG option), Dorman, and others. A direct CQG bridge would complement the Rithmic bridge to cover nearly all retail futures traders.

## What's Needed

A bridge that implements the [TLADe Bridge Protocol](../../protocol/BRIDGE_SPEC.md):
- `/health` — connection status
- `/ib_data?ticker=ES` — real-time 5min candles with volume
- `/ib_daily?ticker=ES` — 1Y daily bars (optional)
- `/ib_history?ticker=ES` — 2W 5min history (optional)

## Alternative

If you use CQG through NinjaTrader 8, the [NinjaTrader bridge](../ninjatrader/) already works — it's feed-agnostic and supports CQG, Rithmic, and Kinetick through NT8.

## Contributing

If you have CQG API access and development experience, we'd love your help. Open an issue to discuss the approach before starting.
