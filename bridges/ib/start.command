#!/bin/bash
# TLADe Bridge — Interactive Brokers (macOS)
# Double-click this file in Finder to launch.
# First-time only: if macOS blocks it, right-click → Open, or run:
#   chmod +x start.command

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "  ========================================"
echo "   TLADe Bridge Lite - Interactive Brokers"
echo "  ========================================"
echo ""

# ── Check Python 3 ──
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [!] Python 3 not found."
    echo ""
    echo "  TLADe Bridge requires Python 3.8 or later."
    echo "  Install one of:"
    echo "    - From https://www.python.org/downloads/"
    echo "    - Via Homebrew:  brew install python3"
    echo ""
    echo "  After installing Python, re-open this script."
    echo ""
    read -n 1 -s -r -p "  Press any key to exit..."
    exit 1
fi

PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "  [OK] Python $PYVER found"
echo ""

# ── Check/install dependencies ──
echo "  Checking dependencies..."
if ! python3 -c "import flask" >/dev/null 2>&1; then
    echo "  Installing flask, flask-cors, ib_insync..."
    if ! pip3 install flask flask-cors ib_insync; then
        echo ""
        echo "  [!] pip install failed. Try manually:"
        echo "      pip3 install flask flask-cors ib_insync"
        echo ""
        read -n 1 -s -r -p "  Press any key to exit..."
        exit 1
    fi
    echo ""
elif ! python3 -c "import ib_insync" >/dev/null 2>&1; then
    echo "  Installing ib_insync..."
    pip3 install ib_insync
fi
echo "  [OK] Dependencies ready"
echo ""

# ── Load saved config ──
CONFIG_FILE="$DIR/.ib_config"
SETUP=0
if [ -f "$CONFIG_FILE" ]; then
    echo "  [OK] Loading saved configuration..."
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
    echo "   TWS Host:  $IB_HOST"
    echo "   TWS Port:  $IB_PORT"
    echo "   Client ID: $IB_CLIENT"
    echo ""
    read -r -p "   Use these settings? (Y/n): " REUSE
    case "$REUSE" in
        n|N) SETUP=1 ;;
    esac
else
    SETUP=1
fi

if [ "$SETUP" = "1" ]; then
    echo ""
    echo "  ----------------------------------------"
    echo "  First-time setup"
    echo "  ----------------------------------------"
    echo ""
    echo "  Make sure TWS or IB Gateway is running"
    echo "  with API enabled (File > Global Configuration"
    echo "  > API > Settings > Enable Socket Clients)"
    echo ""

    IB_HOST="127.0.0.1"
    read -r -p "   TWS API port (7496=live, 7497=paper) [7496]: " IB_PORT
    [ -z "$IB_PORT" ] && IB_PORT=7496
    read -r -p "   Client ID (change if other apps use TWS) [10]: " IB_CLIENT
    [ -z "$IB_CLIENT" ] && IB_CLIENT=10

    {
        echo "IB_HOST=\"$IB_HOST\""
        echo "IB_PORT=\"$IB_PORT\""
        echo "IB_CLIENT=\"$IB_CLIENT\""
    } > "$CONFIG_FILE"
    echo ""
    echo "  [OK] Configuration saved to .ib_config"
    echo ""
fi

# ── Launch ──
echo "  ----------------------------------------"
echo ""
echo "  Starting bridge (TWS $IB_HOST:$IB_PORT)..."
echo "  Press Ctrl+C to stop."
echo ""

export IB_HOST IB_PORT IB_CLIENT
python3 "$DIR/tlade_bridge_lite.py"

echo ""
read -n 1 -s -r -p "  Bridge stopped. Press any key to close this window..."
