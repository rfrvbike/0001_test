export function mapJQuantsMockToStockData(raw, options = {}) {
  const price = Number(raw.price);
  const previousClose = Number(raw.previousClose);
  const change = price - previousClose;
  const changePercent = previousClose > 0 ? (change / previousClose) * 100 : 0;

  return {
    code: raw.code,
    name: raw.name,
    market: raw.market,
    dataSource: "J_QUANTS_MOCK",
    dataSourceLabel: options.dataSourceLabel || "J-Quants接続準備用モック",
    lastUpdated: raw.lastUpdated || "J-Quants mock data",
    isMock: true,
    isTradableData: false,
    tradableDataLabel: options.tradableDataLabel || "実API未接続",
    price,
    previousClose,
    change,
    changePercent,
    volume: Number(raw.volume),
    averageVolume20d: Number(raw.averageVolume20d),
    ma25: Number(raw.ma25),
    ma75: Number(raw.ma75),
    rsi: Number(raw.rsi),
    high52w: Number(raw.high52w),
    highYtd: Number(raw.highYtd),
    latestEarningsDate: raw.latestEarningsDate || "",
    nextEarningsDate: raw.nextEarningsDate || "",
    earningsTrend: raw.earningsTrend || "STABLE",
    hasUpwardRevision: Boolean(raw.hasUpwardRevision),
    hasDownwardRevision: Boolean(raw.hasDownwardRevision),
    hasDividendIncrease: Boolean(raw.hasDividendIncrease),
    hasBuyback: Boolean(raw.hasBuyback),
    importantDisclosures: Array.isArray(raw.importantDisclosures) ? raw.importantDisclosures : [],
    policyThemes: Array.isArray(raw.policyThemes) ? raw.policyThemes : [],
    policyRelationType: raw.policyRelationType || "NONE",
    policyDescription: raw.policyDescription || "J-Quants接続準備用のサンプルです",
    candlePattern: raw.candlePattern || "NORMAL",
    isBeforeEarnings: Boolean(raw.isBeforeEarnings)
  };
}

