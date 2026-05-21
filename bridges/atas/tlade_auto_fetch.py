#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mihai Ostafe — TLADe ATAS Bridge contribution
# Copyright (c) 2026 TLADe — Trade Like a Dealer (https://tradelikeadealer.com)
"""
TLADe Auto Fetch  v1.0.0

End-to-end automation: read GEX levels straight from the TLADe Terminal
via browser automation (Playwright) and forward them to the ATAS bridge
without any manual interaction.

Install (one-time):
  pip install playwright requests
  playwright install chromium

First run (login):
  python tlade_auto_fetch.py
  -> A browser window opens — log into the TLADe Terminal
  -> The session is saved automatically under ~/.tlade_playwright/
  -> Levels are pushed as soon as they load

Subsequent runs (fully automatic):
  python tlade_auto_fetch.py
  -> Browser launched in the background (headless)
  -> Auto-refresh every REFRESH_MIN minutes
  -> Ctrl+C to stop

How it works:
  1. Playwright opens the TLADe Terminal in a Chromium headless browser
  2. Intercepts ALL API responses from tradelikeadealer.com
  3. Auto-detects the response that carries GEX data
  4. Parses the TLADe format (S:|L:|P: or native JSON)
  5. POSTs the levels to the ATAS bridge on /push_levels
  6. Repeats every REFRESH_MIN minutes
"""

import asyncio
import json
import re
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────────

BRIDGE_URL    = "http://localhost:5000"
TLADE_URL     = "https://tradelikeadealer.com/terminal/"
PROFILE_DIR   = str(Path.home() / ".tlade_playwright")
REFRESH_MIN   = 5      # how often to reload TLADe (minutes)
TICKER        = "ES"   # ES or NQ
HEADLESS      = None   # None = auto (headless after first successful login)

# Marker file: presence means the user is already logged in
_LOGGED_IN_FLAG = Path(PROFILE_DIR) / ".logged_in"

# ── Pattern matching for GEX data ──────────────────────────────────────────────

# Markers for the Pine-Script-style TLADe format (S:|L:|P:)
PINE_MARKERS   = ["|L:", ",ZG,", ",MP,", ",CW,", ",PW,", ",EH,", ",EL,"]

# Markers for a possible native TLADe JSON
JSON_MARKERS   = ["call_wall", "put_wall", "zero_gamma", "max_pain",
                  "em_high", "em_low", "vol_band", "gex_level", "gamma_flip"]


def _score_pine(text: str) -> int:
    """Confidence score that the text is the Pine-Script TLADe format."""
    return sum(1 for m in PINE_MARKERS if m in text)


def _score_json(text: str) -> int:
    """Confidence score that the text is a GEX-bearing JSON."""
    return sum(1 for m in JSON_MARKERS if m in text.lower())


def _is_tlade_data(text: str) -> bool:
    """Return True iff the string looks like TLADe GEX data."""
    return _score_pine(text) >= 2 or _score_json(text) >= 2


# ── Parse the Pine-Script format (known from the TV indicator) ─────────────────

TYPE_MAP = {
    "ZG": "zero_gamma", "MP": "max_pain",
    "EH": "em_high",    "EL": "em_low",
    "VH": "vol_band_up","VL": "vol_band_down",
    "CW": "call_wall",  "PW": "put_wall",
    "PDH":"structure_pdh","PDL":"structure_pdl",
    "PWH":"structure_pwh","PWL":"structure_pwl",
}


