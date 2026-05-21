#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mihai Ostafe — TLADe ATAS Bridge contribution
# Copyright (c) 2026 TLADe — Trade Like a Dealer (https://tradelikeadealer.com)
"""
TLADe Level Pusher  v1.1.0

Parse the GEX string from the TLADe Terminal (same format as the TV Pine
Script indicator) and POST the levels to the ATAS bridge at /push_levels.

Run modes:
  python tlade_push_levels.py              -> interactive: manual paste + Enter x2
  python tlade_push_levels.py --watch      -> automatic clipboard watcher (recommended)
  python tlade_push_levels.py --file X.txt -> read from a text file
  python tlade_push_levels.py --data "S:.."-> send a string directly

Recommended workflow (watch mode):
  1. Start: python tlade_push_levels.py --watch
  2. In the TLADe Terminal copy the GEX string (TV / Copy / Export button)
  3. The script auto-detects the clipboard and pushes to the bridge
  4. The ATAS TLADe Levels indicator refreshes in < 60 seconds

TLADe data format (identical to the Pine Script input.text_area):
  S:30.46|L:7103,ZG,ZERO GAMMA,tooltip,0;7055,MP,MAX PAIN,...|P:7075,0.2,1;...

  S: = ES-SPX spread (points)
  L: = levels: price,code,label,tooltip~...,magnitude
  P: = GEX profile: price,strength,sign (ignored by ATAS — not needed)

Type codes (L:):
  ZG  = Zero Gamma       MP  = Max Pain
  EH  = EM High          EL  = EM Low
  VH  = Vol Band High    VL  = Vol Band Low
  CW  = Call Wall        PW  = Put Wall
  PDH = Prior Day High   PDL = Prior Day Low
  PWH = Prior Week High  PWL = Prior Week Low

Install dependencies:
  pip install requests pyperclip
"""

import sys
import time
import json
import argparse
from datetime import datetime

try:
    import requests
except ImportError:
    print("[ERROR] Install requests: pip install requests")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────────

BRIDGE_URL  = "http://localhost:5000"
DEFAULT_TICKER = "ES"

# Minimum keywords to recognize a TLADe GEX string in clipboard
TLADE_MARKERS = ["|L:", "S:", ",ZG,", ",MP,", ",CW,", ",PW,", ",EH,", ",EL,"]

# Pine-Script code -> internal type (used for colours in TLAdeLevels.cs)
TYPE_MAP = {
    "ZG":  "zero_gamma",
    "MP":  "max_pain",
    "EH":  "em_high",
    "EL":  "em_low",
    "VH":  "vol_band_up",
    "VL":  "vol_band_down",
    "CW":  "call_wall",
    "PW":  "put_wall",
    "PDH": "structure_pdh",
    "PDL": "structure_pdl",
    "PWH": "structure_pwh",
    "PWL": "structure_pwl",
}


# ── Parser ─────────────────────────────────────────────────────────────────────

def parse_tlade_string(raw: str) -> tuple[float, list[dict]]:
    """
    Parse the TLADe GEX string in the format used by the Pine Script indicator.
    Returns (es_spx_spread, list_of_levels).

    L: entry format:
      price,code,label,tooltip~tip2~tip3,magnitude_M
    """
    raw = raw.strip().replace("\n", "").replace("\r", "")
    spread = 24.0
    levels = []

    # 1) Extract spread S:XX.XX|...
    if raw.startswith("S:"):
        pipe = raw.find("|")
        if pipe > 2:
            try:
                spread = float(raw[2:pipe])
            except ValueError:
                pass
            raw = raw[pipe + 1:]

    # 2) Split L: from P:
    levels_raw = ""
    if "|P:" in raw:
        pipe = raw.find("|P:")
        levels_raw = raw[:pipe]
    elif raw.startswith("L:") or "," in raw:
        levels_raw = raw
    else:
        levels_raw = raw

    # 3) Strip L: prefix
    if levels_raw.startswith("L:"):
        levels_raw = levels_raw[2:]

    if not levels_raw.strip():
        return spread, levels

    # 4) Parse each "price,code,label,tooltip,mag" entry
    for entry in levels_raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(",")
        if len(parts) < 2:
            continue

        try:
            price = float(parts[0])
        except ValueError:
            continue

        code  = parts[1].strip().upper()
        label_name = parts[2].strip() if len(parts) >= 3 else code
        # parts[3] = tooltip (ignored)
        mag = 0.0
        if len(parts) >= 5:
            try:
                mag = float(parts[4])
            except ValueError:
                pass

        mapped = TYPE_MAP.get(code, "other")

        # Build display label (same as Pine Script: "7103 ZG Zero Gamma")
        label = f"{price:.2f} {code} {label_name}"

        levels.append({
            "price":     price,
            "type":      mapped,
            "label":     label,
            "magnitude": round(mag, 2),
        })

    return spread, levels


def _looks_like_tlade(text: str) -> bool:
    """Quick check whether a string looks like TLADe GEX data."""
    if not text or len(text) < 20:
        return False
    # Must contain at least 2 TLADe markers
    hits = sum(1 for m in TLADE_MARKERS if m in text)
    return hits >= 2


