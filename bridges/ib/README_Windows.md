# TLADe IB Bridge — Windows Setup

Step-by-step guide to connect your TWS to TLADe on Windows. No command-line knowledge required.

## Step 1 — Enable the API in TWS

Open TWS and go to:
**File → Global Configuration → API → Settings**

Check the following:
- ✅ **Enable ActiveX and Socket Clients**
- Socket port: **7496** (live account) or **7497** (paper account)
- ✅ **Allow connections from localhost only**

Click **Apply**, then **OK**. Restart TWS if prompted.

## Step 2 — Install Python (once)

If you don't already have Python 3:

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Windows installer
3. **Important:** during install, check the box **"Add Python to PATH"** on the first screen
4. Click **Install Now** and wait for it to finish

Verify: open a new Command Prompt window and type:
```
python --version
```
You should see `Python 3.12.x` or similar.

## Step 3 — Download the bridge

1. Download the `bridges/ib/` folder from this GitHub repo (or clone the whole `tlade-bridges` repo)
2. Place it somewhere you can find — e.g., `C:\TLADe\bridges\ib`

## Step 4 — Launch the bridge

1. Open the folder `bridges\ib` in File Explorer
2. **Double-click `start.bat`**
3. Windows SmartScreen may show a warning:
   > *"Windows protected your PC"*
   Click **More info → Run anyway**
4. A Command Prompt window opens and runs automatically

### What happens on first launch

- The script checks if Python is installed
- It installs the required Python packages (`flask`, `flask-cors`, `ib_insync`)
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

> **Important:** Leave the Command Prompt window open while you trade. Closing it = stopping the bridge. You can minimize it.

## Step 5 — Open TLADe

Go to [tradelikeadealer.com](https://tradelikeadealer.com) and open the terminal. The live data indicator will switch on automatically within a few seconds.

**There are no API keys, headers, or endpoints to configure.** The terminal detects the bridge on `localhost:5000` on its own.

## Troubleshooting

### "Python is not recognized as an internal or external command"

Python is not in your PATH. Re-run the Python installer and make sure **"Add Python to PATH"** is checked on the first screen. Or uninstall and reinstall Python with that option enabled.

Alternative: launch the bridge with the full Python path:
```
C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe tlade_bridge_lite.py
```

### "Address already in use" on port 5000

Another program is using port 5000. Find out which one:
```
netstat -ano | findstr :5000
```
Common culprits: another bridge instance, a local dev server. Kill the process from Task Manager (match the PID from `netstat`), or change the bridge port:
```
set BRIDGE_PORT=5001
python tlade_bridge_lite.py
```
> Note: TLADe terminal currently auto-detects only port 5000. Custom port support coming soon.

### "IB not connected" in TLADe terminal

1. **Is TWS running and logged in?** The bridge cannot connect if TWS is closed
2. **Did you enable the API in TWS?** (See Step 1)
3. **Does the TWS port match?** Default **7496** live, **7497** paper
4. Check if TWS is actually listening on that port:
   ```
   netstat -ano | findstr :7496
   ```
   If no result, TWS isn't listening — double-check API settings and restart TWS
5. **Windows Firewall / antivirus** may block localhost connections. Allow `python.exe` through Windows Defender Firewall

### "No data for ES / NQ"

Your IB account needs a CME real-time data subscription. Check in TWS:
**Account → Market Data Subscriptions**

Paper trading accounts have limited data — some feeds don't stream via API. For full functionality, use a live account.

### pip install fails

- **Behind corporate proxy:**
  ```
  pip install --proxy http://your-proxy:port flask flask-cors ib_insync
  ```
- **Permission error:**
  ```
  pip install --user flask flask-cors ib_insync
  ```
- **Outdated pip:**
  ```
  python -m pip install --upgrade pip
  ```
  Then retry.

### SmartScreen keeps blocking `start.bat`

Right-click `start.bat` → **Properties** → check **Unblock** at the bottom → **OK**.

### The bridge runs, but TLADe never switches to live data (Chrome)

If the bridge is streaming in its own window and `http://localhost:5000/health` responds, but the terminal never picks up the live feed, the blocker is your browser — not the bridge.

Chrome is progressively rolling out a security policy called **Local Network Access**, which blocks websites loaded over HTTPS from reaching services on your own machine (`localhost`). When it applies, the terminal's requests to the bridge are silently blocked.

**Fix (Chrome):**

1. Open `chrome://flags/#local-network-access-check`
2. Set **Local Network Access Checks** to **Disabled**
3. Restart Chrome completely

Two caveats: the flag is version-dependent — it may be renamed or removed after a Chrome update, so if the bridge stops connecting right after updating Chrome, suspect this first. And the flag disables the check browser-wide, not just for TLADe.

**Alternative:** Firefox does not enforce this policy the same way and connects to the bridge out of the box.

## Manual Setup (advanced)

If you prefer to run the bridge from Command Prompt directly:

```
cd C:\TLADe\bridges\ib
pip install flask flask-cors ib_insync
python tlade_bridge_lite.py
```

## Configuration (advanced)

Environment variables (all optional — set them before launching the script in the same window):

| Variable | Default | Description |
|---|---|---|
| `IB_HOST` | `127.0.0.1` | TWS host |
| `IB_PORT` | `7496` | TWS API port (`7497` for paper) |
| `IB_CLIENT` | `10` | Client ID (use different IDs for multiple connections) |
| `BRIDGE_PORT` | `5000` | Bridge HTTP port |

Example (paper trading) in Command Prompt:
```
set IB_PORT=7497
python tlade_bridge_lite.py
```

In PowerShell:
```powershell
$env:IB_PORT = "7497"
python tlade_bridge_lite.py
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
