# TLADe Bridge — NinjaTrader 8

Connect NinjaTrader 8 to TLADe for real-time ES/NQ data. Feed-agnostic — works with **Rithmic, CQG, and Kinetick** through NT8.

## What You Get

- **Real-time spot** — every tick pushed from NT8 indicator via HTTP
- **5-minute bar history** — closed bars are pushed too; the terminal plots NT8 candles natively instead of falling back to the public candle source
- **Startup backfill** — on indicator mount, the most recent ~500 closed bars are seeded automatically so chart history is available immediately
- **Any feed** — Rithmic, CQG, Kinetick, Simulated — if NT8 can see it, TLADe gets it
- **Zero config** — NT8 indicator auto-pushes, Python receiver auto-serves

## Architecture

```
Your Feed (Rithmic/CQG/Kinetick)
  └── NinjaTrader 8
        └── TLAdeBridge.cs (NT8 indicator, pushes ticks via HTTP POST)
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

Open an ES or NQ chart in NT8, add the `TLAdeBridge` indicator. Use a **5-minute chart** — the indicator pushes the chart's own bars, and the TLADe terminal expects 5-minute candles.

### 3. Run the receiver

```bash
pip install flask flask-cors
python tlade_bridge_nt8.py
```

### 4. Open TLADe

The terminal auto-detects the bridge on localhost.

## FAQ

### Why does the indicator appear to only work on one chart when I add it to two?

By design — the TLAdeBridge indicator is a *data publisher*, not a chart
visualiser. It forwards ticks and closed bars from NinjaTrader to the local
bridge on port 5000. Adding it to a second chart doesn't open a second data
channel: both instances post to the same endpoints, so the receiver keeps
the freshest tick and a single bar series per ticker.

You only need the indicator loaded on **one chart per ticker** (one for ES,
one for NQ). Use a **5-minute chart** for both — the indicator pushes the
chart's own bars and the terminal expects 5-minute candles. Multi-timeframe
analysis (15m / 30m / H1 / H4) happens inside the TLADe terminal itself by
aggregating from the 5-minute stream.

### The indicator is loaded but the terminal shows no chart candles yet

On startup, TLAdeBridge backfills the most recent 500 closed bars to the
receiver — this is async and bursty (a small delay between bars to avoid
saturating the local socket). For a default 500-bar backfill, expect the
chart to fill in within ~10 seconds of loading the indicator. Watch the
NinjaScript Output window for `[TLAdeBridge] BAR ... → OK` lines.

If after 30 seconds you still see no candles in the terminal:
- Make sure the receiver (`python tlade_bridge_nt8.py`) is running and shows `[BAR]` lines incoming.
- Hard-refresh the terminal browser (Ctrl+F5 / Cmd+Shift+R) to retry `/ib_data`.

## Status

**v1.1.0 — Beta with bars.** Spot ticks + closed 5-minute bars now both push to the receiver, so the terminal plots NT8 candles natively (no Yahoo fallback). Startup backfill of ~500 bars seeds chart history on indicator load. Validated against the standard Bridge Protocol; live-feed testing with funded Rithmic/CQG accounts ongoing — please report results via issues.

## Contributing

If you have a live NT8 connection with Rithmic or CQG, we'd appreciate testing reports. Open an issue with your results.
