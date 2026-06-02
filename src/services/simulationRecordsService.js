export const SIMULATION_RECORDS_KEY = "stockAnalyzer.simulationRecords";
export const SIMULATION_RECORDS_MAX = 100;
export const SIMULATION_RECORDS_CSV_NOTICE = "これは実売買ではなく、仮記録の検証用データです。注文・約定・実損益ではありません。";

const CSV_HEADERS = [
  "recordedAt",
  "analysisDate",
  "code",
  "name",
  "market",
  "sector",
  "recordedPrice",
  "lastCheckedPrice",
  "referenceChange",
  "referenceChangePercent",
  "lastCheckedAt",
  "dataSource",
  "isMock",
  "decisionLabel",
  "overallStatus",
  "totalScore",
  "buyScore",
  "financialScore",
  "themeCount",
  "preTradeStatus",
  "memo",
  "resultMemo",
  "status",
  "notice"
];

const FORBIDDEN_KEYS = new Set([
  "apiKey",
  "JQUANTS_API_KEY",
  "headers",
  "rawRows",
  "debugInfo",
  "financialSummary",
  "structuredSummary",
  "aiSummary",
  "themeSummary",
  "preTradeCheck",
  "scoreResult",
  "indicators"
]);

export function buildSimulationRecordFiltersDefault() {
  return {
    datePreset: "all",
    dateFrom: "",
    dateTo: "",
    keyword: "",
    decisionLabel: "all",
    diffStatus: "all"
  };
}

export function filterSimulationRecords(records, filters = {}) {
  const safeFilters = {
    ...buildSimulationRecordFiltersDefault(),
    ...(filters || {})
  };
  return (Array.isArray(records) ? records : [])
    .map(normalizeSimulationRecord)
    .filter(Boolean)
    .filter((record) => matchesSimulationRecordDateRange(record, safeFilters))
    .filter((record) => matchesSimulationRecordKeyword(record, safeFilters.keyword))
    .filter((record) => safeFilters.decisionLabel === "all" || record.decisionLabel === safeFilters.decisionLabel)
    .filter((record) => safeFilters.diffStatus === "all" || getSimulationRecordDiffStatus(record) === safeFilters.diffStatus);
}

export function summarizeSimulationRecords(records) {
  const safeRecords = (Array.isArray(records) ? records : [])
    .map(normalizeSimulationRecord)
    .filter(Boolean);
  const diffRecords = safeRecords.filter((record) => Number.isFinite(numberOrNull(record.lastCheckedChangePercent)));
  const positiveRecords = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "positive");
  const negativeRecords = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "negative");
  const neutralRecords = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "neutral");
  const unknownRecords = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "unknown");
  const diffPercents = diffRecords.map((record) => numberOrNull(record.lastCheckedChangePercent)).filter(Number.isFinite);
  return {
    totalRecords: safeRecords.length,
    positiveCount: positiveRecords.length,
    negativeCount: negativeRecords.length,
    neutralCount: neutralRecords.length,
    unknownCount: unknownRecords.length,
    averageChangePercent: diffPercents.length
      ? roundNumber(diffPercents.reduce((sum, value) => sum + value, 0) / diffPercents.length, 2)
      : null,
    maxPositiveChangePercent: diffPercents.length ? roundNumber(Math.max(...diffPercents), 2) : null,
    maxNegativeChangePercent: diffPercents.length ? roundNumber(Math.min(...diffPercents), 2) : null
  };
}

export function summarizeSimulationRecordsByMonth(records) {
  return buildSimulationGroupSummary(records, getSimulationRecordMonth, (a, b) => b.key.localeCompare(a.key));
}

export function summarizeSimulationRecordsByStock(records) {
  return buildSimulationGroupSummary(records, getSimulationRecordStockKey, (a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return b.averageChangePercentForSort - a.averageChangePercentForSort;
  });
}

