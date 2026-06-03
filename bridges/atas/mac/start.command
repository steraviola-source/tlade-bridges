#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# TLADe Bridge - ATAS X (macOS) — equivalent of start.bat
# Double-click in Finder or run from Terminal.

set -u

cd "$(dirname "$0")"

echo
echo "  ====================================="
echo "   TLADe Bridge - ATAS X Edition (Mac)"
echo "  ====================================="
echo
echo "  Architecture:"
echo "    ATAS X (Rithmic/CQG)"
echo "      -> TLAdeBridgeATAS.dll (ATAS indicator, HTTP push)"
echo "            -> tlade_bridge_atas.py (receiver, localhost:5000)"
echo "                  -> TLADe Terminal (auto-detects on localhost:5000)"
echo

# ── Detect Python ──
PYTHON=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON="$cand"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  [!] Python not found."
    echo
    echo "  TLADe Bridge requires Python 3.8+."
    echo "  Install from: https://www.python.org/downloads/macos/"
    echo "  or: brew install python3"
    echo
    read -n 1 -s -r -p "  Press any key to close..."
    exit 1
fi

PYVER=$("$PYTHON" --version 2>&1 | awk '{print $2}')
echo "  [OK] Python $PYVER found ($PYTHON)"
echo

# ── Check/install dependencies ──
echo "  Checking dependencies (flask, flask-cors)..."
if ! "$PYTHON" -c "import flask, flask_cors" >/dev/null 2>&1; then
    echo "  Installing flask flask-cors..."
    # --user avoids permissions / PEP 668 issues with the system Python
    "$PYTHON" -m pip install --user --quiet flask flask-cors 2>/dev/null \
        || "$PYTHON" -m pip install --user --break-system-packages --quiet flask flask-cors
    if ! "$PYTHON" -c "import flask, flask_cors" >/dev/null 2>&1; then
        echo "  [!] flask/flask-cors cannot be imported after install."
        echo
        echo "  Try manually in Terminal:"
        echo "      $PYTHON -m pip install --user flask flask-cors"
        echo "  then verify:"
        echo "      $PYTHON -c 'import flask, flask_cors'"
        echo
        read -n 1 -s -r -p "  Press any key to close..."
        exit 1
    fi
fi
echo "  [OK] Dependencies OK"
echo

# ── Check whether port 5000 is in use ──
if lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "  [!] Port 5000 is already in use by another process."
    echo "      Inspect with: lsof -nP -iTCP:5000 -sTCP:LISTEN"
    echo
    echo "  NOTE: on macOS, AirPlay Receiver uses port 5000 by default."
    echo "  If that's the cause: System Settings -> General -> AirDrop & Handoff"
    echo "  -> turn OFF 'AirPlay Receiver'."
    echo
    read -n 1 -s -r -p "  Press any key to close..."
    exit 1
fi

# ── Launch ──
echo "  Starting TLADe ATAS Bridge..."
echo "  Waiting for data from the TLAdeBridgeATAS indicator in ATAS X..."
echo
echo "  (Leave this window open while you trade)"
echo
exec "$PYTHON" "$(dirname "$0")/tlade_bridge_atas.py"
