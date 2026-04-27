# TLADe Rithmic Bridge — macOS Setup

Step-by-step guide to connect your Rithmic account to TLADe on a Mac. No terminal commands required.

> **Note:** Rithmic is primarily used on Windows. This macOS setup works, but some Rithmic-related tools (RTrader Pro, etc.) are Windows-only. If you hit blockers, the [NinjaTrader bridge](../ninjatrader/) is an alternative — NT8 supports Rithmic and runs via Crossover or a Windows VM on Mac.

## ⚠️ Before you start — One Market Data Session

Rithmic allows only **one Market Data session at a time** per account. **Close any other application using your Rithmic market data before launching the bridge** (RTrader Pro, NinjaTrader, etc.), otherwise you'll get authentication errors.

## Step 1 — Gather your Rithmic credentials

You'll need three things from your broker:

1. **Username** — your Rithmic login
2. **Password** — your Rithmic password
3. **System name** — e.g., `Apex`, `TopstepTrader`, `Rithmic 01`, `Bulenox`, etc. Must match **exactly** what your broker provided (case-sensitive).

## Step 2 — Download the bridge

1. Download the `bridges/rithmic/` folder from this GitHub repo
2. Place it somewhere you can find — e.g., Desktop or Documents

## Step 3 — Launch the bridge

1. Open Finder and go to the `bridges/rithmic` folder
2. **Right-click `start.command`** → select **Open**
3. macOS will show a security warning — click **Open** again
4. A Terminal window opens automatically

### What happens on first launch

- The script checks if Python 3 is installed
- It installs the required Python packages (`flask`, `flask-cors`, `async_rithmic`)
- It asks you for your Rithmic username, password, and system name
- **Your password is hidden as you type** — don't worry if you see nothing, it's recording
- It saves to `.rithmic_config` so you won't be asked again
- It launches the bridge

> **Important:** Leave the Terminal window open while you trade. Closing it = stopping the bridge.

macOS will remember the security choice — next time you can double-click `start.command` directly.

## Step 4 — Open TLADe

Go to [tradelikeadealer.com](https://tradelikeadealer.com) and open the terminal. The live data indicator will switch on automatically within a few seconds.

**There are no API keys, headers, or endpoints to configure.** The terminal detects the bridge on `localhost:5000` on its own.

## About the "terminate running processes" dialog

When you close the Terminal window running the bridge, macOS shows:

> *"Do you want to terminate running processes in this window? Closing this window will terminate the running process bash."*

**This is normal macOS behavior, not an error.** Clicking **Terminate** simply stops the bridge. Nothing is lost.

## Python not installed?

**Option A — python.org (recommended for non-technical users):**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest macOS installer, run it, accept defaults
3. Re-open `start.command`

**Option B — Homebrew (for developers):**
```bash
brew install python3
```

Verify with:
```bash
python3 --version
```

## Troubleshooting

### "Already connected" or auth failures

This is the **#1 most common error**. Cause: another app is using your Rithmic Market Data session. Close any other Rithmic-connected application. Only one Market Data session at a time is allowed per account.

### `You must specify valid SYSTEM_NAME in the credentials: ['Rithmic Test']`

This error is **almost always a region mismatch**, not a credential problem. Rithmic provisions accounts on a specific regional cluster (EU or US). If you pick the wrong region during setup, the gateway you connect to doesn't have your account on its allow-list and returns this misleading message.

**Fix in 30 seconds:**

1. Stop the bridge (Ctrl+C in the Terminal window, or close it)
2. In Finder, open the bridge folder and **delete the file `.rithmic_config`**
   - File hidden? Press `Cmd+Shift+.` to toggle hidden files
3. Right-click `start.command` → **Open** to relaunch
4. Re-enter your Rithmic credentials
5. When asked **"Region - (E)urope or (U)S? [E]:"**, **try the OTHER region** from what you picked last time
   - Most Apex / Topstep / Bulenox accounts are routed via **Europe** — pick `e`
   - If you already tried Europe and it failed, then try `u`

You should see `[Rithmic] Connected!` followed by ES + NQ streaming.

If both regions return the same `['Rithmic Test']` error, your account is genuinely restricted server-side — open a ticket with your prop firm support attaching this README section.

### Wrong credentials

Double-check username, password, and system name (case-sensitive, must match exactly what your broker provides).

To reset saved credentials, delete the `.rithmic_config` file in `bridges/rithmic/` and re-run `start.command`.

### DNS resolution errors

Some ISPs append a search suffix that breaks Rithmic hostname resolution. Set the gateway IP explicitly before launching:
```bash
export RITHMIC_GATEWAY_IP="34.254.173.171"
python3 tlade_bridge_rithmic.py
```

### "Address already in use" on port 5000

On macOS the most common cause is **AirPlay Receiver**. Disable it:

**System Settings → General → AirDrop & Handoff → AirPlay Receiver → Off**

Or find and kill the conflicting process:
```bash
lsof -i :5000
kill -9 <PID>
```

### Gatekeeper keeps blocking `start.command`

Run once in Terminal:
```bash
cd /path/to/bridges/rithmic
chmod +x start.command
xattr -d com.apple.quarantine start.command
```

After this, double-click works normally.

## Manual Setup (advanced)

```bash
cd /path/to/bridges/rithmic
pip3 install flask flask-cors async_rithmic

export RITHMIC_USER="your_username"
export RITHMIC_PASS="your_password"
export RITHMIC_SYSTEM="Apex"

python3 tlade_bridge_rithmic.py
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
