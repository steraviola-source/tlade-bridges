// ============================================================
//  SPDX-License-Identifier: MIT
//  Copyright (c) 2026 Mihai Ostafe — TLADe ATAS Bridge contribution
//  Copyright (c) 2026 TLADe — Trade Like a Dealer (https://tradelikeadealer.com)
//
//  TLADe Bridge — ATAS Edition  v2.7.1 (Mac)
//  C# indicator for ATAS (Advanced Time & Sales)
//
//  Forked from Mihai Ostafe's v2.4.0. Changes since fork:
//    - v2.7.1: port the closest-candidate time-strategy probe from the
//              Windows bridge (`3b89143`). The previous Mac port used the
//              old ±10 min hard tolerance — when GetCandle(bar) returned
//              the last CLOSED bar (open already several minutes behind
//              UtcNow) NONE of the three candidates landed inside the
//              gate, so detection silently fell back to AsLocal. On a
//              Mac in a non-CT timezone this produced 2-7h shifted bar
//              timestamps and the terminal rendered every session box
//              off by that same amount. Closest-wins removes the gate
//              and resolves the strategy unambiguously (candidates are
//              always at least 1h apart).
//
//    - v2.7.0: defensive guard against partial / malformed bars reaching the
//              terminal. The lightweight-charts library on the terminal side
//              throws "Value is null" the moment any OHLC field comes through
//              as null / NaN / Infinity / 0. On the Mac build we saw this
//              intermittently — most likely from a freshly streamed bar whose
//              decimal-to-double conversion landed on a non-finite value, or
//              from a partial backfill row before all fields were populated.
//              v2.7.0 adds `IsValidBar` + a NaN-safe `Js` formatter, drops
//              any bar whose OHLC fails the check both in `PostBar` and
//              `PostDailyBar`, and sanity-checks the spot price too. The
//              Python bridge has matching guards at `/push_bar` and
//              `/ib_data` so a malformed row gets rejected on entry and
//              filtered on exit. The indicator logs every drop so we can
//              spot the upstream pattern.
//
//    - v2.4.4: timezone-robust bar timestamps. The previous PostBar relied
//              on `((DateTimeOffset)cd.Time)` which silently assumes Local
//              when Kind=Unspecified — fine in the Roma local timezone of
//              the developer's machine but wrong elsewhere (Mihai's setup
//              showed a 4h30m shift). v2.4.4 probes the live bar against
//              DateTime.UtcNow at INIT, picks whichever interpretation —
//              AsLocal / AsUtc / AsExchange(CT) — lands within ±10 min of
//              now, and reuses that strategy for the backfill and every
//              subsequent PostBar. No user setting required.
//
//    - v2.4.3: auto re-backfill when the Python bridge has been restarted while
//              the chart instance is still alive. Every 30s we poll /health,
//              parse the per-ticker `bars_count`, and if the bridge is below
//              the threshold (50) we clear the dedup set and re-push the
//              200-bar history. Throttled to at most once every 5 minutes.
//              Pairs with the bridge-side state_atas.json persistence so a
//              normal Python restart usually doesn't need the rebackfill at all.
//    - v2.4.2: BACKFILL of the last 200 closed bars on INIT (= first time we
//              reach the live bar). ATAS already holds these in chart memory;
//              pushing them makes the bridge self-contained — same model as
//              IB (reqHistoricalData) and Rithmic (get_historical_time_bars).
//              When the bridge is up the terminal renders ATAS bars end-to-end;
//              if the bridge drops, the terminal falls back to Yahoo through
//              the standard candleService path, just like for IB / Rithmic.
//              Push is sequential (single Task.Run + foreach) so bars land in
//              chronological order and LightWeight Charts doesn't trip the
//              "data must be asc ordered by time" assert.
//    - v2.4.1: PostBar emits `time` as Unix seconds (integer) instead of ISO
//              string. Matches the Bridge Protocol §chart_data convention used
//              by gex_data_server3.py and the other bridges. Without this,
//              `t * 1000` on the terminal side produces NaN and every bar
//              collapses to a degenerate OHLC=NaN tick.
//    - All Romanian comments and Display strings translated to English.
//    - SPDX MIT header + joint copyright (Mihai Ostafe / TLADe).
//
//  Architecture:
//    Rithmic / CQG feed
//      -> ATAS
//           -> TLAdeBridgeATAS.cs   (indicator, HTTP POST push)
//                -> tlade_bridge_atas.py   (Python receiver, port 5000)
//                     -> TLADe Terminal    (auto-detects localhost:5000)
//
//  Push endpoints (ATAS -> receiver):
//    POST /push_spot    -> live tick
//    POST /push_bar     -> closed bar (OHLCV + delta + bid/ask volume)
//    POST /push_daily   -> daily bar (last bar of the previous trading day)
//
//  Install:
//    1. Build:   dotnet build TLAdeBridgeATAS.csproj -c Release
//                (the DLL is auto-copied to Documents\ATAS\Scripts\)
//    2. ATAS:    Settings -> Extensions -> Reload
//    3. Add the indicator to an ES or NQ chart
//    4. Start the receiver: double-click start.bat (or `python tlade_bridge_atas.py`)
//    5. TLADe Terminal auto-detects the bridge on localhost:5000.
//
//  v2.4.0: Channel<> for bars — single worker thread, no thread-pool explosion
//    - _postedBarTimes: every bar sent exactly once (key = candle.Time.Ticks)
//    - _barSem: at most 3 concurrent POSTs to Flask
//    - removed the broken time/index filter
// ============================================================

