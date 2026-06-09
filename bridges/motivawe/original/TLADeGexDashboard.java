package study_examples;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.Stroke;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import com.motivewave.platform.sdk.common.DataContext;
import com.motivewave.platform.sdk.common.DataSeries;
import com.motivewave.platform.sdk.common.Defaults;
import com.motivewave.platform.sdk.common.DrawContext;
import com.motivewave.platform.sdk.common.Instrument;
import com.motivewave.platform.sdk.common.NVP;
import com.motivewave.platform.sdk.common.desc.BooleanDescriptor;
import com.motivewave.platform.sdk.common.desc.ColorDescriptor;
import com.motivewave.platform.sdk.common.desc.DiscreteDescriptor;
import com.motivewave.platform.sdk.common.desc.DoubleDescriptor;
import com.motivewave.platform.sdk.common.desc.IntegerDescriptor;
import com.motivewave.platform.sdk.common.desc.SettingGroup;
import com.motivewave.platform.sdk.common.desc.SettingTab;
import com.motivewave.platform.sdk.common.desc.SettingsDescriptor;
import com.motivewave.platform.sdk.common.desc.StringDescriptor;
import com.motivewave.platform.sdk.draw.Figure;
import com.motivewave.platform.sdk.study.RuntimeDescriptor;
import com.motivewave.platform.sdk.study.Study;
import com.motivewave.platform.sdk.study.StudyHeader;

/**
 * TLADe GEX Dashboard — MotiveWave port of the NinjaTrader 8 {@code TLADeGexDashboardNT}
 * indicator.
 *
 * <p>Renders a Gamma-Exposure (GEX) "dashboard" from a single data string exported by the
 * TLADe Terminal. The string carries three optional sections, pipe-separated:</p>
 *
 * <pre>  S:&lt;spread&gt; | L:&lt;levels&gt; | P:&lt;profile&gt;</pre>
 *
 * <ul>
 *   <li><b>S:</b> real-time ES&ndash;SPX spread (overrides the manual spread setting).</li>
 *   <li><b>L:</b> {@code ;}-separated level records {@code strike,type,label,tooltip,magnitude}.
 *       Types: GEX walls {@code CW/PW/GL}, system {@code ZG/MP/EH/EL/VH/VL}, structure
 *       {@code PDH/PDL/PWH/PWL}.</li>
 *   <li><b>P:</b> {@code ;}-separated profile rows {@code strike,value,sign} drawn as a
 *       right-edge histogram (call/put colored).</li>
 * </ul>
 *
 * <p>All strikes are quoted in <b>ES points</b>; {@link #convertPrice} maps them to the chart's
 * display instrument (ES/SPX/SPY/NQ/NDX/QQQ) using the configured spreads.</p>
 *
 * <p><b>Layout differs from NinjaTrader.</b> NT8 anchors every element in bar/offset space
 * ({@code RightOffsetBars}, {@code LabelPaddingBars}, {@code ProfileOffsetBars}). MotiveWave
 * Figures paint in pixel space, so this port draws level lines across the full plot width,
 * places labels at the right edge, and renders the profile histogram as right-aligned pixel
 * bars whose length is scaled by {@code ProfileWidthBars * barWidth}. The behaviour (which
 * levels show, colors, filtering, profile semantics, auto-fetch) is faithful; only the
 * coordinate model is adapted. Drawing is done in a single custom {@link Figure} because the
 * SDK's bundled {@code Enums} nested types do not resolve at compile time in this build.</p>
 *
 * <p><b>Auto-fetch.</b> When enabled, the study pulls the latest levels from the TLADe Cloud
 * Function on load and at the six daily ET windows, on a background thread (the SDK draw/calc
 * threads are never blocked on network I/O). With an API key it fetches live data; without one
 * it fetches free delayed (3-business-day) data and shows a banner.</p>
 */
@StudyHeader(
    namespace = "com.custom",
    id = "TLADE_GEX_DASHBOARD",
    name = "TLADe GEX Dashboard",
    label = "TLADe GEX",
    desc = "Gamma-Exposure dashboard from a TLADe Terminal data string (S:/L:/P:). Draws GEX, "
         + "system and structure levels with labels plus a right-edge GEX profile histogram. "
         + "Strikes are in ES points and mapped to the chart instrument via configurable spreads. "
         + "Optional background auto-fetch from the TLADe API (live with key, delayed without).",
    menu = "My Studies",
    overlay = true,
    studyOverlay = true,
    supportsBarUpdates = true)
public class TLADeGexDashboard extends Study
{
  // ---- Setting keys ----------------------------------------------------------------------------
  final static String DISPLAY_TICKER = "displayTicker";
  final static String ES_SPX_SPREAD  = "esSpxSpread";
  final static String NQ_NDX_SPREAD  = "nqNdxSpread";

  final static String GEX_DATA = "gexData";

  final static String SHOW_GEX       = "showGex";
  final static String SHOW_SYSTEM    = "showSystem";
  final static String SHOW_STRUCTURE = "showStructure";
  final static String MAX_GEX        = "maxGex";
  final static String SHOW_ONLY_NEAR = "showOnlyNear";
  final static String NEAR_PCT       = "nearPct";
  final static String ENABLE_THRESH  = "enableThreshold";
  final static String GEX_THRESHOLD  = "gexThreshold";

