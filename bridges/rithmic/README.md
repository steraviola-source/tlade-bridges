# TLADe Bridge — Rithmic (R|Protocol)

**Status: Ready**

Direct connection to Rithmic R|Protocol API for real-time CME futures data. Works with all Rithmic-powered brokers and prop firms.

## What You Get

- **Real-time ticks** — 5min bars streamed live from Rithmic
- **2 weeks of history** — backfill on startup
- **Real volume** — tick-accurate volume on every bar (VP/AVWAP calculated from actual trades)
- **All Rithmic brokers** — one bridge covers every Rithmic-powered platform

## Supported Systems

Apex, TopstepTrader, Bulenox, Earn2Trade, 10XFutures, 4PropTrader, DayTraders.com, LegendsTrading, LucidTrading, MES Capital, PropShopTrader, TradeFundrr, Tradeify, ThriveTrading, Rithmic 01, Rithmic Paper Trading.

If your broker connects through Rithmic, this bridge works.

## Requirements

- A Rithmic account (any of the supported systems above)
- Python 3.8+
- A TLADe subscription ([tradelikeadealer.com](https://tradelikeadealer.com))

## Setup (PowerShell)

### 1. Install dependencies

```powershell
pip install flask flask-cors async_rithmic
```

### 2. Set your credentials

```powershell
$env:RITHMIC_USER = "your_username"
$env:RITHMIC_PASS = "your_password"
$env:RITHMIC_SYSTEM = "your_system"
```

`RITHMIC_SYSTEM` is the system name from your broker (e.g. `Apex`, `TopstepTrader`, `Rithmic 01`, etc.).

### 3. Run the bridge

```powershell
python tlade_bridge_rithmic.py
```

### 4. Open TLADe

The terminal auto-detects the bridge on `localhost:5000`. You'll see the live indicator switch on.

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `RITHMIC_USER` | *(required)* | Your Rithmic username |
| `RITHMIC_PASS` | *(required)* | Your Rithmic password |
| `RITHMIC_SYSTEM` | *(required)* | System name (Apex, TopstepTrader, etc.) |
| `RITHMIC_GATEWAY` | `wss://rithmic.com:443` | WebSocket gateway URL |
| `RITHMIC_GATEWAY_IP` | `34.254.173.171` | Gateway IP (default is EU) |
| `BRIDGE_PORT` | `5000` | Local port for the bridge server |

## Important: One Market Data Session

Rithmic allows only **one Market Data session at a time** per account. Before running the bridge, close any other application using your Rithmic market data connection:

- RTrader Pro
- NinjaTrader (if connected via Rithmic)
- Any other Rithmic-connected platform

If you see authentication errors, this is almost always the cause.

## Troubleshooting

### DNS resolution errors
Some ISPs append a search suffix that breaks Rithmic hostname resolution. If you see DNS errors, try setting `RITHMIC_GATEWAY_IP` explicitly:
```powershell
$env:RITHMIC_GATEWAY_IP = "34.254.173.171"
```

### "Already connected" or auth failures
Close RTrader Pro, NinjaTrader, or any other platform using your Rithmic market data. Only one Market Data session is allowed at a time.

### Wrong credentials
Double-check `RITHMIC_USER`, `RITHMIC_PASS`, and `RITHMIC_SYSTEM`. The system name must match exactly what your broker provides.

## Alternative

If you use Rithmic through NinjaTrader 8, the [NinjaTrader bridge](../ninjatrader/) also works — it's feed-agnostic and supports Rithmic, CQG, and Kinetick through NT8.
