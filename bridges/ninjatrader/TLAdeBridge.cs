#region Using declarations
using System;
using System.Globalization;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.Data;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class TLAdeBridge : Indicator
    {
        private static readonly HttpClient httpClient = new HttpClient();
        private double lastPostedPrice = 0;
        private DateTime lastPostTime  = DateTime.MinValue;
        private int lastPostedBarIndex = -1;
        private bool backfillDone      = false;

        // How many closed bars to push on startup to seed the bridge with
        // history. The terminal expects "at least 2 weeks of 5-minute bars"
        // per Bridge Protocol §ib_data — 500 covers ~2 trading days, which
        // is enough for AVWAP/VP on the active session. The cap also keeps
        // the startup burst bounded.
        private const int BACKFILL_BARS = 500;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "TLADe local data bridge — pushes ES/NQ ticks and closed bars to localhost:5000";
                Name        = "TLAdeBridge";
                Calculate   = Calculate.OnEachTick;
                IsOverlay   = true;
                IsSuspendedWhileInactive = false;
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;

            string ticker = NormalizeTicker();

            // ── 1. Backfill on first call after data loaded ─────────────────
            // Push the most recent closed bars so the terminal has chart
            // history immediately (instead of accumulating tick-by-tick).
            if (!backfillDone && CurrentBar > 0)
            {
                backfillDone = true;
                int count = Math.Min(BACKFILL_BARS, CurrentBar);
                Task.Run(() => BackfillBars(ticker, count));
            }

            // ── 2. On the first tick of a new bar, post the just-closed bar ─
            // IsFirstTickOfBar == true means we're at the open of bar[0];
            // the bar that just closed is bar[1]. Dedupe by bar_index to
            // avoid double-posting when OnBarUpdate fires multiple times
            // at the very start of a new bar.
            if (IsFirstTickOfBar && CurrentBar > 0)
            {
                int closedBarIndex = CurrentBar - 1;
                if (closedBarIndex != lastPostedBarIndex)
                {
                    lastPostedBarIndex = closedBarIndex;
                    Task.Run(() => PostBar(ticker, 1, closedBarIndex));
                }
            }

            // ── 3. Spot tick (unchanged) ────────────────────────────────────
            double price = Close[0];
            DateTime now = DateTime.Now;

            Print($"[TLAdeBridge] OnBarUpdate fired — price={price} lastPrice={lastPostedPrice} timeDiff={(now - lastPostTime).TotalSeconds:F1}s");

            if ((now - lastPostTime).TotalSeconds < 2) return;
            if (price == lastPostedPrice) return;

            lastPostedPrice = price;
            lastPostTime    = now;

            Print($"[TLAdeBridge] Posting {ticker} {price}...");
            Task.Run(() => PostSpot(ticker, price, now));
        }

        private string NormalizeTicker()
        {
            string sym = Instrument.MasterInstrument.Name;
            return sym.StartsWith("NQ") ? "NQ" : "ES";
        }

        private async Task PostSpot(string ticker, double price, DateTime ts)
        {
            try
            {
                string payload = $"{{\"ticker\":\"{ticker}\",\"spot\":{price.ToString(CultureInfo.InvariantCulture)},\"ts\":\"{ts:O}\"}}";
                var content    = new StringContent(payload, Encoding.UTF8, "application/json");
                var response   = await httpClient.PostAsync("http://localhost:5000/push_spot", content);
                Print($"[TLAdeBridge] {ticker} {price} → {(response.IsSuccessStatusCode ? "OK" : "FAIL")}");
            }
            catch (Exception ex)
            {
                Print($"[TLAdeBridge] POST error: {ex.Message}");
            }
        }

        private async Task PostBar(string ticker, int barsAgo, int barIndex)
        {
            try
            {
                long unixTime = ((DateTimeOffset)Time[barsAgo]).ToUnixTimeSeconds();
                string payload =
                    "{" +
                    $"\"ticker\":\"{ticker}\"," +
                    $"\"time\":{unixTime}," +
                    $"\"open\":{Open[barsAgo].ToString(CultureInfo.InvariantCulture)}," +
                    $"\"high\":{High[barsAgo].ToString(CultureInfo.InvariantCulture)}," +
                    $"\"low\":{Low[barsAgo].ToString(CultureInfo.InvariantCulture)}," +
                    $"\"close\":{Close[barsAgo].ToString(CultureInfo.InvariantCulture)}," +
                    $"\"volume\":{(long)Volume[barsAgo]}," +
                    $"\"bar_index\":{barIndex}" +
                    "}";
                var content  = new StringContent(payload, Encoding.UTF8, "application/json");
                var response = await httpClient.PostAsync("http://localhost:5000/push_bar", content);
                Print($"[TLAdeBridge] BAR {ticker} idx={barIndex} t={unixTime} C={Close[barsAgo]} V={Volume[barsAgo]} → {(response.IsSuccessStatusCode ? "OK" : "FAIL")}");
            }
            catch (Exception ex)
            {
                Print($"[TLAdeBridge] BAR POST error: {ex.Message}");
            }
        }

        private async Task BackfillBars(string ticker, int count)
        {
            // Push from oldest → newest so the receiver's deduper preserves order.
            for (int i = count; i >= 1; i--)
            {
                int barIndex = CurrentBar - i;
                if (barIndex < 0) continue;
                await PostBar(ticker, i, barIndex);
                // Tiny delay so the bursty startup doesn't saturate the local socket
                // and the Python receiver has time to process between bars.
                await Task.Delay(10);
            }
            Print($"[TLAdeBridge] Backfill complete: {count} bars for {ticker}");
        }
    }
}