  final static String THEME          = "theme";
  final static String BAR_COLOR      = "barColorStyle";
  final static String CUSTOM_CALL    = "customCallColor";
  final static String CUSTOM_PUT     = "customPutColor";

  final static String SHOW_LABELS    = "showLabels";
  final static String LABEL_SIZE     = "labelFontSize";

  final static String SHOW_PROFILE   = "showProfile";
  final static String PROFILE_WIDTH  = "profileWidthBars";
  final static String PROFILE_HEIGHT = "profileBarHeightTicks";
  final static String PROFILE_SCALE  = "profileScaleMax";
  final static String AUTO_SCALE     = "autoScaleProfileMax";
  final static String MAX_PROFILE    = "maxProfileRows";

  final static String AUTO_FETCH     = "autoFetch";
  final static String API_KEY        = "apiKey";

  final static String SHOW_STATUS    = "showStatus";

  // ---- Auto-fetch constants (mirrors NT8) ------------------------------------------------------
  private static final String API_URL = "https://europe-west1-omggex.cloudfunctions.net/indicatorData";
  // 6 fetch times per day (ET), as minutes-of-day:
  // ASIA 18:05, EU 02:05, PRE 08:05, RTH 09:35, OPRANGE 10:35, PWRHOUR 13:05
  private static final int[] FETCH_MINUTES_ET = {1085, 125, 485, 575, 635, 785};

  // ---- Parsed model ----------------------------------------------------------------------------
  private static class LevelEntry
  {
    double esStrike;
    String type;
    String label;
    double magnitude;
  }

  private static class ProfileEntry
  {
    double esStrike;
    double value;
    double sign; // -1 put, +1 call (color only)
  }

  private final List<LevelEntry> levels = new ArrayList<>();
  private final List<ProfileEntry> profile = new ArrayList<>();

  // ---- Precomputed draw model (built in calculateValues, painted by the figure) ----------------
  // The figure is fully self-contained: it reads only these lists plus DrawContext bounds/translate,
  // never DataContext at draw time (mirrors the working SigmaZones figures).
  private static class DrawLevel
  {
    double price;       // converted to display-instrument price
    Color color;
    boolean gex, sys;   // stroke style: gex=solid, sys=dash, else=dot
    int lineWidth;
    String label;       // "" when labels hidden
  }

  private static class DrawProf
  {
    double price;       // converted price (bar vertical center)
    double frac;        // |value| / maxAbs  (length fraction; pixels resolved at draw time)
    Color color;        // already alpha-blended
  }

  private final List<DrawLevel> drawLevels = new ArrayList<>();
  private final List<DrawProf> drawProfile = new ArrayList<>();
  private int profWidthBars = 70;
  private int profHeightTicks = 8;

  // Last DataContext seen, so the background fetch thread can request a recalc on completion.
  private volatile DataContext lastCtx = null;

  // Diagnostic snapshot (shown by the status banner when SHOW_STATUS is on).
  private volatile String statusText = "TLADe GEX: initializing…";

  // Theme / bar brushes resolved from settings (recomputed on each rebuild).
  private Color posColor = new Color(0x22, 0xc5, 0x5e);
  private Color negColor = new Color(0xef, 0x44, 0x44);
  private Color profCallColor = negColor;
  private Color profPutColor  = posColor;

  // Auto-fetch bookkeeping.
  private volatile String fetchedData = null; // set by background thread, consumed on next calc
  private int lastFetchMinuteET = -1;
  private long lastFetchTimeMs = 0L;
  private boolean delayedMode = false;
  private volatile boolean fetchInFlight = false;

  // ================================================================================================
  // Initialization
  // ================================================================================================