export function summarizeSimulationRecordsByDecision(records) {
  return buildSimulationGroupSummary(records, getSimulationRecordDecisionKey, (a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return a.label.localeCompare(b.label, "ja");
  });
}

export function buildSimulationGroupSummary(records, groupKey, sortFn) {
  const safeRecords = (Array.isArray(records) ? records : [])
    .map(normalizeSimulationRecord)
    .filter(Boolean);
  const getGroup = typeof groupKey === "function" ? groupKey : () => ({ key: "unknown", label: "未分類" });
  const groups = new Map();
  safeRecords.forEach((record) => {
    const group = getGroup(record) || {};
    const key = normalizeText(group.key || "unknown") || "unknown";
    const label = normalizeText(group.label || key) || "未分類";
    if (!groups.has(key)) groups.set(key, { key, label, records: [] });
    groups.get(key).records.push(record);
  });
  const summaries = Array.from(groups.values()).map((group) => {
    const stats = calculateSimulationSummaryStats(group.records);
    return {
      key: group.key,
      label: group.label,
      ...stats,
      sampleCodes: Array.from(new Set(group.records.map((record) => record.code).filter(Boolean))).slice(0, 5),
      latestRecordedAt: group.records
        .map((record) => normalizeText(record.recordedAt))
        .filter(Boolean)
        .sort((a, b) => b.localeCompare(a))[0] || "",
      averageChangePercentForSort: stats.averageChangePercent ?? -Infinity
    };
  });
  return summaries.sort(sortFn || ((a, b) => b.count - a.count));
}

export function calculateSimulationSummaryStats(records) {
  const safeRecords = (Array.isArray(records) ? records : [])
    .map(normalizeSimulationRecord)
    .filter(Boolean);
  const checkedRecords = safeRecords.filter((record) => Number.isFinite(numberOrNull(record.lastCheckedChangePercent)));
  const positiveCount = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "positive").length;
  const negativeCount = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "negative").length;
  const flatCount = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "neutral").length;
  const uncheckedCount = safeRecords.filter((record) => getSimulationRecordDiffStatus(record) === "unknown").length;
  const percents = checkedRecords.map((record) => numberOrNull(record.lastCheckedChangePercent)).filter(Number.isFinite);
  return {
    count: safeRecords.length,
    positiveCount,
    negativeCount,
    flatCount,
    uncheckedCount,
    checkedCount: checkedRecords.length,
    averageChangePercent: percents.length
      ? roundNumber(percents.reduce((sum, value) => sum + value, 0) / percents.length, 2)
      : null,
    maxPositiveChangePercent: percents.length ? roundNumber(Math.max(...percents), 2) : null,
    maxNegativeChangePercent: percents.length ? roundNumber(Math.min(...percents), 2) : null
  };
}