def _parse_pine(raw: str) -> list[dict]:
    """Parse the S:|L:|P: Pine-Script / TLADe format."""
    raw = raw.strip().replace("\n","").replace("\r","")
    # Strip S: spread prefix
    if raw.startswith("S:"):
        pipe = raw.find("|")
        if pipe > 2:
            raw = raw[pipe + 1:]
    # Extract the L: section
    levels_raw = ""
    if "|P:" in raw:
        pipe = raw.find("|P:")
        levels_raw = raw[:pipe]
    else:
        levels_raw = raw
    if levels_raw.startswith("L:"):
        levels_raw = levels_raw[2:]

    levels = []
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
        label = parts[2].strip() if len(parts) >= 3 else code
        mag   = 0.0
        if len(parts) >= 5:
            try: mag = float(parts[4])
            except: pass
        mapped = TYPE_MAP.get(code, "other")
        levels.append({
            "price":     price,
            "type":      mapped,
            "label":     f"{price:.2f} {code} {label}",
            "magnitude": round(mag, 2),
        })
    return levels


def _parse_json_native(data: dict) -> list[dict]:
    """
    Try to extract levels from a native TLADe JSON
    (exact shape discovered at first run).
    """
    levels = []
    text = json.dumps(data).lower()

    # Try common shapes: {"levels": [...], "call_wall": X, ...}
    for key in ("levels", "gex_levels", "strikes", "data"):
        if key in data and isinstance(data[key], list):
            for item in data[key]:
                if not isinstance(item, dict):
                    continue
                price = (item.get("price") or item.get("strike") or
                         item.get("level") or item.get("value"))
                typ   = (item.get("type") or item.get("kind") or
                         item.get("label") or "unknown")
                label = item.get("label") or item.get("name") or str(price)
                if price:
                    levels.append({
                        "price": float(price),
                        "type":  str(typ).lower().replace(" ","_"),
                        "label": str(label),
                    })

    # Try scalar fields: {"call_wall": 5300, "put_wall": 5200, ...}
    scalar_map = {
        "call_wall":    "call_wall",
        "put_wall":     "put_wall",
        "zero_gamma":   "zero_gamma",
        "gamma_flip":   "zero_gamma",
        "max_pain":     "max_pain",
        "max_pain_strike": "max_pain",
        "em_high":      "em_high",
        "em_low":       "em_low",
    }
    for api_key, our_type in scalar_map.items():
        val = data.get(api_key) or (data.get("levels") or {}).get(api_key)
        if val and isinstance(val, (int, float)):
            levels.append({
                "price": float(val),
                "type":  our_type,
                "label": f"{val:.2f} {our_type.replace('_',' ').title()}",
            })

    return levels


# ── Push to bridge ─────────────────────────────────────────────────────────────

def _push(levels: list[dict], ticker: str) -> bool:
    if not levels:
        return False
    try:
        r = requests.post(
            f"{BRIDGE_URL}/push_levels",
            json={"ticker": ticker, "levels": levels},
            timeout=5,
        )
        d = r.json()
        if d.get("ok"):
            ts = datetime.now().strftime("%H:%M:%S")
            by_type = {}
            for lv in levels:
                by_type[lv["type"]] = by_type.get(lv["type"], 0) + 1
            summary = ", ".join(f"{v}x {k}" for k, v in sorted(by_type.items()))
            print(f"[{ts}] PUSH OK  {ticker}  {len(levels)} levels  [{summary}]")
            return True
        print(f"[ERROR] Bridge: {d}")
        return False
    except requests.ConnectionError:
        print(f"[ERROR] Bridge not responding at {BRIDGE_URL}.")
        print("        Start it with: python tlade_bridge_atas.py")
        return False
    except Exception as exc:
        print(f"[ERROR] Push: {exc}")
        return False


# ── Extract levels from captured responses ─────────────────────────────────────