  @Override
  public void initialize(Defaults defaults)
  {
    SettingsDescriptor sd = createSD();

    // --- Ticker ---------------------------------------------------------------------------------
    SettingTab tickerTab = sd.addTab("Ticker");
    SettingGroup tickerGrp = tickerTab.addGroup("Ticker Settings");
    List<NVP> tickers = new ArrayList<>();
    for (String t : new String[] {"ES", "SPX", "SPY", "NQ", "NDX", "QQQ"})
      tickers.add(new NVP(t, t));
    tickerGrp.addRow(new DiscreteDescriptor(DISPLAY_TICKER, "Display Ticker", "ES", tickers)
        .setDescription("Strikes are quoted in ES points; this maps them to the chart instrument."));
    tickerGrp.addRow(new DoubleDescriptor(ES_SPX_SPREAD, "ES-SPX Spread", 24.0, 0.0, 1000.0, 0.01));
    tickerGrp.addRow(new DoubleDescriptor(NQ_NDX_SPREAD, "NQ-NDX Spread", 40.0, 0.0, 1000.0, 0.01));

    // --- Data -----------------------------------------------------------------------------------
    SettingTab dataTab = sd.addTab("Data");
    SettingGroup dataGrp = dataTab.addGroup("GEX Data");
    dataGrp.addRow(new StringDescriptor(GEX_DATA, "GEX Data (paste from TLADe)", "")
        .setHeight(90));
    SettingGroup fetchGrp = dataTab.addGroup("Auto-Fetch");
    fetchGrp.addRow(new BooleanDescriptor(AUTO_FETCH, "Auto-Fetch from TLADe API", true)
        .setDescription("Fetch levels on load and at the 6 daily ET windows, on a background "
            + "thread. Replaces the pasted data."));
    fetchGrp.addRow(new StringDescriptor(API_KEY, "API Key (from TLADe Terminal)", "")
        .setDescription("With a key: live data. Without: free delayed (3 business days)."));

    // --- Level Visibility -----------------------------------------------------------------------
    SettingTab visTab = sd.addTab("Levels");
    SettingGroup visGrp = visTab.addGroup("Visibility");
    visGrp.addRow(new BooleanDescriptor(SHOW_GEX, "Show GEX Levels (CW/PW/GL)", true));
    visGrp.addRow(new BooleanDescriptor(SHOW_SYSTEM, "Show System Levels (ZG/MP/EH/EL/VH/VL)", true));
    visGrp.addRow(new BooleanDescriptor(SHOW_STRUCTURE, "Show Structure Levels (PDH/PDL/PWH/PWL)", true));
    visGrp.addRow(new IntegerDescriptor(MAX_GEX, "Max GEX Levels (999=All)", 10, 1, 999, 1)
        .setDescription("Caps GEX walls shown, split above/below price. Nearest above & below "
            + "are always kept."));
    visGrp.addRow(new BooleanDescriptor(SHOW_ONLY_NEAR, "Show only levels near price", false));
    visGrp.addRow(new DoubleDescriptor(NEAR_PCT, "  Radius (%)", 3.0, 0.1, 25.0, 0.1));
    visGrp.addRow(new BooleanDescriptor(ENABLE_THRESH, "Enable GEX Threshold Filter", false));
    visGrp.addRow(new DoubleDescriptor(GEX_THRESHOLD, "  Min GEX Magnitude (M)", 50.0, 0.0, 5000.0, 1.0));

    // --- Colors ---------------------------------------------------------------------------------
    SettingTab colorTab = sd.addTab("Colors");
    SettingGroup themeGrp = colorTab.addGroup("Theme");
    List<NVP> themes = new ArrayList<>();
    themes.add(new NVP("Wall Street Classic", "Wall Street Classic"));
    themes.add(new NVP("Boreal", "Boreal"));
    themes.add(new NVP("Lady Trader", "Lady Trader"));
    themeGrp.addRow(new DiscreteDescriptor(THEME, "Theme", "Wall Street Classic", themes));
    List<NVP> barStyles = new ArrayList<>();
    barStyles.add(new NVP("Theme Colors", "Theme Colors"));
    barStyles.add(new NVP("Greyscale", "Greyscale"));
    barStyles.add(new NVP("Custom", "Custom"));
    themeGrp.addRow(new DiscreteDescriptor(BAR_COLOR, "Bar Color Style", "Theme Colors", barStyles));
    themeGrp.addRow(new ColorDescriptor(CUSTOM_CALL, "  Custom Call Bar Color", new Color(0xef, 0x44, 0x44)));
    themeGrp.addRow(new ColorDescriptor(CUSTOM_PUT, "  Custom Put Bar Color", new Color(0x22, 0xc5, 0x5e)));

    // --- Labels ---------------------------------------------------------------------------------
    SettingGroup labelGrp = colorTab.addGroup("Labels");
    labelGrp.addRow(new BooleanDescriptor(SHOW_LABELS, "Show Labels", true));
    labelGrp.addRow(new IntegerDescriptor(LABEL_SIZE, "Label Font Size", 11, 6, 50, 1));

    // --- Profile --------------------------------------------------------------------------------
    SettingTab profTab = sd.addTab("Profile");
    SettingGroup profGrp = profTab.addGroup("GEX Profile (P:)");
    profGrp.addRow(new BooleanDescriptor(SHOW_PROFILE, "Show Profile Bars", true));
    profGrp.addRow(new IntegerDescriptor(PROFILE_WIDTH, "Profile Width (bars)", 70, 1, 500, 1)
        .setDescription("Max histogram length, in bar-widths, anchored at the right edge."));
    profGrp.addRow(new IntegerDescriptor(PROFILE_HEIGHT, "Profile Bar Height (ticks)", 8, 1, 50, 1));
    profGrp.addRow(new DoubleDescriptor(PROFILE_SCALE, "Profile Scale Max", 10.0, 0.1, 1000.0, 0.1));
    profGrp.addRow(new BooleanDescriptor(AUTO_SCALE, "Auto Scale Profile Max", false));
    profGrp.addRow(new IntegerDescriptor(MAX_PROFILE, "Max Profile Rows", 1500, 10, 5000, 1));

    SettingGroup devGrp = profTab.addGroup("Developer");
    devGrp.addRow(new BooleanDescriptor(SHOW_STATUS, "Show Status / Diagnostics Banner", true)
        .setDescription("Top-left overlay showing data state, parsed/visible counts, spot and "
            + "converted price range. Turn off once levels render correctly."));

    // --- Runtime --------------------------------------------------------------------------------
    RuntimeDescriptor rd = createRD();
    rd.setLabelSettings(DISPLAY_TICKER);
  }

