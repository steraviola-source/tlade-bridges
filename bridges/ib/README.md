# TLADe Bridge — Interactive Brokers

Connect your TWS or IB Gateway to TLADe for real-time ES/NQ data with tick-accurate volume.

## What You Get

- **Real-time candles** — 5min bars streamed live from TWS, 2 weeks of history
- **Tick volume** — real volume on every bar (not estimated)
- **Daily bars** — 1 year of D1 data for PDH/PDL/PWH/PWL levels
- **VP & AVWAP** — calculated from real volume, not Yahoo estimates
- **Zero latency** — everything runs on localhost

## Requirements

- Interactive Brokers account (live or paper)
- TWS or IB Gateway running
- Python 3.8+
- TLADe subscription

## Setup (5 minutes)

### 1. Enable TWS API

In TWS: **File > Global Configuration > API > Settings**

- [x] Enable ActiveX and Socket Clients
- [x] Socket port: **7496** (live) or **7497** (paper)
- [x] Allow connections from localhost only

### 2. Install dependencies

```bash
pip install flask flask-cors ib_insync
```

### 3. Run the bridge

```bash
python tlade_bridge_lite.py
```

You should see:
```
  TLADe Bridge Lite
  TWS 127.0.0.1:7496 → localhost:5000

[IB] Connecting to 127.0.0.1:7496...
[IB] Connected
[IB] ES: ESM6
[IB] NQ: NQM6
[IB] ES + NQ streaming
```

### 4. Open TLADe

Go to [tradelikeadealer.com](https://tradelikeadealer.com) — the terminal auto-detects the bridge. You'll see the live data indicator switch on.

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `IB_HOST` | `127.0.0.1` | TWS host |
| `IB_PORT` | `7496` | TWS API port (7497 for paper) |
| `IB_CLIENT` | `10` | Client ID (use different IDs for multiple connections) |
| `BRIDGE_PORT` | `5000` | Bridge HTTP port |

Example for paper trading:
```bash
IB_PORT=7497 python tlade_bridge_lite.py
```

## Endpoints

| Endpoint | Description | Auto-cached |
|----------|-------------|-------------|
| `/health` | Connection status | — |
| `/ib_data?ticker=ES` | Live 5min candles (2 weeks) | — |
| `/ib_daily?ticker=ES` | 1Y daily bars | Per day |
| `/ib_history?ticker=ES` | 2W 5min bars (real volume) | Per day |

## Troubleshooting

**"IB not connected" in terminal**
- Check TWS is running and API is enabled
- Verify port 7496 is correct (7497 for paper)
- Check TWS API log for connection attempts

**Bridge crashes on start**
- Make sure no other process uses port 5000
- Try `BRIDGE_PORT=5001` (update won't auto-detect yet)

**"No data for ES"**
- TWS needs a moment to load contracts after market open
- Check your IB market data subscriptions include CME futures
