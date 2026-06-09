# TLADe Native Indicators and Add-ons

Indicators that run **inside the TLADe terminal itself** — drawn on the
native LWChart (built on TradingView Lightweight Charts) layer of the
React frontend, alongside the GEX, AVWAP, Session and Volume Profile
overlays you already see by default.

## What "native" means here

Native indicators are part of the terminal's own React code path. They:

- Have direct access to the live engine state (regime, walls, dealer
  flow, candle stream) without going through the public HTTP API
- Draw on the **same** LWChart instance the rest of the platform uses
  (no plugin sandbox, no separate canvas) → pixel-aligned with our
  existing overlays
- Ship as part of the terminal bundle, not as a downloadable artifact

This is the opposite of [`../bridges/`](../bridges/), which holds
**third-party integrations** — indicators and bridges built for
external platforms (TradingView, NinjaTrader 8, ATAS, MotiveWave…)
that overlay TLADe data on charts running outside our terminal.

## Status (2026-06-09)

The native indicator surface is currently **closed**: every native
indicator in TLADe today (Walls, Magnets, AVWAP, Session Boxes, Worldlines,
Quantum Field overlay, Dealer Flow ribbon, etc.) is developed and
maintained directly by the TLADe team. There is no public plugin API
yet — third-party native add-ons are not accepted.

This folder exists to make the distinction explicit and to host the
developer documentation when we eventually open the native layer to
external contributions. For now it's a placeholder: the indicators
themselves live in the terminal repo, not here.

## Want to build something native?

Two paths in the meantime:

1. **External overlay** — if your idea can run as an overlay on a
   third-party platform (TradingView Pine, NT8 indicator, ATAS, etc.),
   build it as a bridge/indicator under [`../bridges/`](../bridges/).
   The published `S:|L:|P:` data contract is stable and gives you the
   same level taxonomy the terminal renders natively.

2. **Feature request** — open an issue or write to
   support@tradelikeadealer.com with a sharp description of what you'd
   draw, where, and why. If it fits the platform direction we'll
   prioritise it in the next terminal release.

## Looking ahead

When the native add-on API opens, this README will be replaced with
the developer guide (chart primitive APIs, level lifecycle hooks,
publish/render flow, performance constraints). Until then, third-party
integrations under [`../bridges/`](../bridges/) are the only public
surface for community work.

## Questions?

📧 support@tradelikeadealer.com