  @Override
  public void clearState()
  {
    super.clearState();
    levels.clear();
    profile.clear();
    fetchedData = null;
    lastFetchMinuteET = -1;
    lastFetchTimeMs = 0L;
    fetchInFlight = false;
  }

  /** Force a full rebuild whenever the user edits any setting. */
  @Override
  public void onSettingsUpdated(DataContext ctx)
  {
    super.onSettingsUpdated(ctx);
    if (ctx != null) recalculate(ctx);
  }

  /** Kick off the initial fetch when the study is loaded onto a chart. */
  @Override
  public void onLoad(Defaults defaults)
  {
    super.onLoad(defaults);
    if (getSettings().getBoolean(AUTO_FETCH, true))
      startFetch(true);
  }

  // ================================================================================================
  // Calculation / figure build
  // ================================================================================================

  @Override
  protected void calculateValues(DataContext ctx)
  {
    DataSeries series = ctx.getDataSeries();
    Instrument instr = ctx.getInstrument();
    if (series == null || instr == null || series.size() == 0) return;

    lastCtx = ctx;

    // Consume any data delivered by the background fetch thread.
    String pending = fetchedData;
    if (pending != null) {
      fetchedData = null;
      getSettings().setString(GEX_DATA, pending);
    }

    // Schedule the next time-window fetch (non-blocking).
    maybeScheduleFetch();

    resolveColors();
    parse(getSettings().getString(GEX_DATA, ""));

    double spot = lastClose(series);
    buildDrawModel(spot, ctx);

    buildStatus(series, instr, spot);

    clearFigures();
    beginFigureUpdate();
    addFigure(new DashboardFigure());
    endFigureUpdate();
  }

  /** Compose the diagnostic snapshot shown by the status banner. */
  private void buildStatus(DataSeries series, Instrument instr, double spot)
  {
    String raw = getSettings().getString(GEX_DATA, "");
    int rawLen = (raw == null) ? 0 : raw.trim().length();
    String ticker = getSettings().getString(DISPLAY_TICKER, "ES");

    // Converted price span of all parsed levels (helps spot a range mismatch).
    double lo = Double.MAX_VALUE, hi = -Double.MAX_VALUE;
    for (LevelEntry l : levels) {
      double y = convertPrice(l.esStrike);
      lo = Math.min(lo, y); hi = Math.max(hi, y);
    }
    String span = levels.isEmpty() ? "n/a"
        : String.format(Locale.ROOT, "%.1f..%.1f", lo, hi);

    boolean fetching = fetchInFlight;
    boolean autoFetch = getSettings().getBoolean(AUTO_FETCH, true);
    boolean hasKey = !getSettings().getString(API_KEY, "").trim().isEmpty();

    statusText = String.format(Locale.ROOT,
        "TLADe GEX  ticker=%s  autoFetch=%s key=%s%s\n"
      + "dataChars=%d  parsed: %d levels / %d profile\n"
      + "visible: %d levels / %d profile\n"
      + "spot=%.2f  bars=%d  levelSpan(%s)=%s",
        ticker, autoFetch, hasKey, fetching ? " [fetching…]" : "",
        rawLen, levels.size(), profile.size(),
        drawLevels.size(), drawProfile.size(),
        spot, series.size(), ticker, span);
  }

  /** Latest non-NaN close. */
  private static double lastClose(DataSeries series)
  {
    for (int i = series.size() - 1; i >= 0; i--) {
      double c = series.getClose(i);
      if (!Double.isNaN(c)) return c;
    }
    return Double.NaN;
  }

