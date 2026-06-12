# CHANGELOG — MotiveWave Indicator

## 2026-06-12 — Tick-independent scheduler + Charm Magnet / Breakout + Session AVWAP (v1.3)

Three changes on `TLADeGexDashboard.java`. All pure Java, no native code,
cross-OS preserved (same jar still loads on macOS / Windows / Linux).

### 1. Sync fix — auto-refresh no longer dependent on chart ticks

v1.2 drove the 6 daily auto-fetches by calling `maybeScheduleFetch()`
from inside `calculateValues` and `onBarUpdate`. Both are tick-driven:
on cash-index charts outside RTH and on futures Globex quiet hours the
chart receives zero ticks for the entire pre-market window, so all 3
pre-RTH slots (ASIA 18:05, EU 02:05, PRE 08:05 ET) were silently
skipped. Users worked around it by toggling the study off and on.

v1.3 introduces a real `ScheduledExecutorService` daemon-thread
scheduler started in `onLoad` and chained per-slot. Fires exactly 7
fetches per trading day (1 mount + 6 absolute ET slots), correctly
picks the *next ascending* slot at any time of day. `FETCH_MINUTES_ET`
sorted ascending; the unsorted-array bug that took the first slot
greater than `nowMins` instead of the minimum (= jumping straight to
18:05 ASIA from 04:00 ET, skipping all 4 same-day slots) caught in the
ATAS v3.1 port and fixed here too.

The legacy `maybeScheduleFetch()` is kept as dead code; the new path
no longer relies on `OnCalculate`/`OnBarUpdate` to drive fetches.

### 2. Two new level families parsed from the extended cloud payload

The cloud `indicatorData` endpoint was extended to emit two on-chain-
derived levels the terminal renders:

- **CM** — Charm Magnet (violet line). Strike where charm flow
  magnetises price, surfaced from the volatility cascade. Matches
  the terminal's Market Pulse panel "Magnete Charm".
- **BL / BS** — Breakout Areas (emerald / rose lines). Long / short
  breakout zones detected by the PA engine.

Two new toggles in the Visibility settings group: `Show Breakout
Areas (BL/BS)` and `Show Charm Magnet (CM)`.

### 3. Session AVWAP — local compute, mirrors the Pine indicator

Four anchored-VWAP polylines drawn directly by the indicator from the
chart's own bars — same formula as our TradingView Pine, no extra
round-trip through the cloud. Source = `hlc3 * volume` cumulative,
reset at each session anchor in ET:

- **Asia** (amber) — anchored at 18:00 ET (= futures day start)
- **EU** (blue) — anchored at 02:00 ET
- **US** (green) — anchored at 09:30 ET RTH open
- **Prev Day US** (dim green) — yesterday's US AVWAP, promoted at the
  futures-day rollover and held for the rest of the day

New settings group **"Session AVWAP"**: individual on/off per polyline,
line width (1–4), label visibility, "Show Historical AVWAP (prev days)"
switch (off by default = only the current futures day is drawn, keeps
the chart clean).

Same approach as the ATAS v3.1.1 port: cross-OS Java only, uses
`DataSeries.getStartTime(i)` + `DrawContext.translateTime(long)` /
`translateValue(double)` from the SDK — no platform-specific code.

## 2026-06-09 — Cross-OS build (v1.2)

Rebuilt against the MotiveWave macOS SDK (`mwave_sdk.jar` class file
version 69, Java 25) so the single `dist/TLADeGexDashboard.jar` now
loads on macOS, Windows and Linux — anywhere MotiveWave ships its
Java 25-or-newer runtime. Source unchanged from v1.1.

**Why:** the previous build was compiled against the Windows SDK
(class file v70 / Java 26). MotiveWave on macOS still bundles a Java
25 runtime, so the Java 26 bytecode was silently skipped at extension
load time — no warning, no entry under Studies. macOS users were
effectively locked out.

**How:** the macOS `mwave_sdk.jar` exposes the same `Study` /
`DataContext` / `Defaults` / `Figure` / descriptor surface as the
Windows one; only the target bytecode version differs. Compiling
against the macOS SDK with `javac --release 25` produces a single
universal jar — backward-compatible with the Java 26 Windows JVM
(JVMs read older class file versions without issue), forward-
compatible with whatever Java 25 macOS ships.

**Footprint:** identical (18.7 KB jar, same five inner classes).

## 2026-06-09 — TLADe patches (v1.1)

Four small robustness fixes on top of Herat's original `v1.0`. Logic
verified line-by-line against the `TLADeGexDashboardNT.cs` (NinjaTrader
8 reference) — parsing, `convertPrice`, level selection + counting,
threshold gating, protected-strike retention, profile rendering, theme
palette, auto-fetch lifecycle: all unchanged. Only the four points
below were modified.

### 1. 🟠 Race calc/draw — draw lists made swap-safe

**Problem:** `drawLevels` and `drawProfile` were final fields that
`buildDrawModel` mutated in place between fetch completion and the
next `drawCanvas` invocation. The draw thread could observe a list
half-populated under live bars, producing flicker / partial paints
and (rarely) a `ConcurrentModificationException`.

**Fix:** the two fields are now `volatile`, and `buildDrawModel`
constructs the new lists on local references and **publishes them via
a single atomic assignment**. The draw thread either sees the previous
complete list or the new complete list — never an intermediate state.

### 2. 🟠 Settings mutation inside `calculateValues`

**Problem:** the fetched data string and the spread parsed from the
`S:` prefix were being written into the indicator's settings object
during `calculateValues`. That could re-trigger MotiveWave's
`onSettingsUpdated` → `recalculate` cycle, creating a re-entrancy
edge during live bar updates.

**Fix:** introduced two new private fields, `lastData` and
`spreadOverride`, that hold the fetched string + parsed spread without
touching settings. `convertPrice` now reads the effective spread from
`spreadOverride` (or the manual setting if no override). The settings
object is now write-only from the user's UI.

**Behavioural note:** the fetched data string no longer appears in the
"GEX Data" settings textbox (it used to). Functionally identical —
the diagnostic top-left box still shows the right `dataChars` count.
The `S:` prefix is also now a sticky override: as long as new data
arrives with `S:`, the manual "ES-SPX Spread" field in the UI is
ignored. The TLADe export always includes `S:`, so this is the
expected steady-state.

### 3. 🟡 ZG / structure-level colour aligned to NT8 reference

**Problem:** Zero Gamma and structure-level lines were drawn at
`#696969` (DimGray). The NT8 reference uses WPF's `Brushes.DarkGray`
(`#A9A9A9`), one shade lighter. Cross-platform consistency.

**Fix:** colour constant changed to `#A9A9A9`. Pixel-match with NT8.

### 4. 🧹 Deprecation cleanup — `new URL(String)` → `URI.create(...).toURL()`

**Problem:** `new URL(String)` is deprecated since JDK 20. Compiling
on JDK 26 surfaces the warning.

**Fix:** all URL instantiation routed through `URI.create(s).toURL()`.
**Compiles with 0 warnings** on JDK 26.

---

## 2026-06-09 — Original (v1.0) by Herat Acharya

Initial port of `TLADeGexDashboardNT` (NinjaTrader 8) to MotiveWave.

- Same `S:|L:|P:` data contract as the TradingView Pine indicator
- Same six TLADe publish-time auto-fetch slots
- Full level taxonomy: CW / PW / ZG / MP / EH / EL / VH / VL / PDH /
  PDL / PWH / PWL
- API key / free-delayed dual mode
- Profile histogram + chip labels + diagnostic status box

Credit: **Herat Acharya** — community contribution, June 2026.