export function mapJQuantsDailyBarsToStockData(rawResult, options = {}) {
  const code = String(options.code || "").trim();
  const rawRows = extractDailyBars(rawResult);
  const rows = rawRows
    .map(normalizeDailyBar)
    .filter((bar) => bar.date && Number.isFinite(bar.close))
    .sort((a, b) => a.date.localeCompare(b.date));
  const calculationWarnings = [];

  if (!rows.length) {
    return {
      stockData: buildEmptyMappedStockData(code),
      calculationWarnings: ["J-Quants日足データが空のため変換できませんでした"],
      debugInfo: buildDebugInfo({ rawRows, rows, latest: null, averageVolume20d: null, ma25: null, ma75: null, rsi: null })
    };
  }

  const latest = rows[rows.length - 1];
  const previous = rows.length >= 2 ? rows[rows.length - 2] : null;
  const closes = rows.map((row) => row.close).filter(Number.isFinite);
  const highs = rows.map((row) => row.high).filter(Number.isFinite);
  const volumes = rows.map((row) => row.volume).filter(Number.isFinite);
  const { change, changePercent } = calculateChange(latest.close, previous?.close ?? null);
  const averageVolume20d = rows.length >= 20 ? average(volumes.slice(-20)) : null;
  const ma25 = calculateSimpleMovingAverage(closes, 25);
  const ma75 = calculateSimpleMovingAverage(closes, 75);
  const rsi = calculateRsiFromCloses(closes, 14);
  const high52w = rows.length >= 250 ? Math.max(...highs.slice(-250)) : null;
  const year = latest.date.slice(0, 4);
  const ytdRows = rows.filter((row) => row.date.startsWith(year));
  const highYtd = ytdRows.length >= 20 ? Math.max(...ytdRows.map((row) => row.high).filter(Number.isFinite)) : null;

  if (averageVolume20d == null) calculationWarnings.push("出来高データを十分に取得できなかったためaverageVolume20dは未計算です");
  if (ma25 == null) calculationWarnings.push("終値データを十分に取得できなかったためma25は未計算です");
  if (ma75 == null) calculationWarnings.push("終値データを十分に取得できなかったためma75は未計算です");
  if (rsi == null) calculationWarnings.push("RSI計算に必要な終値データが不足しています");
  if (high52w == null) calculationWarnings.push("52週高値を計算するには十分な期間のデータが必要です");
  if (highYtd == null) calculationWarnings.push("年初来高値を計算するには十分な期間のデータが必要です");

  return {
    stockData: {
      code: code || latest.code || "",
      name: options.name || `${code || latest.code} J-Quants確認用`,
      market: "",
      dataSource: "J_QUANTS_MAPPED",
      dataSourceLabel: "J-Quants実データ変換確認",
      lastUpdated: latest.date,
      isMock: false,
      isTradableData: false,
      tradableDataLabel: "J-Quants実データ確認用",
      price: latest.close,
      previousClose: previous?.close ?? null,
      change,
      changePercent,
      volume: latest.volume,
      averageVolume20d,
      ma25,
      ma75,
      rsi,
      high52w,
      highYtd,
      latestEarningsDate: "",
      nextEarningsDate: "",
      earningsTrend: "UNKNOWN",
      hasUpwardRevision: false,
      hasDownwardRevision: false,
      hasDividendIncrease: false,
      hasBuyback: false,
      importantDisclosures: ["J-Quants日足データから変換した確認用データです"],
      policyThemes: [],
      policyRelationType: "NONE",
      policyDescription: "国策テーマ判定は未接続です",
      candlePattern: detectSimpleCandlePattern(latest),
      isBeforeEarnings: false
    },
    calculationWarnings,
    debugInfo: buildDebugInfo({ rawRows, rows, latest, averageVolume20d, ma25, ma75, rsi })
  };
}

export function calculateSimpleMovingAverage(values, period) {
  const numbers = values.filter(Number.isFinite);
  if (numbers.length < period) return null;
  return round(average(numbers.slice(-period)));
}

export function calculateRsiFromCloses(closes, period = 14) {
  const numbers = closes.filter(Number.isFinite);
  if (numbers.length < period + 1) return null;
  const recent = numbers.slice(-(period + 1));
  let gains = 0;
  let losses = 0;
  for (let index = 1; index < recent.length; index += 1) {
    const diff = recent[index] - recent[index - 1];
    if (diff >= 0) gains += diff;
    else losses += Math.abs(diff);
  }
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return round(100 - (100 / (1 + rs)));
}

export function calculateChange(price, previousClose) {
  if (!Number.isFinite(price) || !Number.isFinite(previousClose) || previousClose === 0) {
    return { change: null, changePercent: null };
  }
  const change = price - previousClose;
  return {
    change: round(change),
    changePercent: round((change / previousClose) * 100)
  };
}

export function detectSimpleCandlePattern(latestBar) {
  if (!latestBar || !Number.isFinite(latestBar.open) || !Number.isFinite(latestBar.close)) return "NORMAL";
  const range = Number.isFinite(latestBar.high) && Number.isFinite(latestBar.low) ? latestBar.high - latestBar.low : 0;
  if (range <= 0) return "NORMAL";
  const bodyRatio = Math.abs(latestBar.close - latestBar.open) / range;
  if (bodyRatio < 0.15) return "NORMAL";
  return latestBar.close > latestBar.open ? "BULLISH" : "BEARISH";
}

function extractDailyBars(rawResult) {
  if (Array.isArray(rawResult?.data)) return rawResult.data;
  if (Array.isArray(rawResult?.sampleRows)) return rawResult.sampleRows;
  if (Array.isArray(rawResult)) return rawResult;
  return [];
}

