# TLADe Bridges — Third-Party Indicators and Add-ons

**Bring your own data feed and your own charting platform to
[TLADe](https://tradelikeadealer.com)** — the GEX analytics terminal
for futures and options traders.

This repo holds the integrations that run **outside** the TLADe
terminal — on TradingView, NinjaTrader 8, ATAS, MotiveWave and
broker/feed APIs. For indicators that run **inside** the TLADe
terminal itself (drawn natively on its LWChart canvas), see
[`../native/`](native/).

## How It Works

```
Your Broker/Platform  ──>  Bridge (runs locally)  ──>  TLADe Terminal
   (TWS, NT8, etc.)        (Python/C#/any lang)        (auto-detects on localhost)
```

1. You run a bridge on your machine — a small local server that reads from your data feed
2. The TLADe terminal automatically detects it on `localhost:5000`
3. You get real-time data with zero latency and tick-accurate volume

**No data leaves your machine.** The bridge runs 100% locally.

## Available Integrations

The integrations below come in two flavours, kept side by side for
transparency: those **built by the TLADe team** (canonical
reference implementations) and those **contributed by the community
and patched by TLADe** (original source preserved, our patches
documented in each subfolder's `CHANGELOG`).

### TLADe-built

Canonical integrations developed and maintained directly by the
TLADe team.

| Integration | Status | Feed / Surface | Language |
|---|---|---|---|
| [TradingView Pine](bridges/) (in repo terminal/TV-Indicators/) | **Ready** | Pine v6 indicators for ES/SPX/SPY and NQ/NDX/QQQ — published on TradingView | Pine |
| [Interactive Brokers](bridges/ib/) | **Ready** | TWS / IB Gateway | Python |
| [Rithmic](bridges/rithmic/) | **Ready** | R\|Protocol direct (Apex, TopstepTrader, Bulenox, Earn2Trade + 12 other prop firms) | Python |
| [NinjaTrader 8 bridge](bridges/ninjatrader/) | **Beta** | Rithmic, CQG, Kinetick (via NT8) | C# + Python |

### Community-contributed (TLADe-patched)

Built originally by a community contributor; reviewed line-by-line,
patched by the TLADe team where needed, and published with the
original source preserved next to ours. Each integration's
`original/` folder holds the contributor's untouched code with full
credit; the root-level source is the TLADe-patched build. See
`CHANGELOG.md` in each subfolder for the patch list.

| Integration | Status | Surface | Contributor |
|---|---|---|---|
| [ATAS](bridges/atas/) | **Ready** | ATAS Platform — Bridge + GEX Dashboard + Quantum Field Ladder (Rithmic / CQG via ATAS data) | Mihai (C# + Python) |
| [MotiveWave](bridges/motivawe/) | **Ready (Java 26+)** | TLADe levels overlay on MotiveWave charts. Universal Java 17 build in progress. | Herat Acharya (Java) |
| [CQG](bridges/cqg/) | Wanted | CQG API direct | — |

## Build Your Own Bridge

Any program that implements the [Bridge Protocol](protocol/BRIDGE_SPEC.md) is compatible with TLADe. The protocol is 4 HTTP endpoints — you can write a bridge in any language.

See [`templates/bridge_template.py`](templates/bridge_template.py) for a minimal skeleton.

## Contributing

We welcome community bridges! If you have access to a data feed that isn't covered:

1. Read the [Bridge Protocol Spec](protocol/BRIDGE_SPEC.md)
2. Use the [template](templates/bridge_template.py) as a starting point
3. Test with your TLADe terminal (it auto-detects `localhost:5000/health`)
4. Open a PR

## Requirements

- A TLADe subscription ([tradelikeadealer.com](https://tradelikeadealer.com))
- A local data feed (your broker account + platform)
- Python 3.8+ (for Python bridges) or .NET (for NT8 bridges)

## License

MIT — use, modify, and distribute freely.