  /**
   * Build the precomputed lists the figure paints from. Runs here (not in draw) because the
   * filtering needs {@code spot} and the level caps must be applied once, deterministically.
   */
  private void buildDrawModel(double spot, DataContext ctx)
  {
    drawLevels.clear();
    drawProfile.clear();
    profWidthBars = Math.max(1, getSettings().getInteger(PROFILE_WIDTH, 70));
    profHeightTicks = Math.max(1, getSettings().getInteger(PROFILE_HEIGHT, 8));

    boolean showLabels = getSettings().getBoolean(SHOW_LABELS, true);

    // ---- Levels ----
    if (!levels.isEmpty() && !Double.isNaN(spot)) {
      int maxVisible = getSettings().getInteger(MAX_GEX, 10);
      if (maxVisible <= 0) maxVisible = 10;
      int halfMax = (int) Math.ceil(maxVisible / 2.0);
      boolean maxIsAll = maxVisible >= 999;

      boolean showGex = getSettings().getBoolean(SHOW_GEX, true);
      boolean showSystem = getSettings().getBoolean(SHOW_SYSTEM, true);
      boolean showStructure = getSettings().getBoolean(SHOW_STRUCTURE, true);
      boolean onlyNear = getSettings().getBoolean(SHOW_ONLY_NEAR, false);
      double nearPct = getSettings().getDouble(NEAR_PCT, 3.0);
      boolean enableThresh = getSettings().getBoolean(ENABLE_THRESH, false);
      double threshold = getSettings().getDouble(GEX_THRESHOLD, 50.0);

      double closestAboveEs = Double.NaN, closestBelowEs = Double.NaN;
      double closestAboveDist = Double.MAX_VALUE, closestBelowDist = Double.MAX_VALUE;
      for (LevelEntry lvl : levels) {
        if (!isGex(lvl.type)) continue;
        double y0 = convertPrice(lvl.esStrike);
        double dist = Math.abs(y0 - spot);
        if (y0 > spot && dist < closestAboveDist) { closestAboveDist = dist; closestAboveEs = lvl.esStrike; }
        else if (y0 <= spot && dist < closestBelowDist) { closestBelowDist = dist; closestBelowEs = lvl.esStrike; }
      }

      int gexAboveDrawn = 0, gexBelowDrawn = 0;
      for (LevelEntry lvl : levels) {
        double y = convertPrice(lvl.esStrike);
        boolean inRange = !onlyNear
            || (Math.abs(spot - y) / Math.max(1e-9, spot) * 100.0 <= nearPct);

        boolean gex = isGex(lvl.type);
        boolean sys = isSystem(lvl.type);
        boolean struct = isStructure(lvl.type);

        boolean passesThreshold = !enableThresh || !gex || lvl.magnitude == 0.0
            || lvl.magnitude >= threshold;
        boolean isProtected = gex
            && (nearlyEqual(lvl.esStrike, closestAboveEs) || nearlyEqual(lvl.esStrike, closestBelowEs));
        boolean isAbove = y > spot;

        boolean shouldShow = false;
        if (gex && showGex && passesThreshold) {
          if (maxIsAll) shouldShow = true;
          else if (isProtected) shouldShow = true;
          else if (isAbove && gexAboveDrawn < halfMax) shouldShow = true;
          else if (!isAbove && gexBelowDrawn < halfMax) shouldShow = true;
        } else if (sys && showSystem) shouldShow = true;
        else if (struct && showStructure) shouldShow = true;

        if (!shouldShow || !inRange) continue;

        if ((lvl.type.equals("CW") || lvl.type.equals("PW")) && !maxIsAll && !isProtected) {
          if (isAbove) gexAboveDrawn++; else gexBelowDrawn++;
        }

        DrawLevel d = new DrawLevel();
        d.price = y;
        d.color = colorFor(lvl, y, spot);
        d.gex = gex;
        d.sys = sys;
        d.lineWidth = (lvl.type.equals("ZG") || lvl.type.equals("MP")) ? 2 : 1;
        d.label = showLabels ? (formatPrice(lvl.esStrike) + " " + lvl.label) : "";
        drawLevels.add(d);
      }
    }

    // ---- Profile ----
    if (getSettings().getBoolean(SHOW_PROFILE, true) && !profile.isEmpty()) {
      double scaleMax = Math.max(1e-9, getSettings().getDouble(PROFILE_SCALE, 10.0));
      double maxAbs = scaleMax;
      if (getSettings().getBoolean(AUTO_SCALE, false)) {
        double dataMax = 0.0;
        for (ProfileEntry pr : profile) dataMax = Math.max(dataMax, Math.abs(pr.value));
        maxAbs = Math.max(maxAbs, dataMax);
      }
      for (ProfileEntry pr : profile) {
        double lenValue = Math.abs(pr.value);
        double frac = lenValue / maxAbs;
        if (frac <= 0) continue;
        Color base = (pr.sign >= 0) ? profCallColor : profPutColor;
        double intensity = Math.min(1.0, frac);
        int alpha = clamp((int) Math.round(255.0 * (0.60 + intensity * 0.40)), 0, 255);
        DrawProf dp = new DrawProf();
        dp.price = convertPrice(pr.esStrike);
        dp.frac = Math.min(1.0, frac);
        dp.color = new Color(base.getRed(), base.getGreen(), base.getBlue(), alpha);
        drawProfile.add(dp);
      }
    }
  }

  /** Live bars: nudge a redraw so the right-edge anchored figure stays put. */
  @Override
  public void onBarUpdate(DataContext ctx)
  {
    super.onBarUpdate(ctx);
    lastCtx = ctx;
    if (fetchedData != null) {
      recalculate(ctx);
      return;
    }
    maybeScheduleFetch();
    notifyRedraw();
  }

  // ================================================================================================
  // Data-string parsing (faithful to NT8 ParseIfChanged)
  // ================================================================================================

