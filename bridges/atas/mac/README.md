# TLADe ATAS Bridge — Mac extension

This is a community-maintained Mac port of the TLADe ATAS Bridge. It is a **derivative** of the official Windows build in [`../`](../) — same wire protocol, different platform target, separate DLL artifact, and its own patch history.

The Windows official build is **not modified** by changes in this folder.

## Credits

- **Mihai Ostafe** — original `TLAdeBridgeATAS.cs` (v2.4.0) and the entire indicator stack. All upstream copyrights preserved verbatim in the source header.
- **Krzysztof** — ported the bridge to macOS / .NET 10 cross-platform target (`TLAdeBridgeATAS.Mac.csproj`, `start.command` launcher). Without his work the indicator would not load inside ATAS on Mac.
- **Cornel** — patched the bridge to fix the intermittent `Value is null` crash that surfaced only on the Mac runtime (see Patch notes below). Author of v2.7.0 (C#) and v1.4.0 (Python).

## Disclaimer

The Mac port is supplied **as is** by the TLADe community for fellow Mac users. It is not part of the official TLADe distribution: TLADe does not test it on every release and does not guarantee feature parity with the Windows build. Use it at your own risk. Report issues to the contributors above (or open a thread in the TLADe channel) — TLADe will route bug reports forward but does not own the maintenance burden of this branch.

## Patch notes

### v2.7.0 (C#) + v1.4.0 (Python) — "Value is null" crash fix
Three-layer guard against partial / malformed OHLC bars reaching the terminal. The lightweight-charts library on the terminal side throws `Value is null` on the first sample whose `open / high / low / close` is `null`, `NaN`, `Infinity`, or `0`. Observed intermittently on the Mac build — most likely a freshly streamed bar whose decimal→double conversion landed on a non-finite value, or a partial backfill row before all fields were populated.

**C# (`TLAdeBridgeATAS.cs`, v2.7.0):**
- `IsFinitePositive(v)` + `IsValidBar(cd)` reject any OHLC field that isn't a finite positive number.
- `Js(v, ci)` formatter emits `0` instead of literal `NaN` / `Infinity` tokens — `JSON.parse` on the terminal was silently coercing those to `null`.
- `PostSpot`, `PostBar`, `PostDailyBar` drop malformed rows at the source and log `SKIP BAR (invalid OHLC) …` so the upstream pattern can be inspected.
- `DetectTimeStrategy` simplified to a ±10 min tolerance check called directly in INIT (previous version was a SANITY 2h + closest-match heuristic that ran late on `Unknown`).
- HTTP `/health` ping timeout 2s → 5s (was racing on slow first contact).

**Python (`tlade_bridge_atas.py`, v1.4.0):**
- `/push_spot`, `/push_bar`, `/push_daily` reject malformed inputs with HTTP 400 + `[BAR-DROP]` / `[DAILY-DROP]` log.
- `/ib_data` outbound filter strips invalid bars already sitting in the in-memory cache — protects against stale state from older bridge builds.

After this fix an upstream NaN never reaches `lightweight-charts`; the chart no longer crashes on Mac.

## Build

```
dotnet build TLAdeBridgeATAS.Mac.csproj -c Release
```

Output DLL lives at `bin/Release/TLAdeBridgeATAS.dll`. A pre-built copy of v2.7.0 ships in this directory for users who don't want to install the .NET 10 SDK.

## Install

1. Copy `bin/Release/TLAdeBridgeATAS.dll` into the ATAS indicators folder (Mac path: `~/Library/Application Support/ATAS/Indicators/`).
2. Run `tlade_bridge_atas.py` via `start.command` (double-click in Finder) or manually with `python3 tlade_bridge_atas.py`.
3. Restart ATAS, add the `TLAde Bridge ATAS` indicator to any chart, configure your API key.

The terminal at `https://tradelikeadealer.com/` will auto-detect the bridge on `localhost:5000` once it is running.