def _summarize(levels: list) -> str:
    """Compact log summary."""
    counts = {}
    for lv in levels:
        t = lv["type"]
        counts[t] = counts.get(t, 0) + 1
    parts = [f"{v}x {k}" for k, v in sorted(counts.items())]
    return ", ".join(parts) if parts else "0 levels"


# ── Push to bridge ─────────────────────────────────────────────────────────────

def push_levels(levels: list, ticker: str, url: str) -> bool:
    """Send the parsed levels to the ATAS bridge."""
    if not levels:
        print("[WARN] No levels parsed; nothing to send.")
        return False

    payload = {"ticker": ticker, "levels": levels}
    try:
        resp = requests.post(f"{url}/push_levels", json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] PUSH OK — {data.get('count', len(levels))} levels "
                  f"-> {ticker} ({_summarize(levels)})")
            return True
        print(f"[ERROR] Bridge response: {data}")
        return False
    except requests.ConnectionError:
        print(f"[ERROR] Bridge not responding at {url}.")
        print("        Is `python tlade_bridge_atas.py` running?")
        return False
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return False


def process_raw(raw: str, ticker: str, url: str):
    """Parse + push a raw string."""
    spread, levels = parse_tlade_string(raw)
    print(f"  ES/SPX spread parsed: {spread} points")
    print(f"  Levels found:         {len(levels)}")
    if levels:
        push_levels(levels, ticker, url)
    else:
        print("[WARN] No valid levels parsed. Check the string format.")


# ── Run modes ──────────────────────────────────────────────────────────────────

def interactive_mode(ticker: str, url: str):
    """Manual paste + Enter x2."""
    print("=" * 60)
    print(f"  TLADe Level Pusher — Interactive mode  (ticker={ticker})")
    print("=" * 60)
    print()
    print("How to grab the GEX string from TLADe:")
    print("  1. In the TLADe Terminal, open the TV indicator (GEX Levels)")
    print("  2. Copy the 'GEX Data' field content (input.text_area)")
    print("  3. Paste below and press Enter TWICE:")
    print()

    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        return

    raw = " ".join(lines).strip()
    if not raw:
        print("[ERROR] Empty string — nothing to send.")
        return

    process_raw(raw, ticker, url)


def watch_clipboard_mode(ticker: str, url: str, interval: float = 1.5):
    """Clipboard watcher — auto-detects the GEX string."""
    try:
        import pyperclip
    except ImportError:
        print("[ERROR] Install pyperclip: pip install pyperclip")
        print("        Then run again with --watch")
        return

    print("=" * 60)
    print(f"  TLADe Level Pusher — Clipboard Watcher  (ticker={ticker})")
    print("=" * 60)
    print()
    print("Waiting for a GEX string on the clipboard...")
    print("  -> Copy the string from the TLADe Terminal / Pine Script")
    print("  -> The bridge updates automatically")
    print("  -> The ATAS TLADe Levels indicator repaints in < 60s")
    print()
    print("Ctrl+C to stop.")
    print()

    last_seen = ""
    try:
        while True:
            try:
                clip = pyperclip.paste() or ""
            except Exception:
                clip = ""

            # Detect a new TLADe string
            if clip != last_seen and _looks_like_tlade(clip):
                last_seen = clip
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] TLADe string detected on clipboard! Parsing...")
                process_raw(clip, ticker, url)
                print()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nClipboard watcher stopped.")


def file_mode(filepath: str, ticker: str, url: str):
    """Read the string from a text file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except FileNotFoundError:
        print(f"[ERROR] File '{filepath}' does not exist.")
        return
    print(f"Read {len(raw)} characters from '{filepath}'")
    process_raw(raw, ticker, url)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="TLADe Level Pusher — send GEX levels to the ATAS bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tlade_push_levels.py                    # interactive: manual paste
  python tlade_push_levels.py --watch            # clipboard watcher (recommended)
  python tlade_push_levels.py --watch --ticker NQ
  python tlade_push_levels.py --file gex_data.txt
  python tlade_push_levels.py --data "S:30.46|L:..."
        """,
    )
    p.add_argument("--ticker",   default=DEFAULT_TICKER, choices=["ES", "NQ"],
                   help=f"Ticker (default: {DEFAULT_TICKER})")
    p.add_argument("--url",      default=BRIDGE_URL,
                   help=f"ATAS bridge URL (default: {BRIDGE_URL})")
    p.add_argument("--watch",    action="store_true",
                   help="Automatic clipboard watcher (detects TLADe strings)")
    p.add_argument("--interval", type=float, default=1.5,
                   help="Clipboard check interval in seconds (default: 1.5)")
    p.add_argument("--file",     metavar="PATH",
                   help="Read the string from a file")
    p.add_argument("--data",     metavar="STRING",
                   help="GEX string passed directly as CLI argument")
    args = p.parse_args()

    if args.data:
        process_raw(args.data, args.ticker, args.url)
    elif args.file:
        file_mode(args.file, args.ticker, args.url)
    elif args.watch:
        watch_clipboard_mode(args.ticker, args.url, args.interval)
    else:
        interactive_mode(args.ticker, args.url)


if __name__ == "__main__":
    main()