function normalizeDailyBar(row) {
  const open = pickNumber(row, ["AdjOpen", "AdjO", "O", "Open", "open"]);
  const high = pickNumber(row, ["AdjHigh", "AdjH", "H", "High", "high"]);
  const low = pickNumber(row, ["AdjLow", "AdjL", "L", "Low", "low"]);
  const close = pickNumber(row, ["AdjClose", "AdjC", "C", "Close", "close"]);
  const volume = pickNumber(row, ["AdjVolume", "AdjVo", "AdjV", "V", "Vo", "Volume", "volume"]);
  return {
    date: String(row.Date || row.date || ""),
    code: String(row.Code || row.code || ""),
    open: open.value,
    high: high.value,
    low: low.value,
    close: close.value,
    volume: volume.value,
    fieldUsage: {
      open: open.field,
      high: high.field,
      low: low.field,
      close: close.field,
      volume: volume.field
    }
  };
}

function pickNumber(row, fields) {
  for (const field of fields) {
    if (!(field in row)) continue;
    const value = toNumberOrNull(row[field]);
    if (value != null) return { field, value };
  }
  return { field: null, value: null };
}

function buildDebugInfo({ rawRows, rows, latest, averageVolume20d, ma25, ma75, rsi }) {
  const validVolumeCount = rows.filter((row) => Number.isFinite(row.volume)).length;
  const fieldCounts = countUsedFields(rows);
  return {
    rawRowCount: rawRows.length,
    closeFieldUsed: latest?.fieldUsage?.close || mostUsedField(fieldCounts.close),
    volumeFieldUsed: latest?.fieldUsage?.volume || mostUsedField(fieldCounts.volume),
    openFieldUsed: latest?.fieldUsage?.open || mostUsedField(fieldCounts.open),
    highFieldUsed: latest?.fieldUsage?.high || mostUsedField(fieldCounts.high),
    lowFieldUsed: latest?.fieldUsage?.low || mostUsedField(fieldCounts.low),
    validCloseCount: rows.length,
    validVolumeCount,
    canCalculateAverageVolume20d: averageVolume20d != null || validVolumeCount >= 20,
    canCalculateMa25: ma25 != null || rows.length >= 25,
    canCalculateMa75: ma75 != null || rows.length >= 75,
    canCalculateRsi: rsi != null || rows.length >= 15
  };
}

function countUsedFields(rows) {
  return rows.reduce((counts, row) => {
    for (const key of ["open", "high", "low", "close", "volume"]) {
      const field = row.fieldUsage?.[key];
      if (!field) continue;
      counts[key][field] = (counts[key][field] || 0) + 1;
    }
    return counts;
  }, { open: {}, high: {}, low: {}, close: {}, volume: {} });
}

function mostUsedField(counts) {
  const entries = Object.entries(counts || {});
  if (!entries.length) return null;
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}

function buildEmptyMappedStockData(code) {
  return {
    code,
    name: `${code} J-Quants確認用`,
    market: "",
    dataSource: "J_QUANTS_MAPPED",
    dataSourceLabel: "J-Quants実データ変換確認",
    lastUpdated: "",
    isMock: false,
    isTradableData: false,
    tradableDataLabel: "J-Quants実データ確認用",
    price: null,
    previousClose: null,
    change: null,
    changePercent: null,
    volume: null,
    averageVolume20d: null,
    ma25: null,
    ma75: null,
    rsi: null,
    high52w: null,
    highYtd: null,
    latestEarningsDate: "",
    nextEarningsDate: "",
    earningsTrend: "UNKNOWN",
    hasUpwardRevision: false,
    hasDownwardRevision: false,
    hasDividendIncrease: false,
    hasBuyback: false,
    importantDisclosures: ["J-Quants日足データから変換した確認用データです"],
    policyThemes: [],
    policyRelationType: "NONE",
    policyDescription: "国策テーマ判定は未接続です",
    candlePattern: "NORMAL",
    isBeforeEarnings: false
  };
}

function toNumberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function average(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value) {
  return Number.isFinite(value) ? Math.round(value * 100) / 100 : null;
}
