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

## Quick Start (Windows)

Download this folder, then **double-click `start.bat`**.

The script will:
1. Check if Python is installed (if not, opens the download page)
2. Install dependencies automatically (`flask`, `flask-cors`, `async_rithmic`)
3. Prompt for your Rithmic credentials + system name + region on first launch (saves to `.rithmic_config`)
4. Launch the bridge

That's it. No terminal commands needed.

## Quick Start (macOS)

Download this folder, then **double-click `start.command`**.

The script does the same steps as the Windows `.bat` — Python check, dependency install, credentials prompt, launch. Your password is hidden as you type.

### First-run Gatekeeper block

macOS may block a downloaded `.command` file with:
> "start.command" cannot be opened because it is from an unidentified developer.

Two ways to unblock:

**Option A — Right-click → Open (one-time)**
1. In Finder, right-click `start.command` → **Open**
2. Click **Open** in the warning dialog

**Option B — Terminal (one-time)**
```bash
cd /path/to/bridges/rithmic
chmod +x start.command
xattr -d com.apple.quarantine start.command
```

### Python not installed?

- Download from [python.org/downloads](https://www.python.org/downloads/), or
- Homebrew: `brew install python3`

Then re-open `start.command`.

## Manual Setup (any platform)

If you prefer a terminal command:

```bash
# Install Python 3.8+ first
pip3 install flask flask-cors async_rithmic

# Set your credentials (PowerShell: use $env:VAR = "value")
export RITHMIC_USER="your_username"
export RITHMIC_PASS="your_password"
export RITHMIC_SYSTEM="Apex"   # or your broker's system name

python3 tlade_bridge_rithmic.py
```

`RITHMIC_SYSTEM` is the system name from your broker (e.g. `Apex`, `TopstepTrader`, `Rithmic 01`, etc.).

## Open TLADe

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
