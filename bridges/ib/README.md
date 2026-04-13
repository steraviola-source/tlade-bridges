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
- TWS or IB Gateway running with API enabled
- TLADe subscription

## Enable TWS API (all platforms)

In TWS: **File > Global Configuration > API > Settings**

- [x] Enable ActiveX and Socket Clients
- [x] Socket port: **7496** (live) or **7497** (paper)
- [x] Allow connections from localhost only

Then open TLADe at [tradelikeadealer.com](https://tradelikeadealer.com) — the terminal auto-detects the bridge and switches on the live data indicator.

## Quick Start (Windows)

Download this folder, then **double-click `start.bat`**.

The script will:
1. Check if Python is installed (if not, opens the download page)
2. Install dependencies automatically (`flask`, `flask-cors`, `ib_insync`)
3. Prompt for TWS port + client ID on first launch (saves to `.ib_config`)
4. Launch the bridge

That's it. No terminal commands needed.

## Quick Start (macOS)

Download this folder, then **double-click `start.command`**.

The script does the same steps as the Windows `.bat` — Python check, dependency install, config prompt, launch.

### First-run Gatekeeper block

macOS may block a downloaded `.command` file with:
> "start.command" cannot be opened because it is from an unidentified developer.

Two ways to unblock:

**Option A — Right-click → Open (one-time)**
1. In Finder, right-click `start.command` → **Open**
2. Click **Open** in the warning dialog
3. macOS will remember this and double-click will work next time

**Option B — Terminal (one-time)**
```bash
cd /path/to/bridges/ib
chmod +x start.command
xattr -d com.apple.quarantine start.command
```

Then double-click works normally.

### Python not installed?

If Python 3 is not found, install it with either:
- Download from [python.org/downloads](https://www.python.org/downloads/)
- Homebrew: `brew install python3`

Then re-open `start.command`.

## Manual Setup (any platform)

If you prefer a terminal command:

```bash
# Install Python 3.8+ first
pip3 install flask flask-cors ib_insync
python3 tlade_bridge_lite.py
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

### Bridge won't start / "Address already in use"

Port 5000 is already taken by another process. Find out what:
```bash
# Windows
netstat -ano | findstr :5000

# Mac/Linux
lsof -i :5000
```
Common culprits: another bridge instance, AirPlay Receiver (Mac port 5000), or a local dev server. Kill the process or change the bridge port:
```bash
set BRIDGE_PORT=5001
python tlade_bridge_lite.py
```
> Note: TLADe terminal currently auto-detects only port 5000. Custom port support coming soon.

### "IB not connected" in TLADe terminal

1. **Is TWS running?** The bridge needs TWS or IB Gateway open
2. **Is the API enabled?** TWS > File > Global Configuration > API > Settings:
   - "Enable ActiveX and Socket Clients" must be checked
   - Port must match (default: **7496** live, **7497** paper)
3. **Is the port correct?** Check what TWS is actually listening on:
   ```bash
   # Windows
   netstat -ano | findstr :7496
   ```
   If no result, TWS isn't listening. Double-check the API settings and restart TWS.
4. **Firewall?** Windows Defender or antivirus may block localhost connections. Allow Python through the firewall.
5. **Client ID conflict?** If you have other TWS API connections (MultiCharts, Sierra Chart, etc.), they may use the same client ID. Change it:
   ```bash
   set IB_CLIENT=20
   python tlade_bridge_lite.py
   ```

### "No data for ES" / "No data for NQ"

- **Market data subscription required.** Your IB account must have CME real-time data. Check in TWS: Account > Market Data Subscriptions.
- **Contract not found.** This can happen briefly during futures roll week. The bridge auto-selects the front-month contract — wait a minute and retry.
- **Paper account limitations.** Paper trading accounts have delayed/limited data. Some market data may not stream via API. Try with a live account.

### Bridge connects but TLADe doesn't show live data

1. Open browser console (F12) and check for `[IB] TWS detected` message
2. If you see `[IB Detector] Started health polling` but no detection:
   - The bridge may be on a different port — verify it's on 5000
   - Try opening `http://localhost:5000/health` in your browser — you should see JSON with `"ib_connected": true`
3. **HTTPS/Mixed content issue:** If you're on `https://tradelikeadealer.com`, the browser blocks `http://localhost` requests on some configurations. Check console for "Mixed Content" errors.

### Python not found

**Windows (`start.bat`):**
- Make sure you checked **"Add Python to PATH"** during Python installation
- If you installed Python but `start.bat` still can't find it, restart your terminal/PC
- Or run manually: `C:\Users\YourName\AppData\Local\Programs\Python\Python3x\python.exe tlade_bridge_lite.py`

**macOS (`start.command`):**
- Install Python from [python.org](https://www.python.org/downloads/) or `brew install python3`
- Verify with: `python3 --version`
- Re-open `start.command` after install

### pip install fails

- **Behind corporate proxy:** `pip install --proxy http://your-proxy:port flask flask-cors ib_insync`
- **Permission error:** Try `pip install --user flask flask-cors ib_insync`
- **Old pip:** `python -m pip install --upgrade pip` then retry
