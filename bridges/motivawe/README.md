# TLADe GEX Dashboard — MotiveWave Indicator

**Status: Java 26+ (compatible build coming for older MotiveWave installs)**

Overlay TLADe GEX levels directly on your MotiveWave chart. Same data
contract as the TradingView indicator (`S:|L:|P:` string) — same six
session windows, same level taxonomy (Call/Put Walls, Zero Gamma, Max
Pain, EM High/Low, Vol Bands, PA structure).

## Community Contribution

This MotiveWave indicator is a community contribution by
**Herat Acharya**, ported from the [`TLADeGexDashboardNT`](../ninjatrader/)
(NinjaTrader 8) reference. Many thanks for the work.

This repo ships two versions:

- **`original/TLADeGexDashboard.java`** — Herat's untouched source, full
  credit. The starting point.
- **`TLADeGexDashboard.java`** — same logic, with four small robustness
  patches applied by the TLADe team (see [CHANGELOG](CHANGELOG.md)).

Both versions implement the same MotiveWave Study contract and produce
identical visuals; the patched version just makes the draw thread
swap-safe and removes a re-entrancy edge in `calculateValues`.

## Requirements

- MotiveWave with Java **26** runtime (the bundled `mwave_sdk.jar` must
  match — `class file version 70`)
- A TLADe subscription with a valid API key for live data; without a
  key the indicator falls back to the free/delayed cloud endpoint
- ~5 MB free in `MotiveWave Extensions/` for the compiled `.jar`

⚠️ **Older MotiveWave (Java 17 / 21):** the prebuilt `.jar` here will
NOT load — its bytecode is Java 26. A backward-compatible build is in
the works (target Java 17, single universal jar). For now, either:

- update MotiveWave to the latest release (Java 26+), or
- recompile from source against your local `mwave_sdk.jar` (see below)

## Install (prebuilt jar)

A prebuilt `TLADeGexDashboard.jar` is attached to the latest release on
GitHub (Java 26 only for now):

1. Close MotiveWave completely.
2. Download `TLADeGexDashboard.jar` from the release page.
3. Drop it into `~/MotiveWave Extensions/` (macOS) or
   `%USERPROFILE%\MotiveWave Extensions\` (Windows).
4. Reopen MotiveWave → open a chart (ES or NQ futures) →
   **Study → My Studies → "TLADe GEX"**.
5. Optionally enter your API key under the indicator's **Data → API
   Key** field for live data; leave blank for delayed/free.

## Build from source

Requires **JDK matching your MotiveWave's Java version** (run
`cat "<MotiveWave>/jre/release"` to check `JAVA_VERSION`). For
MotiveWave Java 26:

```powershell
# (Windows) JDK 26 portable, no install needed
$base = "$env:LOCALAPPDATA\tlade-build"
New-Item -ItemType Directory -Force -Path $base | Out-Null
Invoke-WebRequest "https://api.adoptium.net/v3/binary/latest/26/ea/windows/x64/jdk/hotspot/normal/eclipse?project=jdk" -OutFile "$base\jdk26.zip"
Expand-Archive "$base\jdk26.zip" -DestinationPath $base -Force
$javac = (Get-ChildItem $base -Recurse -Filter javac.exe | Select-Object -First 1).FullName
$jar   = $javac -replace 'javac\.exe$','jar.exe'

# Compile + package
$sdk   = "C:\Program Files (x86)\MotiveWave\lib\mwave_sdk.jar"
$src   = "C:\path\to\tlade-bridges\bridges\motivawe"
$build = "$src\build"
New-Item -ItemType Directory -Force -Path $build | Out-Null
& $javac -classpath $sdk -d $build "$src\TLADeGexDashboard.java"
Push-Location $build; & $jar cf "$build\TLADeGexDashboard.jar" study_examples\*.class; Pop-Location

# Install
Copy-Item "$build\TLADeGexDashboard.jar" "$env:USERPROFILE\MotiveWave Extensions" -Force
```

```bash
# (macOS / Linux) using a system or sdkman-managed JDK matching MW's version
javac -classpath /Applications/MotiveWave/lib/mwave_sdk.jar -d build TLADeGexDashboard.java
cd build && jar cf TLADeGexDashboard.jar study_examples/*.class
cp TLADeGexDashboard.jar ~/MotiveWave\ Extensions/
```

## How it works

The indicator runs entirely client-side:

1. On chart open it polls our public endpoint `indicatorData?ticker=…`
   on the six TLADe publish slots (Asia 18:01 ET / Europe 02:00 / Pre
   08:00 / RTH 09:30 / Opening Range 10:30 / Close 16:00).
2. The response is the same `S:|L:|P:` string used by the TradingView
   Pine — spread + level list + per-strike GEX profile.
3. The Study draws horizontal lines per level (color-coded by type),
   chip labels on the right edge, and an optional GEX histogram in the
   right margin.
4. A small diagnostic box top-left shows the auto-fetch state and the
   last fetch time.

No data leaves your machine besides the public `indicatorData` call.

## Questions?

📧 support@tradelikeadealer.com
