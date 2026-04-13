#!/bin/bash
# TLADe Bridge — Rithmic R|Protocol (macOS)
# Double-click this file in Finder to launch.
# First-time only: if macOS blocks it, right-click → Open, or run:
#   chmod +x start.command

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "  ========================================"
echo "   TLADe Bridge - Rithmic (R|Protocol)"
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
    echo "  Installing flask, flask-cors, async_rithmic..."
    if ! pip3 install flask flask-cors async_rithmic; then
        echo ""
        echo "  [!] pip install failed. Try manually:"
        echo "      pip3 install flask flask-cors async_rithmic"
        echo ""
        read -n 1 -s -r -p "  Press any key to exit..."
        exit 1
    fi
    echo ""
elif ! python3 -c "import async_rithmic" >/dev/null 2>&1; then
    echo "  Installing async_rithmic..."
    pip3 install async_rithmic
fi
echo "  [OK] Dependencies ready"
echo ""

# ── Load saved config ──
CONFIG_FILE="$DIR/.rithmic_config"
SETUP=0
if [ -f "$CONFIG_FILE" ]; then
    echo "  [OK] Loading saved configuration..."
    # shellcheck disable=SC1090
    . "$CONFIG_FILE"
    echo "   User:   $RITHMIC_USER"
    echo "   System: $RITHMIC_SYSTEM"
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
    echo "  Supported systems:"
    echo "    Apex, TopstepTrader, Bulenox, Earn2Trade,"
    echo "    10XFutures, 4PropTrader, DayTraders.com,"
    echo "    LegendsTrading, LucidTrading, MES Capital,"
    echo "    PropShopTrader, TradeFundrr, Tradeify,"
    echo "    ThriveTrading, Rithmic 01, Rithmic Paper Trading"
    echo ""

    read -r -p "   Rithmic User ID: " RITHMIC_USER
    # Hide password input
    read -r -s -p "   Rithmic Password: " RITHMIC_PASS
    echo ""
    read -r -p "   System name (e.g. Apex): " RITHMIC_SYSTEM

    RITHMIC_GATEWAY="wss://rithmic.com:443"
    RITHMIC_GATEWAY_IP="34.254.173.171"
    echo ""
    read -r -p "   Region - (E)urope or (U)S? [E]: " REGION
    case "$REGION" in
        u|U)
            RITHMIC_GATEWAY_IP="38.79.0.86"
            echo "  [OK] Using US gateway"
            ;;
        *)
            echo "  [OK] Using Europe gateway"
            ;;
    esac

    {
        echo "RITHMIC_USER=\"$RITHMIC_USER\""
        echo "RITHMIC_PASS=\"$RITHMIC_PASS\""
        echo "RITHMIC_SYSTEM=\"$RITHMIC_SYSTEM\""
        echo "RITHMIC_GATEWAY=\"$RITHMIC_GATEWAY\""
        echo "RITHMIC_GATEWAY_IP=\"$RITHMIC_GATEWAY_IP\""
    } > "$CONFIG_FILE"
    # Protect credentials: owner read/write only
    chmod 600 "$CONFIG_FILE" 2>/dev/null || true
    echo ""
    echo "  [OK] Configuration saved to .rithmic_config"
    echo ""
fi

# ── Launch ──
echo "  ----------------------------------------"
echo ""
echo "  IMPORTANT: Close RTrader Pro or NinjaTrader"
echo "  before starting (one market data session only)."
echo ""
echo "  Starting bridge..."
echo "  Press Ctrl+C to stop."
echo ""

export RITHMIC_USER RITHMIC_PASS RITHMIC_SYSTEM RITHMIC_GATEWAY RITHMIC_GATEWAY_IP
python3 "$DIR/tlade_bridge_rithmic.py"

echo ""
read -n 1 -s -r -p "  Bridge stopped. Press any key to close this window..."
