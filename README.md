# TLADe Bridges

**Bring your own data feed to [TLADe](https://tradelikeadealer.com)** — the GEX analytics terminal for futures and options traders.

TLADe Bridges let you connect your local data feed (Interactive Brokers, NinjaTrader, CQG, Rithmic...) to the TLADe terminal for real-time candles, spot prices, and historical data with tick-accurate volume.

## How It Works

```
Your Broker/Platform  ──>  Bridge (runs locally)  ──>  TLADe Terminal
   (TWS, NT8, etc.)        (Python/C#/any lang)        (auto-detects on localhost)
```

1. You run a bridge on your machine — a small local server that reads from your data feed
2. The TLADe terminal automatically detects it on `localhost:5000`
3. You get real-time data with zero latency and tick-accurate volume

**No data leaves your machine.** The bridge runs 100% locally.

## Available Bridges

| Bridge | Status | Feed | Language |
|--------|--------|------|----------|
| [Interactive Brokers](bridges/ib/) | **Ready** | TWS / IB Gateway | Python |
| [NinjaTrader 8](bridges/ninjatrader/) | **Beta** | Rithmic, CQG, Kinetick (via NT8) | C# + Python |
| [Rithmic](bridges/rithmic/) | Wanted | R\|Protocol direct | — |
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