  private void parse(String input)
  {
    levels.clear();
    profile.clear();

    String raw = (input == null ? "" : input).replace("\r", "").replace("\n", "").trim();
    if (raw.isEmpty()) return;

    // v7.1: optional "S:<spread>|..." prefix overrides the ES-SPX spread setting.
    if (raw.startsWith("S:")) {
      int sEnd = raw.indexOf('|');
      if (sEnd > 2) {
        String spreadStr = raw.substring(2, sEnd);
        Double parsed = tryParse(spreadStr);
        if (parsed != null && parsed > 0)
          getSettings().setDouble(ES_SPX_SPREAD, parsed);
        raw = raw.substring(sEnd + 1);
      }
    }

    String levelsData = "";
    String profileData = "";

    int pipePos = raw.indexOf("|P:");
    if (pipePos >= 0) {
      String beforePipe = raw.substring(0, pipePos);
      if (beforePipe.startsWith("L:")) levelsData = beforePipe.substring(2);
      profileData = raw.substring(pipePos + 3);
    } else if (raw.startsWith("L:")) {
      levelsData = raw.substring(2);
    }

    if (!levelsData.isEmpty()) {
      for (String p : levelsData.split(";")) {
        if (p.isEmpty()) continue;
        String[] parts = p.split(",", -1);
        if (parts.length < 3) continue;

        Double strike = tryParse(parts[0]);
        if (strike == null) continue;

        LevelEntry e = new LevelEntry();
        e.esStrike = strike;
        e.type = parts[1].trim();
        e.label = parts[2].trim();
        e.magnitude = 0.0;
        if (parts.length >= 5) {
          Double mag = tryParse(parts[4]);
          if (mag != null) e.magnitude = Math.abs(mag);
        }
        levels.add(e);
      }
    }

    if (!profileData.isEmpty()) {
      int maxRows = getSettings().getInteger(MAX_PROFILE, 1500);
      int n = 0;
      for (String r : profileData.split(";")) {
        if (n >= maxRows) break;
        if (r.isEmpty()) continue;
        String[] parts = r.split(",", -1);
        if (parts.length != 3) continue;
        Double strike = tryParse(parts[0]);
        Double value = tryParse(parts[1]);
        Double sign = tryParse(parts[2]);
        if (strike == null || value == null || sign == null) continue;
        ProfileEntry pe = new ProfileEntry();
        pe.esStrike = strike;
        pe.value = value;
        pe.sign = sign;
        profile.add(pe);
        n++;
      }
    }
  }

  private static Double tryParse(String s)
  {
    if (s == null) return null;
    try { return Double.parseDouble(s.trim()); }
    catch (NumberFormatException e) { return null; }
  }

  // ================================================================================================
  // Price mapping (ES points -> display instrument)
  // ================================================================================================

  private boolean isNqFamily()
  {
    String t = getSettings().getString(DISPLAY_TICKER, "ES").toUpperCase(Locale.ROOT);
    return t.equals("NQ") || t.equals("NDX") || t.equals("QQQ");
  }

  private double convertPrice(double esPrice)
  {
    String t = getSettings().getString(DISPLAY_TICKER, "ES").toUpperCase(Locale.ROOT);
    double esSpx = getSettings().getDouble(ES_SPX_SPREAD, 24.0);
    double nqNdx = getSettings().getDouble(NQ_NDX_SPREAD, 40.0);
    switch (t) {
      case "SPX": return esPrice - esSpx;
      case "SPY": return (esPrice - esSpx) / 10.0;
      case "NQ":  return esPrice;
      case "NDX": return esPrice - nqNdx;
      case "QQQ": return (esPrice - nqNdx) / 40.0;
      default:    return esPrice; // ES
    }
  }

  private String formatPrice(double esPrice)
  {
    double c = convertPrice(esPrice);
    String t = getSettings().getString(DISPLAY_TICKER, "ES").toUpperCase(Locale.ROOT);
    if (t.equals("SPY") || t.equals("QQQ"))
      return String.format(Locale.ROOT, "%.2f", c);
    // %.0f already rounds to the nearest integer; pass the double (not Math.round's long,
    // which would throw IllegalFormatConversionException against the %f conversion).
    return String.format(Locale.ROOT, "%.0f", c);
  }

  // ================================================================================================
  // Level-type classification (faithful to NT8)
  // ================================================================================================

  private static boolean isGex(String t) { return t.equals("CW") || t.equals("PW") || t.equals("GL"); }
  private static boolean isSystem(String t)
  {
    return t.equals("ZG") || t.equals("MP") || t.equals("EH") || t.equals("EL")
        || t.equals("VH") || t.equals("VL");
  }
  private static boolean isStructure(String t)
  {
    return t.equals("PDH") || t.equals("PDL") || t.equals("PWH") || t.equals("PWL");
  }

  private static boolean nearlyEqual(double a, double b)
  {
    if (Double.isNaN(a) || Double.isNaN(b)) return false;
    return Math.abs(a - b) < 1e-9;
  }

  // ================================================================================================
  // Colors / theme
  // ================================================================================================

  private void resolveColors()
  {
    posColor = new Color(0x22, 0xc5, 0x5e);
    negColor = new Color(0xef, 0x44, 0x44);

    String theme = getSettings().getString(THEME, "Wall Street Classic").trim();
    if (theme.equalsIgnoreCase("Boreal")) {
      posColor = new Color(0x22, 0xd3, 0xee);
      negColor = new Color(0xf4, 0x72, 0xb6);
    } else if (theme.equalsIgnoreCase("Lady Trader")) {
      posColor = new Color(0x2d, 0xd4, 0xbf);
      negColor = new Color(0xc0, 0x84, 0xfc);
    }

    String bcs = getSettings().getString(BAR_COLOR, "Theme Colors").trim();
    if (bcs.equalsIgnoreCase("Greyscale")) {
      profCallColor = new Color(0xa0, 0xa0, 0xa0);
      profPutColor  = new Color(0x50, 0x50, 0x50);
    } else if (bcs.equalsIgnoreCase("Custom")) {
      profCallColor = getSettings().getColor(CUSTOM_CALL, new Color(0xef, 0x44, 0x44));
      profPutColor  = getSettings().getColor(CUSTOM_PUT, new Color(0x22, 0xc5, 0x5e));
    } else { // Theme Colors (inverted: call=neg, put=pos — matches TV)
      profCallColor = negColor;
      profPutColor  = posColor;
    }
  }

