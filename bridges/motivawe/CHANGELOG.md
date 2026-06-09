# CHANGELOG — MotiveWave Indicator

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
