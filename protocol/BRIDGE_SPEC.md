# TLADe Bridge Protocol Specification

**Version:** 1.1.0
**Last updated:** 2026-03-30

## Overview

A TLADe bridge is a local HTTP server running on `localhost:5000` that exposes market data to the TLADe terminal. The terminal auto-detects the bridge by polling `/health` every 15 seconds.

Any program that implements these endpoints is a valid TLADe bridge — language, platform, and data source don't matter.

## Endpoints

### `GET /health`

Health check — the terminal uses this to detect the bridge.

**Response (200 OK):**
```json
{
  "status": "ok",
  "tlade_bridge": true,
  "ib_connected": true,
  "provider": "ib",
  "lite_mode": true,
  "version": "1.1.0"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"ok"` |
| `tlade_bridge` | boolean | Always `true` — identifies this as a TLADe bridge |
| `ib_connected` | boolean | `true` if the data feed is connected and streaming |
| `provider` | string | Bridge identifier (e.g. `"ib"`, `"ninjatrader"`, `"rithmic"`) |
| `lite_mode` | boolean | `true` for standalone bridges (no gex_data_server) |
| `version` | string | Bridge version |

### `GET /ib_data?ticker={symbol}`

Real-time 5-minute candles (streaming, kept up to date).

**Query params:**
- `ticker` — `ES` or `NQ` (default: `ES`)

**Response (200 OK):**
```json
{
  "chart_data": {
    "time":   [1711756800, 1711757100, ...],
    "open":   [5650.25, 5651.00, ...],
    "high":   [5652.50, 5653.75, ...],
    "low":    [5649.00, 5650.25, ...],
    "close":  [5651.75, 5652.00, ...],
    "volume": [12450, 8320, ...]
  },
  "live_price": 5652.00,
  "instrument": "ES"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `chart_data.time` | number[] | Unix timestamps in **seconds** |
| `chart_data.open/high/low/close` | number[] | OHLC prices |
| `chart_data.volume` | number[] | Real tick volume per bar |
| `live_price` | number | Latest trade price (market data) |
| `instrument` | string | Resolved symbol (`"ES"` or `"NQ"`) |

**Duration:** At least 2 weeks of 5-minute bars (recommended). The terminal uses these for chart display, AVWAP calculation, and session analysis.

**Error (404):**
```json
{ "error": "No data for ES" }
```

### `GET /ib_daily?ticker={symbol}`

Daily (D1) bars for PA level calculation — PDH/PDL, PWH/PWL, breakout detection.

**Query params:**
- `ticker` — `ES` or `NQ` (default: `ES`)

**Response (200 OK):**
```json
{
  "data": [
    { "t": 1711670400, "o": 5620.00, "h": 5665.50, "l": 5615.25, "c": 5652.00, "v": 1250000 },
    ...
  ],
  "instrument": "ES",
  "cached": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data[].t` | number | Unix timestamp in **seconds** (day open) |
| `data[].o/h/l/c` | number | OHLC prices |
| `data[].v` | number | Daily volume |
| `instrument` | string | Resolved symbol |
| `cached` | boolean | `true` if served from cache |

**Duration:** 1 year of daily bars (RTH only).

**Error (503):** Data feed not connected.

### `GET /ib_history?ticker={symbol}`

2 weeks of 5-minute bars with real tick volume — used for Volume Profile and AVWAP calculation.

**Query params:**
- `ticker` — `ES` or `NQ` (default: `ES`)

**Response (200 OK):**
```json
{
  "data": [
    { "t": 1711756800, "o": 5650.25, "h": 5652.50, "l": 5649.00, "c": 5651.75, "v": 12450 },
    ...
  ],
  "instrument": "ES",
  "cached": true
}
```

Same format as `/ib_daily`. Duration: 2 weeks of 5-minute bars, all sessions (not RTH-only).

**Error (503):** Data feed not connected.

## Implementation Notes

### Port
The bridge MUST listen on `localhost:5000`. This is hardcoded in the terminal detector.

### CORS
The bridge MUST allow CORS from any origin:
```
Access-Control-Allow-Origin: *
```

### Timestamps
All timestamps are **Unix seconds** (not milliseconds). The terminal converts to ms internally.

### Caching
`/ib_daily` and `/ib_history` are expensive requests. Bridges should cache these server-side (one fetch per day is enough).

### Ticker Mapping
The terminal sends various ticker formats (`ES`, `ES=F`, `SPX`, `NQ`, `NQ=F`, `NDX`). The bridge should normalize:
- Anything with `NQ` → symbol `NQ`
- Everything else → symbol `ES`

### Graceful Degradation
Not all endpoints are required. The minimum viable bridge is:
- `/health` — required
- `/ib_data` — required (real-time candles)
- `/ib_daily` — optional (terminal falls back to Yahoo Finance)
- `/ib_history` — optional (terminal falls back to Yahoo/Firebase)
