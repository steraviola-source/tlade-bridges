# TLADe Bridge — NinjaTrader 8

Connect NinjaTrader 8 to TLADe for real-time ES/NQ data. Feed-agnostic — works with **Rithmic, CQG, and Kinetick** through NT8.

## What You Get

- **Real-time candles** — tick data pushed from NT8 indicator via HTTP
- **Any feed** — Rithmic, CQG, Kinetick, Simulated — if NT8 can see it, TLADe gets it
- **Zero config** — NT8 indicator auto-pushes, Python receiver auto-serves

## Architecture

```
Your Feed (Rithmic/CQG/Kinetick)
  └── NinjaTrader 8
        └── TLAdeBridge.cs (NT8 indicator, pushes ticks via HTTP POST)
              └── tlade_bridge_nt8.py (Python receiver on port 8765)
                    └── TLADe Terminal (auto-detects on localhost:5000)
```

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

## Status

**Beta** — validated with NT8 Simulated Feed. Tested with live data feeds pending (needs funded AMP account with Rithmic or CQG).

## Contributing

If you have a live NT8 connection with Rithmic or CQG, we'd appreciate testing reports. Open an issue with your results.