export function formatSimulationSummaryPercent(value) {
  const number = numberOrNull(value);
  if (!Number.isFinite(number)) return "未計算";
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

export function getSimulationRecordMonth(record) {
  const date = parseRecordDate(record);
  if (!date) return { key: "unknown", label: "日付不明" };
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const key = `${year}-${month}`;
  return { key, label: key };
}

export function getSimulationRecordStockKey(record) {
  const safe = normalizeSimulationRecord(record);
  if (!safe) return { key: "unknown", label: "銘柄不明" };
  const code = normalizeText(safe.code || "unknown");
  const name = normalizeText(safe.name || "");
  return {
    key: code || "unknown",
    label: `${code}${name ? ` ${name}` : ""}`.trim() || "銘柄不明"
  };
}

export function getSimulationRecordDecisionKey(record) {
  const label = normalizeText(record?.decisionLabel || "データ不足");
  return { key: label || "データ不足", label: label || "データ不足" };
}

export function getSimulationRecordDiffStatus(record) {
  const change = numberOrNull(record?.lastCheckedChange);
  const percent = numberOrNull(record?.lastCheckedChangePercent);
  if (!Number.isFinite(change) || !Number.isFinite(percent)) return "unknown";
  if (change > 0) return "positive";
  if (change < 0) return "negative";
  return "neutral";
}

export function matchesSimulationRecordDateRange(record, filters = {}) {
  const safeFilters = {
    ...buildSimulationRecordFiltersDefault(),
    ...(filters || {})
  };
  const targetDate = parseRecordDate(record);
  if (!targetDate) return safeFilters.datePreset === "all" && !safeFilters.dateFrom && !safeFilters.dateTo;
  const today = startOfDay(new Date());
  let from = null;
  let to = endOfDay(today);
  if (safeFilters.datePreset === "today") {
    from = today;
  } else if (safeFilters.datePreset === "7d") {
    from = addDays(today, -6);
  } else if (safeFilters.datePreset === "30d") {
    from = addDays(today, -29);
  } else if (safeFilters.datePreset === "custom") {
    from = parseInputDate(safeFilters.dateFrom, "start");
    to = parseInputDate(safeFilters.dateTo, "end");
  } else {
    from = parseInputDate(safeFilters.dateFrom, "start");
    to = parseInputDate(safeFilters.dateTo, "end");
  }
  if (from && targetDate < from) return false;
  if (to && targetDate > to) return false;
  return true;
}

export function matchesSimulationRecordKeyword(record, keyword = "") {
  const query = normalizeText(keyword).normalize("NFKC").toLowerCase();
  if (!query) return true;
  const haystack = [
    record?.code,
    record?.name,
    record?.market,
    record?.sector,
    record?.memo,
    record?.resultMemo
  ].map((value) => normalizeText(value).normalize("NFKC").toLowerCase()).join(" ");
  return haystack.includes(query);
}

export function getSimulationDecisionLabels(records) {
  const labels = new Set();
  (Array.isArray(records) ? records : []).forEach((record) => {
    const label = normalizeText(record?.decisionLabel);
    if (label) labels.add(label);
  });
  return Array.from(labels).sort((a, b) => a.localeCompare(b, "ja"));
}

export function getSimulationRecords(storage = getStorage()) {
  if (!storage) return [];
  try {
    const raw = storage.getItem(SIMULATION_RECORDS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalizeSimulationRecord).filter(Boolean).slice(0, SIMULATION_RECORDS_MAX);
  } catch {
    return [];
  }
}

export function saveSimulationRecords(records, storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable.", records: [] };
  try {
    const safeRecords = (Array.isArray(records) ? records : [])
      .map(normalizeSimulationRecord)
      .filter(Boolean)
      .sort((a, b) => String(b.recordedAt).localeCompare(String(a.recordedAt)))
      .slice(0, SIMULATION_RECORDS_MAX);
    storage.setItem(SIMULATION_RECORDS_KEY, JSON.stringify(safeRecords));
    return { ok: true, records: safeRecords, count: safeRecords.length };
  } catch (error) {
    return { ok: false, error: error.message, records: [] };
  }
}

export function addSimulationRecord(record, storage = getStorage()) {
  const current = getSimulationRecords(storage);
  const safe = normalizeSimulationRecord(record);
  if (!safe) return { ok: false, error: "シミュレーション記録を作成できませんでした。", records: current };
  const next = [safe, ...current.filter((item) => item.id !== safe.id)].slice(0, SIMULATION_RECORDS_MAX);
  return saveSimulationRecords(next, storage);
}

export function removeSimulationRecord(id, storage = getStorage()) {
  const current = getSimulationRecords(storage);
  return saveSimulationRecords(current.filter((record) => record.id !== id), storage);
}

export function updateSimulationRecord(id, updates, storage = getStorage()) {
  const current = getSimulationRecords(storage);
  const next = current.map((record) => {
    if (record.id !== id) return record;
    return normalizeSimulationRecord({
      ...record,
      memo: updates?.memo ?? record.memo,
      resultMemo: updates?.resultMemo ?? record.resultMemo,
      status: updates?.status ?? record.status,
      lastCheckedAt: updates?.lastCheckedAt ?? record.lastCheckedAt,
      lastCheckedPrice: updates?.lastCheckedPrice ?? record.lastCheckedPrice,
      lastCheckedChange: updates?.lastCheckedChange ?? record.lastCheckedChange,
      lastCheckedChangePercent: updates?.lastCheckedChangePercent ?? record.lastCheckedChangePercent,
      lastCheckedDataSource: updates?.lastCheckedDataSource ?? record.lastCheckedDataSource,
      lastCheckedIsMock: updates?.lastCheckedIsMock ?? record.lastCheckedIsMock
    });
  });
  return saveSimulationRecords(next, storage);
}

export function updateSimulationRecordCheckResult(id, currentStockData, storage = getStorage()) {
  const current = getSimulationRecords(storage);
  const target = current.find((record) => record.id === id);
  if (!target) return { ok: false, error: "シミュレーション記録が見つかりません。", records: current };
  const checkResult = buildSimulationCheckResult(target, currentStockData);
  return updateSimulationRecord(id, {
    lastCheckedAt: checkResult.checkedAt,
    lastCheckedPrice: checkResult.currentPrice,
    lastCheckedChange: checkResult.priceDiff,
    lastCheckedChangePercent: checkResult.priceDiffPercent,
    lastCheckedDataSource: checkResult.dataSource,
    lastCheckedIsMock: checkResult.isMock
  }, storage);
}

export function clearSimulationRecords(storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    storage.removeItem(SIMULATION_RECORDS_KEY);
    return { ok: true, records: [] };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function buildSimulationRecordsCsv(records, options = {}) {
  const safeRecords = (Array.isArray(records) ? records : [])
    .map(normalizeSimulationRecord)
    .filter(Boolean);
  const headers = options.headers || CSV_HEADERS;
  const rows = safeRecords.map((record) => formatSimulationRecordCsvRow(record, headers));
  const csvBody = [headers.join(","), ...rows].join("\r\n");
  return `${options.includeBom === false ? "" : "\uFEFF"}${csvBody}\r\n`;
}

export function downloadSimulationRecordsCsv(records, options = {}) {
  const safeRecords = Array.isArray(records) ? records : [];
  if (!safeRecords.length) {
    return { ok: false, error: "CSV出力できるシミュレーション記録がありません。" };
  }
  const csvText = buildSimulationRecordsCsv(safeRecords, options);
  const filename = options.filename || buildSimulationRecordsCsvFilename(options.date);
  try {
    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    return { ok: true, filename, count: safeRecords.length };
  } catch (error) {
    return { ok: false, error: error.message || "CSV出力に失敗しました。" };
  }
}

export function sanitizeSimulationRecordForCsv(record) {
  const safe = normalizeSimulationRecord(record);
  if (!safe) return null;
  return {
    recordedAt: safe.recordedAt,
    analysisDate: safe.analysisDate,
    code: safe.code,
    name: safe.name,
    market: safe.market,
    sector: safe.sector,
    recordedPrice: safe.price,
    lastCheckedPrice: safe.lastCheckedPrice,
    referenceChange: safe.lastCheckedChange,
    referenceChangePercent: safe.lastCheckedChangePercent,
    lastCheckedAt: safe.lastCheckedAt,
    dataSource: safe.dataSource,
    isMock: safe.isMock,
    decisionLabel: safe.decisionLabel,
    overallStatus: safe.overallStatus,
    totalScore: safe.totalScore,
    buyScore: safe.buyScore,
    financialScore: safe.financialScore,
    themeCount: safe.themeCount,
    preTradeStatus: safe.preTradeStatus,
    memo: safe.memo,
    resultMemo: safe.resultMemo,
    status: safe.status,
    notice: SIMULATION_RECORDS_CSV_NOTICE
  };
}

export function formatSimulationRecordCsvRow(record, headers = CSV_HEADERS) {
  const safe = sanitizeSimulationRecordForCsv(record);
  if (!safe) return headers.map(() => "").join(",");
  return headers.map((header) => escapeCsvValue(safe[header])).join(",");
}

export function escapeCsvValue(value) {
  if (value === null || value === undefined) return "";
  const text = String(value).replaceAll('"', '""');
  return `"${text}"`;
}

export function buildSimulationRecordsCsvFilename(date = new Date()) {
  const parsed = date instanceof Date ? date : new Date(date);
  const safeDate = Number.isNaN(parsed.getTime()) ? new Date() : parsed;
  const year = safeDate.getFullYear();
  const month = String(safeDate.getMonth() + 1).padStart(2, "0");
  const day = String(safeDate.getDate()).padStart(2, "0");
  return `simulation-records-${year}${month}${day}.csv`;
}

export function buildSimulationRecordFromAnalysis(stockData, options = {}) {
  const stock = stockData?.stock || stockData || {};
  const scoreResult = options.scoreResult || stockData?.scoreResult || {};
  const structuredSummary = options.structuredSummary || stockData?.structuredSummary || stock.structuredSummary || {};
  const preTradeCheck = options.preTradeCheck || stockData?.preTradeCheck || stock.preTradeCheck || {};
  const now = options.now ? new Date(options.now) : new Date();
  const code = normalizeText(stock.code);
  return normalizeSimulationRecord({
    id: options.id || buildSimulationId(code, now),
    code,
    name: stock.name,
    market: stock.market,
    sector: stock.sector,
    recordedAt: now.toISOString(),
    analysisDate: now.toISOString().slice(0, 10),
    price: stock.price,
    previousClose: stock.previousClose,
    change: stock.change,
    changePercent: stock.changePercent,
    dataSource: stock.dataSource,
    isMock: stock.isMock,
    decisionLabel: structuredSummary?.decision?.label || scoreResult.signal || "",
    overallStatus: preTradeCheck?.overallStatus || "",
    totalScore: scoreResult.totalScore,
    buyScore: scoreResult.buyScore,
    financialScore: scoreResult.financialScore ?? stock.financialSignals?.financialScore ?? 0,
    themeCount: Array.isArray(stock.themeSummary?.themes) ? stock.themeSummary.themes.length : 0,
    preTradeStatus: preTradeCheck?.overallStatus || "",
    memo: options.memo || "",
    resultMemo: options.resultMemo || "",
    status: options.status || "watching"
  });
}

export function buildSimulationCheckResult(record, stockData, options = {}) {
  const currentPrice = numberOrNull(stockData?.price);
  const diff = calculateSimulationPriceDiff(record, currentPrice);
  const checkedAt = options.now ? new Date(options.now).toISOString() : new Date().toISOString();
  return {
    id: normalizeText(record?.id || ""),
    code: normalizeText(record?.code || stockData?.code || ""),
    checkedAt,
    recordedPrice: numberOrNull(record?.price),
    currentPrice,
    priceDiff: diff.priceDiff,
    priceDiffPercent: diff.priceDiffPercent,
    calculable: diff.calculable,
    reason: diff.reason,
    dataSource: normalizeText(stockData?.dataSource || ""),
    isMock: Boolean(stockData?.isMock)
  };
}

export function calculateSimulationPriceDiff(record, currentPrice) {
  const recordedPrice = numberOrNull(record?.price);
  const checkedPrice = numberOrNull(currentPrice);
  if (!isValidRecordedPrice(recordedPrice)) {
    return {
      calculable: false,
      priceDiff: null,
      priceDiffPercent: null,
      reason: "recorded_price_unavailable"
    };
  }
  if (!Number.isFinite(checkedPrice)) {
    return {
      calculable: false,
      priceDiff: null,
      priceDiffPercent: null,
      reason: "current_price_unavailable"
    };
  }
  const priceDiff = roundNumber(checkedPrice - recordedPrice, 2);
  const priceDiffPercent = roundNumber((priceDiff / recordedPrice) * 100, 2);
  return {
    calculable: true,
    priceDiff,
    priceDiffPercent,
    reason: ""
  };
}

export function formatSimulationDiff(diff) {
  if (!diff?.calculable) return "差分：未計算";
  const amount = `${diff.priceDiff >= 0 ? "+" : ""}${diff.priceDiff}`;
  const percent = `${diff.priceDiffPercent >= 0 ? "+" : ""}${diff.priceDiffPercent.toFixed(2)}%`;
  return `${amount}円（${percent}）`;
}

export function isValidRecordedPrice(price) {
  const value = numberOrNull(price);
  return Number.isFinite(value) && value > 0;
}

export function normalizeSimulationRecord(record) {
  if (!record || typeof record !== "object") return null;
  const safe = {};
  Object.keys(record).forEach((key) => {
    if (!FORBIDDEN_KEYS.has(key)) safe[key] = record[key];
  });
  const code = normalizeText(safe.code).normalize("NFKC").toUpperCase();
  if (!code) return null;
  return {
    id: normalizeText(safe.id) || buildSimulationId(code),
    code,
    name: normalizeText(safe.name || code),
    market: normalizeText(safe.market || ""),
    sector: normalizeText(safe.sector || ""),
    recordedAt: normalizeText(safe.recordedAt || new Date().toISOString()),
    analysisDate: normalizeText(safe.analysisDate || normalizeText(safe.recordedAt).slice(0, 10) || ""),
    price: numberOrNull(safe.price),
    previousClose: numberOrNull(safe.previousClose),
    change: numberOrNull(safe.change),
    changePercent: numberOrNull(safe.changePercent),
    dataSource: normalizeText(safe.dataSource || ""),
    isMock: Boolean(safe.isMock),
    decisionLabel: normalizeText(safe.decisionLabel || ""),
    overallStatus: normalizeText(safe.overallStatus || ""),
    totalScore: numberOrNull(safe.totalScore),
    buyScore: numberOrNull(safe.buyScore),
    financialScore: numberOrNull(safe.financialScore),
    themeCount: numberOrNull(safe.themeCount) ?? 0,
    preTradeStatus: normalizeText(safe.preTradeStatus || ""),
    memo: normalizeText(safe.memo || ""),
    resultMemo: normalizeText(safe.resultMemo || ""),
    status: normalizeStatus(safe.status),
    lastCheckedAt: normalizeText(safe.lastCheckedAt || ""),
    lastCheckedPrice: numberOrNull(safe.lastCheckedPrice),
    lastCheckedChange: numberOrNull(safe.lastCheckedChange),
    lastCheckedChangePercent: numberOrNull(safe.lastCheckedChangePercent),
    lastCheckedDataSource: normalizeText(safe.lastCheckedDataSource || ""),
    lastCheckedIsMock: Boolean(safe.lastCheckedIsMock)
  };
}

function buildSimulationId(code, date = new Date()) {
  const stamp = date.toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const random = Math.random().toString(36).slice(2, 8);
  return `sim_${stamp}_${code || "unknown"}_${random}`;
}

function normalizeStatus(status) {
  const value = normalizeText(status);
  return ["watching", "review_later", "simulated_entry", "closed", "archived"].includes(value)
    ? value
    : "watching";
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function roundNumber(value, digits = 2) {
  if (!Number.isFinite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function parseRecordDate(record) {
  const source = normalizeText(record?.recordedAt || record?.analysisDate);
  if (!source) return null;
  const date = new Date(source);
  return Number.isNaN(date.getTime()) ? null : date;
}

function parseInputDate(value, boundary = "start") {
  const text = normalizeText(value);
  if (!text) return null;
  const date = new Date(`${text}T${boundary === "end" ? "23:59:59.999" : "00:00:00.000"}`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function endOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function normalizeText(value) {
  return String(value ?? "").trim();
}

function getStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}