class Capture:
    def __init__(self):
        self.items: list[dict] = []   # {"url":..., "body":..., "json":...}

    def add(self, url: str, body: str, data=None):
        self.items.append({"url": url, "body": body, "data": data})

    def best(self) -> Optional[dict]:
        """Return the most likely GEX-data candidate."""
        scored = []
        for item in self.items:
            body = item["body"] or ""
            ps   = _score_pine(body)
            js   = _score_json(body)
            scored.append((ps * 10 + js, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else None


def _extract_levels(capture: Capture) -> list[dict]:
    """Extract levels from the captured data."""
    item = capture.best()
    if not item:
        return []

    body = item.get("body", "")
    data = item.get("data")

    # Try Pine Script format
    if _score_pine(body) >= 2:
        levels = _parse_pine(body)
        if levels:
            print(f"  Format: TLADe Pine Script  (URL: {item['url'][:70]})")
            return levels

    # Try native JSON
    if data and isinstance(data, dict):
        levels = _parse_json_native(data)
        if levels:
            print(f"  Format: native JSON  (URL: {item['url'][:70]})")
            return levels

    # Try JSON embedded in body
    if data and isinstance(data, str):
        try:
            parsed = json.loads(data)
            levels = _parse_json_native(parsed)
            if levels:
                print(f"  Format: JSON string  (URL: {item['url'][:70]})")
                return levels
        except:
            pass

    # Try a regex to find typed prices in any text
    # e.g. "price":7300,"type":"call_wall"
    price_re = re.findall(r'"price"\s*:\s*(\d+(?:\.\d+)?)', body)
    type_re  = re.findall(r'"type"\s*:\s*"([^"]+)"', body)
    if price_re and type_re and len(price_re) == len(type_re):
        levels = []
        for price_s, typ in zip(price_re, type_re):
            price = float(price_s)
            mapped = TYPE_MAP.get(typ.upper(), typ.lower().replace(" ","_"))
            levels.append({
                "price": price,
                "type":  mapped,
                "label": f"{price:.2f} {typ}",
            })
        if levels:
            print(f"  Format: JSON regex  (URL: {item['url'][:70]})")
            return levels

    print(f"  [WARN] Unknown format at URL: {item['url'][:70]}")
    print(f"  [WARN] Body preview: {body[:300]}")
    return []


# ── Playwright core ────────────────────────────────────────────────────────────

async def _fetch_once(pw, headless: bool, debug: bool = False) -> list[dict]:
    """
    Open the TLADe terminal, intercept API responses,
    return the parsed list of GEX levels.
    """
    capture  = Capture()
    all_reqs = []   # for --debug: all tradelikeadealer.com requests

    print(f"[{datetime.now():%H:%M:%S}] Launching browser (headless={headless})...")

    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=headless,
        viewport={"width": 1400, "height": 900},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        ignore_https_errors=True,
    )

    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # ── Response interception ─────────────────────────────────────────────────
    async def on_response(response):
        url = response.url
        if "tradelikeadealer.com" not in url:
            return
        if any(ext in url for ext in [".js", ".css", ".png", ".svg", ".ico", ".woff", ".ttf"]):
            return
        try:
            ct     = response.headers.get("content-type", "")
            status = response.status
            body   = await response.text()
            if not body:
                return

            data = None
            if "json" in ct:
                try:
                    data = await response.json()
                except:
                    data = body

            if debug:
                print(f"  [NET {status}] {url[:90]}")
                print(f"         ct={ct[:40]}  len={len(body)}")
                print(f"         body: {body[:200]}")
                print()

            all_reqs.append({"url": url, "body": body, "data": data, "status": status})

            if _is_tlade_data(body):
                capture.add(url, body, data)
                print(f"  -> GEX captured: {url[:80]}")

        except Exception as exc:
            if debug:
                print(f"  [NET ERR] {url[:80]}: {exc}")

    # ── WebSocket message interception ────────────────────────────────────────
    async def on_websocket(ws):
        if debug:
            print(f"  [WS] {ws.url[:80]}")

        async def on_frame(payload):
            try:
                msg = payload if isinstance(payload, str) else payload.decode("utf-8", errors="replace")
                if debug and len(msg) > 5:
                    print(f"  [WS frame] {ws.url[:50]}  len={len(msg)}  {msg[:150]}")
                if _is_tlade_data(msg):
                    capture.add(ws.url, msg, None)
                    print(f"  -> WS GEX captured: {ws.url[:60]}")
            except:
                pass

        ws.on("framesent",     lambda f: asyncio.create_task(on_frame(
            f.payload if hasattr(f, "payload") else str(f))))
        ws.on("framereceived", lambda f: asyncio.create_task(on_frame(
            f.payload if hasattr(f, "payload") else str(f))))

    page.on("response",  on_response)
    page.on("websocket", on_websocket)

    # ── Navigation ───────────────────────────────────────────────────────────
    try:
        await page.goto(TLADE_URL, wait_until="domcontentloaded", timeout=30_000)
    except Exception as e:
        print(f"[WARN] Goto timeout: {e}")

    # Login check
    current_url = page.url
    needs_login = (
        "login"   in current_url.lower() or
        "sign-in" in current_url.lower() or
        "auth"    in current_url.lower()
    )

    if debug:
        print(f"  [URL] {current_url}")
        print(f"  [LOGIN NEEDED] {needs_login}")

    if needs_login and not headless:
        print()
        print("=" * 55)
        print("  Log into the TLADe Terminal in the open browser.")
        print("  After login, press Enter here to continue.")
        print("=" * 55)
        input()
        await page.wait_for_load_state("networkidle", timeout=30_000)
    elif needs_login and headless:
        print("[ERROR] Not logged in and the browser is headless.")
        print("        Run once without --headless to log in:")
        print("        python tlade_auto_fetch.py --login")
        await ctx.close()
        return []

    # Wait for the page to issue its TLADe API requests
    print("  Waiting for TLADe API requests...")
    await asyncio.sleep(8)

    # Also try the JavaScript app state (React/Next stores on window)
    try:
        js_state = await page.evaluate("""
            () => {
                const tries = [
                    window.__NUXT__      && JSON.stringify(window.__NUXT__),
                    window.__NEXT_DATA__ && JSON.stringify(window.__NEXT_DATA__),
                    window.__STORE__     && JSON.stringify(window.__STORE__),
                    window.gexData       && JSON.stringify(window.gexData),
                    window.tladeLevels   && JSON.stringify(window.tladeLevels),
                ];
                return tries.find(x => x && x.length > 50) || null;
            }
        """)
        if js_state:
            if debug:
                print(f"  [JS STATE] len={len(js_state)}  {js_state[:300]}")
            if _is_tlade_data(js_state):
                print("  -> JS window state captured")
                capture.add("window.__state__", js_state, None)
    except Exception as exc:
        if debug:
            print(f"  [JS STATE ERR] {exc}")

    # As a last resort, scrape visible GEX labels from the DOM
    try:
        dom_levels = await page.evaluate("""
            () => {
                const results = [];
                const allEls = document.querySelectorAll('*');
                const pricePattern = /^(\\d{3,6}(?:\\.\\d{1,4})?)\\s+(ZG|MP|CW|PW|PDH|PDL|EH|EL|VH|VL|Call Wall|Put Wall|Zero Gamma|Max Pain|EM High|EM Low)/i;
                for (const el of allEls) {
                    const txt = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                        ? el.textContent.trim()
                        : '';
                    if (txt && pricePattern.test(txt)) {
                        results.push(txt);
                    }
                }
                return [...new Set(results)].slice(0, 100);
            }
        """)
        if dom_levels and len(dom_levels) > 0:
            print(f"  -> DOM: {len(dom_levels)} GEX labels found")
            if debug:
                for lbl in dom_levels:
                    print(f"     {lbl}")
            dom_parsed = _parse_dom_labels(dom_levels)
            if dom_parsed:
                await ctx.close()
                _LOGGED_IN_FLAG.touch()
                return dom_parsed
    except Exception as e:
        if debug:
            print(f"  [DOM ERR] {e}")

    # Debug mode: if nothing was captured, dump all the requests
    if debug and not capture.items:
        print()
        print(f"  [DEBUG] Total tradelikeadealer.com requests: {len(all_reqs)}")
        for req in all_reqs:
            print(f"    {req['status']} {req['url'][:90]}")

    levels = _extract_levels(capture)

    if levels:
        _LOGGED_IN_FLAG.touch()

    await ctx.close()
    return levels


def _parse_dom_labels(labels: list[str]) -> list[dict]:
    """Parse text labels scraped from the DOM such as '7300 CW Call Wall'."""
    levels = []
    pattern = re.compile(
        r"^(\d{3,6}(?:\.\d{1,4})?)\s+"
        r"(ZG|MP|CW|PW|PDH|PDL|EH|EL|VH|VL|Call Wall|Put Wall|Zero Gamma|Max Pain|EM High|EM Low|Vol High|Vol Low)",
        re.IGNORECASE
    )
    code_map = {
        "call wall": "CW", "put wall": "PW", "zero gamma": "ZG",
        "max pain": "MP", "em high": "EH", "em low": "EL",
        "vol high": "VH", "vol low": "VL",
    }
    for lbl in labels:
        m = pattern.match(lbl)
        if not m:
            continue
        price = float(m.group(1))
        raw_code = m.group(2).upper()
        code = code_map.get(raw_code.lower(), raw_code)
        mapped = TYPE_MAP.get(code, "other")
        levels.append({
            "price": price,
            "type":  mapped,
            "label": lbl.strip(),
        })
    return levels


# ── Main loop ──────────────────────────────────────────────────────────────────

async def run_loop(headless: bool, ticker: str, refresh_min: int, debug: bool = False):
    from playwright.async_api import async_playwright

    print("=" * 60)
    print(f"  TLADe Auto Fetch  (ticker={ticker}, refresh={refresh_min}min)")
    print("=" * 60)
    print()

    async with async_playwright() as pw:
        while True:
            try:
                levels = await _fetch_once(pw, headless, debug=debug)
            except Exception as exc:
                print(f"[ERROR] fetch: {exc}")
                levels = []

            if levels:
                _push(levels, ticker)
            else:
                print(f"[WARN] No levels extracted. Retrying in {refresh_min} min.")

            print(f"  Next refresh in {refresh_min} minutes... (Ctrl+C to stop)")
            print()
            await asyncio.sleep(refresh_min * 60)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    global BRIDGE_URL

    p = argparse.ArgumentParser(
        description="TLADe Auto Fetch — scrape GEX from the TLADe browser session and forward to the ATAS bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tlade_auto_fetch.py              # auto (headless after first login)
  python tlade_auto_fetch.py --login      # force visible browser (re-login)
  python tlade_auto_fetch.py --ticker NQ
  python tlade_auto_fetch.py --refresh 10
        """,
    )
    p.add_argument("--ticker",  default=TICKER,        choices=["ES","NQ"])
    p.add_argument("--refresh", default=REFRESH_MIN,   type=int, metavar="MIN",
                   help=f"Refresh interval in minutes (default: {REFRESH_MIN})")
    p.add_argument("--login",   action="store_true",
                   help="Open a visible browser for (re)login")
    p.add_argument("--once",    action="store_true",
                   help="Run once and exit")
    p.add_argument("--debug",   action="store_true",
                   help="Print every captured HTTP/WS request")
    p.add_argument("--url",     default=BRIDGE_URL,
                   help=f"ATAS bridge URL (default: {BRIDGE_URL})")
    args = p.parse_args()

    BRIDGE_URL = args.url

    # Decide whether to run headless
    already_logged = _LOGGED_IN_FLAG.exists()
    headless = not args.login and already_logged

    if args.login:
        print("Login mode: visible browser.")
    elif not already_logged:
        print("First run: visible browser for login.")
        headless = False
    else:
        print("Saved session: headless browser (background).")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print()
        print("[ERROR] Playwright is not installed. Run:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    async def _once():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            levels = await _fetch_once(pw, headless, debug=args.debug)
            if levels:
                _push(levels, args.ticker)
            else:
                print("[WARN] No levels found.")

    if args.once:
        asyncio.run(_once())
    else:
        asyncio.run(run_loop(headless, args.ticker, args.refresh, debug=args.debug))


if __name__ == "__main__":
    main()
