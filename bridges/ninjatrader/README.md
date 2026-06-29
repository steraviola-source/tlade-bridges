# TLADe Bridge — NinjaTrader 8

Connect NinjaTrader 8 to TLADe for real-time ES/NQ data. Feed-agnostic — works with **Rithmic, CQG, and Kinetick** through NT8.

## What You Get

- **Real-time spot ticks** — every NT8 tick forwarded sub-second
- **Live candles** — the in-progress 5-min bar pushed ~1×/sec so the
  terminal chart paints live, not only at 5-minute closes
- **500-bar backfill** on indicator mount, so chart history is there
  immediately instead of accumulating tick-by-tick
- **Any feed** — Rithmic, CQG, Kinetick, Simulated, IB through NT8 —
  if NinjaTrader can see it, TLADe gets it
- **Zero config** — NT8 indicator auto-pushes, Python receiver auto-serves

## Architecture

```
Your Feed (Rithmic/CQG/Kinetick/IB)
  └── NinjaTrader 8
        └── TLAdeBridge.cs (NT8 indicator, pushes ticks + bars via HTTP POST)
              └── tlade_bridge_nt8.py (Python receiver on port 5000)
                    └── TLADe Terminal (auto-detects on localhost:5000)
```

The receiver speaks the standard [Bridge Protocol](../../protocol/BRIDGE_SPEC.md) on port 5000, exposing `/health` and `/ib_data` to the terminal and `/push_spot` + `/push_bar` for the NT8 indicator.

## Requirements

- NinjaTrader 8 with a connected data feed
- Python 3.8+
- TLADe subscription

## Setup

### 1. Install the NT8 indicator

Copy `TLAdeBridge.cs` to your NinjaTrader indicators folder:
```
Documents\NinjaTrader 8\bin\Custom\Indicators\
```

Restart NinjaTrader or compile custom indicators (right-click in NinjaScript Editor > Compile).

### 2. Add indicator to chart

Open an ES or NQ chart in NT8, add the `TLAdeBridge` indicator.

### 3. Run the receiver

```bash
pip install flask flask-cors
python tlade_bridge_nt8.py
```

### 4. Open TLADe

The terminal auto-detects the bridge on localhost.

## Updating

When a new version ships, follow [`UPDATING.md`](./UPDATING.md) — replacing
the `.cs` file alone is not enough, you also need to flush the NinjaScript
Editor buffer, recompile, and re-attach the indicator on the chart.

## FAQ

### Why does the indicator appear to only work on one chart when I add it to two?

By design — the TLAdeBridge indicator is a *spot-tick publisher*, not a chart
visualiser. It forwards each tick from NinjaTrader to the local bridge on
port 5000. Adding it to a second chart doesn't open a second data channel:
both instances post to the same `/push_spot` endpoint, so the receiver keeps
only the latest tick and the second instance looks idle by comparison.

You only need the indicator loaded on **one chart per ticker** (one for ES,
one for NQ). The timeframe of that NT8 chart (1m, 5m, tick…) doesn't affect
what TLADe receives — multi-timeframe analysis happens inside the TLADe
terminal itself via the built-in 5m / 15m / 30m / H1 / H4 switcher.

## Status

**Beta** — validated with NT8 Simulated Feed. Spot-only path: NT8 sends individual ticks (no bar history), so the terminal uses its own candle source for the chart while spot updates flow live from NT8. Tested with live data feeds pending (needs funded AMP account with Rithmic or CQG).

## Contributing

If you have a live NT8 connection with Rithmic or CQG, we'd appreciate testing reports. Open an issue with your results.
