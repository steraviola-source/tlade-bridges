# TLADe Rithmic Bridge — Windows Setup

Step-by-step guide to connect your Rithmic account to TLADe on Windows. No command-line knowledge required.

## ⚠️ Before you start — One Market Data Session

Rithmic allows only **one Market Data session at a time** per account. **Close RTrader Pro, NinjaTrader (if connected via Rithmic), or any other Rithmic-connected platform before launching the bridge.** Otherwise you'll get authentication errors.

## Step 1 — Install Python (once)

If you don't already have Python 3:

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Windows installer
3. **Important:** during install, check **"Add Python to PATH"** on the first screen
4. Click **Install Now** and wait

Verify: open a new Command Prompt and type:
```
python --version
```
You should see `Python 3.12.x` or similar.

## Step 2 — Gather your Rithmic credentials

You'll need three things from your broker or Rithmic account:

1. **Username** — your Rithmic login
2. **Password** — your Rithmic password
3. **System name** — e.g., `Apex`, `TopstepTrader`, `Rithmic 01`, `Bulenox`, etc. Must match **exactly** what your broker provided (case-sensitive). Check your broker's Rithmic setup docs if unsure.

## Step 3 — Download the bridge

1. Download the `bridges/rithmic/` folder from this GitHub repo
2. Place it somewhere you can find — e.g., `C:\TLADe\bridges\rithmic`

## Step 4 — Launch the bridge

1. Open the folder `bridges\rithmic` in File Explorer
2. **Double-click `start.bat`**
3. Windows SmartScreen may show a warning:
   > *"Windows protected your PC"*
   Click **More info → Run anyway**
4. A Command Prompt window opens

### What happens on first launch

- The script checks if Python is installed
- It installs the required packages (`flask`, `flask-cors`, `async_rithmic`)
- It asks you for your Rithmic username, password, and system name
- **Your password is hidden as you type** — don't worry if you see nothing on screen, it's recording
- It saves these to `.rithmic_config` so you won't be asked again
- It launches the bridge

When the bridge connects you'll see it start streaming data.

> **Important:** Leave the Command Prompt window open while you trade. Closing it = stopping the bridge. You can minimize it.

## Step 5 — Open TLADe

Go to [tradelikeadealer.com](https://tradelikeadealer.com) and open the terminal. The live data indicator will switch on automatically within a few seconds.

**There are no API keys, headers, or endpoints to configure.** The terminal detects the bridge on `localhost:5000` on its own.

## Troubleshooting

### "Already connected" or auth failures

This is the **#1 most common error**. Cause: another app is using your Rithmic Market Data session. Close:

- RTrader Pro
- NinjaTrader (if it connects via Rithmic)
- Any other Rithmic-connected platform

Then re-launch the bridge.

### Wrong credentials

Double-check username, password, and system name. The system name must match **exactly** what your broker provides — e.g., `Apex` not `apex`, `TopstepTrader` not `Topstep`.

To reset saved credentials, delete the `.rithmic_config` file in `bridges\rithmic\` and re-run `start.bat`.

### DNS resolution errors

Some ISPs append a search suffix that breaks Rithmic hostname resolution. Fix by setting the gateway IP explicitly. In PowerShell:
```powershell
$env:RITHMIC_GATEWAY_IP = "34.254.173.171"
python tlade_bridge_rithmic.py
```

### "Python is not recognized"

Python is not in your PATH. Re-run the Python installer and make sure **"Add Python to PATH"** is checked on the first screen. Or uninstall and reinstall with that option enabled.

### "Address already in use" on port 5000

Another program is using port 5000. Find it:
```
netstat -ano | findstr :5000
```
Kill it from Task Manager (match the PID), or change the bridge port:
```
set BRIDGE_PORT=5001
python tlade_bridge_rithmic.py
```
> Note: TLADe currently auto-detects only port 5000. Custom port support coming soon.

### SmartScreen keeps blocking `start.bat`

Right-click `start.bat` → **Properties** → check **Unblock** at the bottom → **OK**.

## Manual Setup (advanced)

```powershell
cd C:\TLADe\bridges\rithmic
pip install flask flask-cors async_rithmic

$env:RITHMIC_USER = "your_username"
$env:RITHMIC_PASS = "your_password"
$env:RITHMIC_SYSTEM = "Apex"

python tlade_bridge_rithmic.py
```

## Configuration (advanced)

| Env Variable | Default | Description |
|---|---|---|
| `RITHMIC_USER` | *(required)* | Your Rithmic username |
| `RITHMIC_PASS` | *(required)* | Your Rithmic password |
| `RITHMIC_SYSTEM` | *(required)* | System name (Apex, TopstepTrader, etc.) |
| `RITHMIC_GATEWAY` | `wss://rithmic.com:443` | WebSocket gateway URL |
| `RITHMIC_GATEWAY_IP` | `34.254.173.171` | Gateway IP (default is EU) |
| `BRIDGE_PORT` | `5000` | Local port for the bridge server |

## Questions?

📧 support@tradelikeadealer.com
