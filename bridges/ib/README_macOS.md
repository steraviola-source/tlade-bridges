# TLADe IB Bridge — macOS Setup

Step-by-step guide to connect your TWS to TLADe on a Mac. No terminal commands, no Python knowledge required.

## Step 1 — Enable the API in TWS

Open TWS and go to:
**File → Global Configuration → API → Settings**

Check the following:
- ✅ **Enable ActiveX and Socket Clients**
- Socket port: **7496** (live account) or **7497** (paper account)
- ✅ **Allow connections from localhost only**

Click **Apply**, then **OK**. Restart TWS if prompted.

## Step 2 — Download the bridge

1. Download the `bridges/ib/` folder from this GitHub repo (or clone the whole `tlade-bridges` repo)
2. Place it somewhere you can find — e.g., Desktop or Documents

## Step 3 — Launch the bridge

1. Open Finder and go to the `bridges/ib` folder
2. **Right-click `start.command`** → select **Open**
3. macOS will show a security warning: *"start.command cannot be opened because it is from an unidentified developer"* — this is normal for downloaded scripts
4. Click **Open** in the warning dialog
5. A Terminal window opens automatically and runs the bridge

macOS will remember this choice — next time you can simply **double-click** `start.command`.

### What happens on first launch

- The script checks if Python 3 is installed
- It installs the required Python packages automatically (`flask`, `flask-cors`, `ib_insync`)
- It asks you for your TWS port (7496 or 7497) and a client ID (default `10` is fine)
- It saves these to `.ib_config` so you won't be asked again
- It launches the bridge

When you see this output, the bridge is running:

```
  TLADe Bridge Lite
  TWS 127.0.0.1:7496 → localhost:5000

[IB] Connecting to 127.0.0.1:7496...
[IB] Connected
[IB] ES: ESM6
[IB] NQ: NQM6
[IB] ES + NQ streaming
```

> **Important:** Leave the Terminal window open while you trade. Closing it = stopping the bridge.

## Step 4 — Open TLADe

Go to [tradelikeadealer.com](https://tradelikeadealer.com) and open the terminal. The live data indicator will switch on automatically within a few seconds.

**There are no API keys, headers, or endpoints to configure.** The terminal detects the bridge on `localhost:5000` on its own.

## About the "terminate running processes" dialog

When you close the Terminal window running the bridge, macOS shows:

> *"Do you want to terminate running processes in this window? Closing this window will terminate the running process bash."*

**This is normal macOS behavior, not an error.** Clicking **Terminate** simply stops the bridge. Nothing is lost or broken.

## Python not installed?

If you see "Python 3 is required" when running `start.command`:

**Option A — python.org (recommended for non-technical users):**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest macOS installer
3. Run the installer, accept defaults
4. Re-open `start.command`

**Option B — Homebrew (for developers):**
```bash
brew install python3
```

Verify with:
```bash
python3 --version
```

## Troubleshooting

### The Terminal window opens, then closes immediately

Open the folder again, right-click `start.command` → **Open With → Terminal**. This keeps the window open so you can read the error message. Send a screenshot to support if needed.

### "Address already in use" on port 5000

Port 5000 is already taken. On macOS the most common cause is **AirPlay Receiver** — disable it:

**System Settings → General → AirDrop & Handoff → AirPlay Receiver → Off**

Or find and kill the conflicting process:
```bash
lsof -i :5000
kill -9 <PID>
```

### "IB not connected" in TLADe terminal

1. **Is TWS running and logged in?** The bridge cannot connect if TWS is closed
2. **Did you enable the API in TWS?** (See Step 1)
3. **Does the TWS port match?** Default **7496** live, **7497** paper
4. Open `http://localhost:5000/health` in your browser — you should see JSON with `"ib_connected": true`. If not, the bridge isn't talking to TWS

### "No data for ES / NQ"

Your IB account needs a CME real-time data subscription. Check in TWS:
**Account → Market Data Subscriptions**

Paper trading accounts have limited data — some feeds don't stream via API. For full functionality, use a live account.

### Gatekeeper keeps blocking `start.command`

Open Terminal and run once:
```bash
cd /path/to/bridges/ib
chmod +x start.command
xattr -d com.apple.quarantine start.command
```

After this, double-click works normally.

## Manual Setup (advanced)

If you prefer to run the bridge from Terminal directly:

```bash
cd /path/to/bridges/ib
pip3 install flask flask-cors ib_insync
python3 tlade_bridge_lite.py
```

## Configuration (advanced)

Environment variables (all optional — set them before launching the script):

| Variable | Default | Description |
|---|---|---|
| `IB_HOST` | `127.0.0.1` | TWS host |
| `IB_PORT` | `7496` | TWS API port (`7497` for paper) |
| `IB_CLIENT` | `10` | Client ID (use different IDs for multiple connections) |
| `BRIDGE_PORT` | `5000` | Bridge HTTP port |

Example (paper trading):
```bash
IB_PORT=7497 python3 tlade_bridge_lite.py
```

## Endpoints

| Endpoint | Description |
|---|---|
| `/health` | Connection status |
| `/ib_data?ticker=ES` | Live 5min candles (2 weeks) |
| `/ib_daily?ticker=ES` | 1Y daily bars |
| `/ib_history?ticker=ES` | 2W 5min bars (real volume) |

## Questions?

📧 support@tradelikeadealer.com