  // ================================================================================================
  // Auto-fetch (background thread; never blocks calc/draw)
  // ================================================================================================

  /** Check the ET clock and fire a background fetch inside a scheduled window. */
  private void maybeScheduleFetch()
  {
    if (!getSettings().getBoolean(AUTO_FETCH, true)) return;

    java.time.ZonedDateTime etNow;
    try {
      etNow = java.time.ZonedDateTime.now(java.time.ZoneId.of("America/New_York"));
    } catch (Exception e) { return; }
    int etMins = etNow.getHour() * 60 + etNow.getMinute();

    int matchedSlot = -1;
    for (int slot : FETCH_MINUTES_ET) {
      int diff = etMins - slot;
      if (diff >= 0 && diff < 5) { matchedSlot = slot; break; }
    }
    if (matchedSlot < 0) return;
    if (matchedSlot == lastFetchMinuteET) return;
    if (System.currentTimeMillis() - lastFetchTimeMs < 4 * 60 * 1000L) return; // debounce

    lastFetchMinuteET = matchedSlot;
    lastFetchTimeMs = System.currentTimeMillis();
    startFetch(false);
  }

  /** Spawn a daemon thread to GET the data; result lands in {@link #fetchedData}. */
  private void startFetch(boolean startup)
  {
    if (fetchInFlight) return;
    final boolean hasKey = !getSettings().getString(API_KEY, "").trim().isEmpty();
    // On a timed (non-startup) fetch, require a key (free mode is fetched once at startup).
    if (!startup && !hasKey) return;

    final String ticker = isNqFamily() ? "NDX" : "SPX";
    final String apiKey = getSettings().getString(API_KEY, "").trim();
    fetchInFlight = true;

    Thread t = new Thread(() -> {
      try {
        String urlStr = hasKey
            ? API_URL + "?ticker=" + ticker
            : API_URL + "?ticker=" + ticker + "&mode=free";
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);
        conn.setRequestProperty("User-Agent", "TLADe-MW/1.0");
        if (hasKey) conn.setRequestProperty("X-API-Key", apiKey);

        int code = conn.getResponseCode();
        String data = readAll(code >= 200 && code < 400 ? conn.getInputStream() : conn.getErrorStream());
        if (data != null && data.contains("L:")) {
          fetchedData = data;
          delayedMode = !hasKey;
          // Re-run calc so the new string is parsed and the draw model rebuilt — a bare
          // notifyRedraw() would only repaint the (still-empty) figure.
          DataContext c = lastCtx;
          if (c != null) recalculate(c);
          else notifyRedraw();
        }
      } catch (Exception ignore) {
        // Silent fail — fall back to whatever is in GEX_DATA.
      } finally {
        fetchInFlight = false;
      }
    }, "TLADe-GEX-fetch");
    t.setDaemon(true);
    t.start();
  }

  private static String readAll(InputStream in) throws Exception
  {
    if (in == null) return null;
    try (InputStream s = in) {
      byte[] buf = s.readAllBytes();
      return new String(buf, StandardCharsets.UTF_8);
    }
  }

  // ================================================================================================
  // The dashboard figure — paints lines, labels and the profile histogram in pixel space.
  // ================================================================================================

  private class DashboardFigure extends Figure
  {
    @Override
    public boolean isVisible(DrawContext ctx) { return true; }

    @Override
    public void draw(Graphics2D gc, DrawContext ctx)
    {
      Rectangle b = ctx.getBounds();
      if (b == null) return;

      gc.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
      gc.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

      // Profile first (underlay), then level lines/labels on top.
      if (!drawProfile.isEmpty())
        paintProfile(gc, ctx, b);

      if (!drawLevels.isEmpty())
        paintLevels(gc, ctx, b);

      if (delayedMode)
        drawDelayedBanner(gc, b);

      // Diagnostics — drawn last so it is always visible, even when nothing else renders.
      if (getSettings().getBoolean(SHOW_STATUS, true))
        drawStatus(gc, b);
    }

    private void drawStatus(Graphics2D gc, Rectangle b)
    {
      String txt = statusText;
      if (txt == null || txt.isEmpty()) return;
      Font f = new Font("Monospaced", Font.PLAIN, 11);
      gc.setFont(f);
      FontMetrics fm = gc.getFontMetrics();
      String[] lines = txt.split("\n");
      int w = 0;
      for (String ln : lines) w = Math.max(w, fm.stringWidth(ln));
      int pad = 6;
      int lineH = fm.getHeight();
      int boxW = w + pad * 2;
      int boxH = lines.length * lineH + pad * 2;
      int x = b.x + 6;
      int y = b.y + 6;
      gc.setColor(new Color(0, 0, 0, 190));
      gc.fillRect(x, y, boxW, boxH);
      gc.setColor(new Color(120, 200, 255));
      gc.drawRect(x, y, boxW, boxH);
      int ty = y + pad + fm.getAscent();
      for (String ln : lines) {
        gc.drawString(ln, x + pad, ty);
        ty += lineH;
      }
    }

    private void paintLevels(Graphics2D gc, DrawContext ctx, Rectangle b)
    {
      Font font = labelFont(ctx.getDefaults());
      gc.setFont(font);
      FontMetrics fm = gc.getFontMetrics();

      for (DrawLevel d : drawLevels) {
        int yPix = ctx.translateValue(d.price);
        if (yPix < b.y - 2 || yPix > b.y + b.height + 2) continue; // off-screen

        gc.setStroke(strokeFor(d.gex, d.sys, d.lineWidth));
        gc.setColor(d.color);
        gc.drawLine(b.x, yPix, b.x + b.width, yPix);

        if (!d.label.isEmpty()) {
          int textW = fm.stringWidth(d.label);
          int padX = 4, padY = 1;
          int chipW = textW + padX * 2;
          int chipH = fm.getHeight() + padY * 2;
          int x = b.x + b.width - chipW - 2;
          int y2 = yPix - chipH / 2;
          gc.setColor(d.color);
          gc.fillRect(x, y2, chipW, chipH);
          gc.setColor(contrastColor(d.color));
          gc.drawString(d.label, x + padX, y2 + padY + fm.getAscent());
        }
      }
    }

    private void paintProfile(Graphics2D gc, DrawContext ctx, Rectangle b)
    {
      double barWidthPx = Math.max(1.0, ctx.getBarWidthAsDouble());
      double maxLenPx = Math.min(b.width, profWidthBars * barWidthPx);

      double tickHeightPx = ctx.getTickHeight();
      // Fall back to a sane pixel height if the SDK reports a non-positive tick height.
      if (!(tickHeightPx > 0)) tickHeightPx = 1.0;
      int halfH = Math.max(2, (int) Math.round(profHeightTicks * tickHeightPx / 2.0));

      int rightX = b.x + b.width;

      gc.setStroke(new BasicStroke(1f));
      for (DrawProf dp : drawProfile) {
        int yPix = ctx.translateValue(dp.price);
        if (yPix < b.y - halfH || yPix > b.y + b.height + halfH) continue;

        int barLenPx = (int) Math.round(dp.frac * maxLenPx);
        if (barLenPx <= 0) continue;
        if (barLenPx > b.width) barLenPx = b.width;

        int x = rightX - barLenPx;
        gc.setColor(dp.color);
        gc.fillRect(x, yPix - halfH, barLenPx, halfH * 2);
        gc.drawRect(x, yPix - halfH, barLenPx, halfH * 2);
      }
    }

    private void drawDelayedBanner(Graphics2D gc, Rectangle b)
    {
      String msg = "DELAYED DATA (3 days) — Subscribe at tradelikeadealer.com for live levels";
      gc.setFont(new Font("Dialog", Font.PLAIN, 11));
      FontMetrics fm = gc.getFontMetrics();
      int w = fm.stringWidth(msg) + 12;
      int x = b.x + b.width - w - 6;
      int y = b.y + 6;
      gc.setColor(new Color(0, 0, 0, 160));
      gc.fillRect(x, y, w, fm.getHeight() + 4);
      gc.setColor(new Color(255, 165, 0));
      gc.drawString(msg, x + 6, y + 2 + fm.getAscent());
    }
  }

  // ---- figure helpers --------------------------------------------------------------------------

  private Color colorFor(LevelEntry lvl, double y, double spot)
  {
    switch (lvl.type) {
      case "CW": {
        boolean flipped = y < spot;
        return flipped ? posColor : negColor;
      }
      case "PW": {
        boolean flipped = y > spot;
        return flipped ? negColor : posColor;
      }
      case "ZG": return new Color(0x69, 0x69, 0x69); // DarkGray
      case "MP": return new Color(0xff, 0x00, 0x00); // Red
      case "EH":
      case "EL": return new Color(0x1e, 0x90, 0xff); // DodgerBlue
      case "VH":
      case "VL": return new Color(0x80, 0x80, 0x80); // Gray
      default:
        if (isStructure(lvl.type)) return new Color(0x69, 0x69, 0x69); // DarkGray
        return new Color(0x80, 0x80, 0x80); // Gray
    }
  }

  private static Stroke strokeFor(boolean gex, boolean sys, int width)
  {
    if (gex) return new BasicStroke(width); // solid
    if (sys) return new BasicStroke(width, BasicStroke.CAP_BUTT, BasicStroke.JOIN_MITER,
        10f, new float[] {6f, 4f}, 0f); // dash
    return new BasicStroke(width, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND,
        10f, new float[] {1f, 4f}, 0f); // dot
  }

  private Font labelFont(Defaults defaults)
  {
    int size = clamp(getSettings().getInteger(LABEL_SIZE, 11), 6, 50);
    Font base = (defaults != null) ? defaults.getFont() : null;
    return (base != null) ? base.deriveFont((float) size) : new Font("Arial", Font.PLAIN, size);
  }

  private static Color contrastColor(Color bg)
  {
    double lum = (0.299 * bg.getRed() + 0.587 * bg.getGreen() + 0.114 * bg.getBlue()) / 255.0;
    return lum > 0.55 ? Color.BLACK : Color.WHITE;
  }

  private static int clamp(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
}