using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using ATAS.Indicators;

namespace ATAS.Indicators.Technical
{
    [DisplayName("TLADe Bridge")]
    [Description("Trimite date live (ticks + bare + delta) catre TLADe Terminal pe localhost:5000")]
    public class TLAdeBridgeATAS : Indicator
    {
        private static readonly HttpClient _http = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(5)
        };

        private static readonly string _logPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "ATAS", "tlade_bridge.log");

        // Channel with capacity 600: a single worker sends bars sequentially
        // Previne thread pool explosion la flood de bare istorice
        private readonly Channel<(string ticker, int bar, CandleData cd)> _barChannel
            = Channel.CreateBounded<(string, int, CandleData)>(new BoundedChannelOptions(600)
              {
                  FullMode    = BoundedChannelFullMode.DropOldest,
                  SingleReader = true,
                  SingleWriter = false
              });

        // Bar deduplication: every bar sent exactly once (key = candle.Time.Ticks)
        private readonly ConcurrentDictionary<long, byte> _postedBarTimes
            = new ConcurrentDictionary<long, byte>();

        // State intern
        private double   _lastPostedPrice    = -1;
        private DateTime _lastSpotTime       = DateTime.MinValue;
        private int      _lastPostedDailyBar = -1;
        private DateTime _lastBarDate        = DateTime.MinValue.Date;
        private bool     _liveMode           = false;
        // Time-resolution strategy auto-detected at INIT against the system
        // clock. ATAS does NOT document `Candle.Time.Kind`, and the value it
        // exposes depends on the platform's timezone settings: Local OS,
        // UTC, or the instrument's exchange timezone (e.g. CME = America/
        // Chicago). The cast `((DateTimeOffset)cd.Time)` silently assumes
        // Local for Kind=Unspecified, which produced multi-hour shifts on
        // setups outside the developer's locale. We probe the live bar
        // against DateTime.UtcNow once at INIT, pick the interpretation
        // that lands within 5 minutes of "now", and reuse it for the
        // backfill and every subsequent PostBar. No user setting needed.
        private enum TimeStrategy { Unknown, AsLocal, AsUtc, AsExchange }
        private TimeStrategy _timeStrategy   = TimeStrategy.Unknown;
        private TimeSpan     _exchangeOffset = TimeSpan.Zero;
        // Auto-rebackfill: if the Python bridge has been restarted (or is empty
        // for any reason) while this chart instance is still alive, the dedup
        // dictionary would block any re-push. We poll /health every 30s; if the
        // bridge reports bars_count below BACKFILL_THRESHOLD we clear the dedup
        // set and re-run the backfill on the next OnCalculate. Throttled to at
        // most once every 5 minutes to avoid loops.
        private DateTime _lastHealthCheck    = DateTime.MinValue;
        private DateTime _lastBackfillTime   = DateTime.MinValue;
        private volatile bool _needsBackfill = false;
        private const int BACKFILL_THRESHOLD = 50;

        [Display(Name = "Port receiver", GroupName = "TLADe", Order = 1)]
        [Range(1024, 65535)]
        public int Port { get; set; } = 5000;

        [Display(Name = "Min interval between ticks (sec)", GroupName = "TLADe", Order = 2)]
        [Range(1, 30)]
        public int SpotThrottleSeconds { get; set; } = 2;

        [Display(Name = "Send intraday bars (OFF = NT8-like, SPOT only)", GroupName = "TLADe", Order = 3)]
        public bool SendIntraBars { get; set; } = false;

        [Display(Name = "Push daily bar at session rollover", GroupName = "TLADe", Order = 4)]
        public bool SendDailyBars { get; set; } = false;

        public TLAdeBridgeATAS() : base(true)
        {
            DataSeries[0].IsHidden = true;
            // Start the worker that sends bars sequentially
            Task.Run(BarWorker);
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            // ATAS v8: bar = bar being processed; CurrentBar = total count; live bar = CurrentBar - 1
            var isLastBar = bar == CurrentBar - 1;

            // INIT: first time we reach the live bar
            if (!_liveMode && isLastBar)
            {
                var candle0 = GetCandle(bar);
                _liveMode   = true;
                Log($"INIT v2.7.1 bar={bar} CurrentBar={CurrentBar} price={candle0?.Close} instrument={DataProvider.InstrumentInfo.Instrument} port={Port}");
                if (candle0 != null) DetectTimeStrategy(candle0.Time);
                DoBackfill(bar, "INIT");
            }

            // Re-backfill when the bridge looks empty (= Python restarted while
            // this chart instance is still alive). Throttled health-check every 30s.
            if (_liveMode && isLastBar)
            {
                var nowUtc = DateTime.UtcNow;
                if ((nowUtc - _lastHealthCheck).TotalSeconds >= 30)
                {
                    _lastHealthCheck = nowUtc;
                    var tk = NormalizeTicker(DataProvider.InstrumentInfo.Instrument);
                    Task.Run(() => CheckBridgeHealthAsync(tk));
                }
                if (_needsBackfill && (nowUtc - _lastBackfillTime).TotalMinutes >= 5)
                {
                    _needsBackfill = false;
                    // Clear dedup so the same Ticks can be re-pushed.
                    _postedBarTimes.Clear();
                    DoBackfill(bar, "REBACKFILL");
                }
            }

            // 1) SPOT — throttled to SpotThrottleSeconds, sent from the live bar
            if (_liveMode && isLastBar)
            {
                var now    = DateTime.UtcNow;
                var candle = GetCandle(bar);
                var valueD = (double)value;
                var closeD = candle != null ? (double)candle.Close : 0.0;
                // value = tick real-time (actualizat per tick); candle.Close poate fi stale
                var price  = valueD > 0 ? valueD : closeD;

                if ((now - _lastSpotTime).TotalSeconds >= SpotThrottleSeconds)
                {
                    Log($"SPOT_DBG val={valueD} close={closeD} price={price} last={_lastPostedPrice}");
                    if (price > 0)
                    {
                        _lastPostedPrice = price;
                        _lastSpotTime    = now;
                        var ticker = NormalizeTicker(DataProvider.InstrumentInfo.Instrument);
                        Task.Run(() => PostSpot(ticker, price, now));
                    }
                }
            }

            // 2) BARA INCHISA — doar daca SendIntraBars=true (default false = NT8-mode)
            if (_liveMode && SendIntraBars && !isLastBar)
            {
                var candle = GetCandle(bar);
                if (candle == null) return;

                // TryAdd returns false if the bar has already been sent
                if (!_postedBarTimes.TryAdd(candle.Time.Ticks, 0)) return;

                // New-day detection -> send the D1 bar of the previous day
                if (SendDailyBars
                    && _lastBarDate != DateTime.MinValue.Date
                    && candle.Time.Date != _lastBarDate
                    && bar > 0
                    && (bar - 1) != _lastPostedDailyBar)
                {
                    _lastPostedDailyBar = bar - 1;
                    var prevCandle = GetCandle(bar - 1);
                    if (prevCandle != null)
                    {
                        var dailyCd = BuildCandleData(prevCandle);
                        var t       = NormalizeTicker(DataProvider.InstrumentInfo.Instrument);
                        Task.Run(() => PostDailyBar(t, bar - 1, dailyCd));
                    }
                }

                _lastBarDate = candle.Time.Date;

                var cd     = BuildCandleData(candle);
                var ticker = NormalizeTicker(DataProvider.InstrumentInfo.Instrument);
                _barChannel.Writer.TryWrite((ticker, bar, cd));
            }
        }

        // Push the last BACKFILL_BARS closed bars in chronological order.
        // Reused from the INIT block and from the auto-detect rebackfill branch.
        private void DoBackfill(int bar, string reason)
        {
            const int BACKFILL_BARS = 200;  // ~16h of 5m bars; ATAS usually holds less
            var ticker = NormalizeTicker(DataProvider.InstrumentInfo.Instrument);
            int fromBar = Math.Max(0, bar - BACKFILL_BARS);
            var toSend = new System.Collections.Generic.List<CandleData>();
            var idxs   = new System.Collections.Generic.List<int>();
            for (int i = fromBar; i < bar; i++)
            {
                var c = GetCandle(i);
                if (c == null) continue;
                if (!_postedBarTimes.TryAdd(c.Time.Ticks, 0)) continue;
                toSend.Add(new CandleData
                {
                    Open = (double)c.Open, High = (double)c.High,
                    Low  = (double)c.Low,  Close = (double)c.Close,
                    Volume = (double)c.Volume,
                    AskVolume = (double)c.Ask, BidVolume = (double)c.Bid,
                    Delta = (double)c.Delta, MaxDelta = (double)c.MaxDelta, MinDelta = (double)c.MinDelta,
                    Time = c.Time,
                });
                idxs.Add(i);
            }
            _lastBackfillTime = DateTime.UtcNow;
            Task.Run(() =>
            {
                for (int k = 0; k < toSend.Count; k++)
                    PostBar(ticker, idxs[k], toSend[k]);
            });
            Log($"BACKFILL[{reason}] queued {toSend.Count} historical bars (range {fromBar}..{bar - 1})");
        }

        // Poll the Python bridge to see whether it has lost its bar cache.
        // If so, signal OnCalculate to re-run the backfill.
        private async Task CheckBridgeHealthAsync(string ticker)
        {
            try
            {
                using var http = new System.Net.Http.HttpClient
                {
                    Timeout = TimeSpan.FromSeconds(5)
                };
                var resp = await http.GetAsync($"http://localhost:{Port}/health");
                if (!resp.IsSuccessStatusCode) return;
                var body = await resp.Content.ReadAsStringAsync();
                // Naive parsing — avoid pulling System.Text.Json over the wire
                // just to read one integer. Find "bars_count":{...} and the
                // ticker's value inside it.
                var key = $"\"{ticker}\":";
                int idx = body.IndexOf("\"bars_count\"");
                if (idx < 0) return;
                int tickerIdx = body.IndexOf(key, idx);
                if (tickerIdx < 0) return;
                int valStart = tickerIdx + key.Length;
                int valEnd = valStart;
                while (valEnd < body.Length && (char.IsDigit(body[valEnd]) || body[valEnd] == ' '))
                    valEnd++;
                if (!int.TryParse(body.Substring(valStart, valEnd - valStart).Trim(), out int count))
                    return;
                if (count < BACKFILL_THRESHOLD)
                {
                    Log($"HEALTH bars_count[{ticker}]={count} < {BACKFILL_THRESHOLD} → scheduling rebackfill");
                    _needsBackfill = true;
                }
            }
            catch (Exception ex)
            {
                Log($"HEALTH check failed: {ex.Message}");
            }
        }

        // Single worker that consumes the channel sequentially — no thread-pool explosion
        private async Task BarWorker()
        {
            await foreach (var (ticker, bar, cd) in _barChannel.Reader.ReadAllAsync())
                await PostBar(ticker, bar, cd);
        }

        public override void Dispose()
        {
            _barChannel.Writer.Complete();
            base.Dispose();
        }

        // Probe the live bar's reported time against UTC now to figure out how
        // ATAS is interpreting Candle.Time on this machine. A 5m bar's open
        // time should be within the [now-5min, now+5min] window. Whichever
        // interpretation lands there is the right one for this session.
        private void DetectTimeStrategy(DateTime liveBarTime)
        {
            long nowU    = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            long asLocal = ((DateTimeOffset)liveBarTime).ToUnixTimeSeconds();
            long asUtc   = ((DateTimeOffset)DateTime.SpecifyKind(liveBarTime, DateTimeKind.Utc)).ToUnixTimeSeconds();

            // Exchange candidate: assume CME / America/Chicago for ES/NQ futures.
            // (SPX/NDX indices follow ET but the ATAS Bridge ships ES/NQ only.)
            TimeSpan ctOffset;
            long asExchange;
            try
            {
                var ctTz = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                ctOffset = ctTz.GetUtcOffset(liveBarTime);
                asExchange = new DateTimeOffset(DateTime.SpecifyKind(liveBarTime, DateTimeKind.Unspecified), ctOffset).ToUnixTimeSeconds();
            }
            catch
            {
                ctOffset = TimeSpan.FromHours(-5);
                asExchange = asLocal - (long)TimeSpan.FromHours(-5).Negate().TotalSeconds; // never used if catch fires
            }

            // Pick the strategy whose interpretation is CLOSEST to "now". No
            // hard tolerance — when GetCandle(bar) returns the last closed bar
            // its open can be 5+ minutes behind now, and we still want to
            // honour the closest match (which beats any other strategy by
            // hours). Safety net: if even the closest is > 2h off, fall back
            // to AsLocal to avoid garbage on a malformed input.
            long absL = Math.Abs(nowU - asLocal);
            long absU = Math.Abs(nowU - asUtc);
            long absE = Math.Abs(nowU - asExchange);
            long min  = Math.Min(absL, Math.Min(absU, absE));
            const long SANITY_SEC = 7200; // 2h — refuse detection if the best candidate is still wildly off
            string pick;
            if (min > SANITY_SEC) { _timeStrategy = TimeStrategy.AsLocal; pick = "Local(fallback,allfar)"; }
            else if (min == absU) { _timeStrategy = TimeStrategy.AsUtc;       pick = "Utc"; }
            else if (min == absE) { _timeStrategy = TimeStrategy.AsExchange;  _exchangeOffset = ctOffset; pick = "Exchange(CT)"; }
            else                  { _timeStrategy = TimeStrategy.AsLocal;     pick = "Local"; }

            Log($"TIME_STRATEGY={pick} liveTime={liveBarTime:O} Kind={liveBarTime.Kind} nowU={nowU} asLocal={asLocal}(Δ{nowU-asLocal}s) asUtc={asUtc}(Δ{nowU-asUtc}s) asExchange={asExchange}(Δ{nowU-asExchange}s)");
        }

        // Apply the auto-detected strategy to convert a bar timestamp into
        // Unix seconds. Always returns a value; defaults to AsLocal if
        // strategy was never set (= shouldn't happen because INIT calls
        // DetectTimeStrategy before any PostBar).
        private long ResolveUnixSec(DateTime t)
        {
            switch (_timeStrategy)
            {
                case TimeStrategy.AsUtc:
                    return ((DateTimeOffset)DateTime.SpecifyKind(t, DateTimeKind.Utc)).ToUnixTimeSeconds();
                case TimeStrategy.AsExchange:
                    return new DateTimeOffset(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), _exchangeOffset).ToUnixTimeSeconds();
                case TimeStrategy.AsLocal:
                case TimeStrategy.Unknown:
                default:
                    return ((DateTimeOffset)t).ToUnixTimeSeconds();
            }
        }

        private static string NormalizeTicker(string symbol)
        {
            var s = (symbol ?? "").ToUpperInvariant();
            if (s.Contains("NQ") || s.Contains("NDX") || s.Contains("MNQ"))
                return "NQ";
            return "ES";
        }

        private static CandleData BuildCandleData(IndicatorCandle candle)
        {
            return new CandleData
            {
                Open      = (double)candle.Open,
                High      = (double)candle.High,
                Low       = (double)candle.Low,
                Close     = (double)candle.Close,
                Volume    = (double)candle.Volume,
                AskVolume = (double)candle.Ask,
                BidVolume = (double)candle.Bid,
                Delta     = (double)candle.Delta,
                MaxDelta  = (double)candle.MaxDelta,
                MinDelta  = (double)candle.MinDelta,
                Time      = candle.Time
            };
        }

        // v2.7.0 — defensive guard against partial / malformed bars reaching the
        // terminal. lightweight-charts throws "Value is null" on the receiving
        // side when any OHLC field comes through as null, NaN, Infinity, or zero.
        // We never want to send those, so any bar that fails this check is
        // dropped at the source instead of polluting the bridge cache.
        // Returns true when every OHLC field is a finite positive number.
        private static bool IsValidBar(CandleData cd)
        {
            return IsFinitePositive(cd.Open)
                && IsFinitePositive(cd.High)
                && IsFinitePositive(cd.Low)
                && IsFinitePositive(cd.Close);
        }

        private static bool IsFinitePositive(double v)
        {
            return !double.IsNaN(v) && !double.IsInfinity(v) && v > 0.0;
        }

        // JSON-safe formatter for any double we ship in payload. NaN / Infinity
        // would otherwise emit literal "NaN" / "Infinity" tokens that the JSON
        // parser on the terminal silently coerces to null. For order-flow
        // fields (delta, volume, …) we emit 0 instead — those tolerate it.
        private static string Js(double v, System.Globalization.CultureInfo ci)
        {
            if (double.IsNaN(v) || double.IsInfinity(v)) return "0";
            return v.ToString(ci);
        }

        private async Task PostSpot(string ticker, double price, DateTime ts)
        {
            // v2.7.0 — never push a non-finite or non-positive spot. The Python
            // bridge already validates this and would 400, but failing fast
            // here keeps the log readable.
            if (!IsFinitePositive(price))
            {
                Log($"SKIP SPOT (invalid price) {ticker} price={price}");
                return;
            }
            var ci = System.Globalization.CultureInfo.InvariantCulture;
            var payload = "{" +
                $"\"ticker\":\"{ticker}\"," +
                $"\"spot\":{Js(price, ci)}," +
                $"\"ts\":\"{ts:O}\"," +
                $"\"provider\":\"atas\"" +
                "}";
            await Post($"http://localhost:{Port}/push_spot", payload,
                       $"SPOT {ticker} {Js(price, ci)}");
        }

        private async Task PostBar(string ticker, int bar, CandleData cd)
        {
            // v2.7.0 — drop malformed bars before they reach the bridge.
            if (!IsValidBar(cd))
            {
                Log($"SKIP BAR (invalid OHLC) {ticker} idx={bar} time={cd.Time:HH:mm} " +
                    $"O={cd.Open} H={cd.High} L={cd.Low} C={cd.Close}");
                return;
            }

            var ci = System.Globalization.CultureInfo.InvariantCulture;
            // Use the auto-detected time strategy (see DetectTimeStrategy +
            // ResolveUnixSec). This handles Kind=Local / Utc / Unspecified
            // correctly across platforms regardless of how ATAS exposes the
            // candle timestamp on a given machine.
            long unixSec = ResolveUnixSec(cd.Time);
            var payload = "{" +
                $"\"ticker\":\"{ticker}\"," +
                $"\"bar_index\":{bar}," +
                $"\"time\":{unixSec}," +
                $"\"open\":{Js(cd.Open, ci)}," +
                $"\"high\":{Js(cd.High, ci)}," +
                $"\"low\":{Js(cd.Low, ci)}," +
                $"\"close\":{Js(cd.Close, ci)}," +
                $"\"volume\":{Js(cd.Volume, ci)}," +
                $"\"ask_volume\":{Js(cd.AskVolume, ci)}," +
                $"\"bid_volume\":{Js(cd.BidVolume, ci)}," +
                $"\"delta\":{Js(cd.Delta, ci)}," +
                $"\"max_delta\":{Js(cd.MaxDelta, ci)}," +
                $"\"min_delta\":{Js(cd.MinDelta, ci)}," +
                $"\"provider\":\"atas\"" +
                "}";
            await Post($"http://localhost:{Port}/push_bar", payload,
                       $"BAR {ticker} {cd.Time:HH:mm} C={Js(cd.Close, ci)} D={cd.Delta:+0;-0}");
        }

        private async Task PostDailyBar(string ticker, int bar, CandleData cd)
        {
            // v2.7.0 — drop malformed daily bars at source too.
            if (!IsValidBar(cd))
            {
                Log($"SKIP DAILY (invalid OHLC) {ticker} idx={bar} time={cd.Time:yyyy-MM-dd} " +
                    $"O={cd.Open} H={cd.High} L={cd.Low} C={cd.Close}");
                return;
            }

            var ci = System.Globalization.CultureInfo.InvariantCulture;
            var payload = "{" +
                $"\"ticker\":\"{ticker}\"," +
                $"\"bar_index\":{bar}," +
                $"\"time\":\"{cd.Time:yyyy-MM-dd}\"," +
                $"\"open\":{Js(cd.Open, ci)}," +
                $"\"high\":{Js(cd.High, ci)}," +
                $"\"low\":{Js(cd.Low, ci)}," +
                $"\"close\":{Js(cd.Close, ci)}," +
                $"\"volume\":{Js(cd.Volume, ci)}," +
                $"\"ask_volume\":{Js(cd.AskVolume, ci)}," +
                $"\"bid_volume\":{Js(cd.BidVolume, ci)}," +
                $"\"delta\":{Js(cd.Delta, ci)}," +
                $"\"provider\":\"atas\"" +
                "}";
            await Post($"http://localhost:{Port}/push_daily", payload,
                       $"DAILY {ticker} {cd.Time:yyyy-MM-dd} C={Js(cd.Close, ci)}");
        }

        private async Task Post(string url, string json, string label)
        {
            try
            {
                var content  = new StringContent(json, Encoding.UTF8, "application/json");
                var response = await _http.PostAsync(url, content);
                Log($"{label} -> {(response.IsSuccessStatusCode ? "OK" : $"FAIL {(int)response.StatusCode}")}");
            }
            catch (TaskCanceledException)
            {
                Log($"TIMEOUT: {label}");
            }
            catch (Exception ex)
            {
                Log($"ERR ({label}): {ex.Message}");
            }
        }

        private static void Log(string msg)
        {
            try
            {
                File.AppendAllText(_logPath,
                    $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} [TLAdeBridge] {msg}{Environment.NewLine}");
            }
            catch { }
        }

        private struct CandleData
        {
            public double   Open, High, Low, Close;
            public double   Volume, AskVolume, BidVolume;
            public double   Delta, MaxDelta, MinDelta;
            public DateTime Time;
        }
    }
}
