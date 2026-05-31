export const RECENT_STOCKS_KEY = "stockAnalyzer.recentStocks";
export const RECENT_STOCKS_MAX = 20;

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
  "scoreResult",
  "indicators"
]);

export function getRecentStocks(storage = getStorage()) {
  if (!storage) return [];
  try {
    const raw = storage.getItem(RECENT_STOCKS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((stock) => normalizeRecentStock(stock))
      .filter(Boolean)
      .sort((a, b) => String(b.viewedAt || "").localeCompare(String(a.viewedAt || "")))
      .slice(0, RECENT_STOCKS_MAX);
  } catch {
    return [];
  }
}

export function saveRecentStocks(recentStocks, storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    const normalized = dedupeRecentStocks(Array.isArray(recentStocks) ? recentStocks : [])
      .slice(0, RECENT_STOCKS_MAX);
    storage.setItem(RECENT_STOCKS_KEY, JSON.stringify(normalized));
    return { ok: true, recentStocks: normalized };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function addRecentStock(stock, storage = getStorage()) {
  const normalized = normalizeRecentStock({
    ...stock,
    viewedAt: new Date().toISOString()
  });
  if (!normalized) return { ok: false, error: "Invalid recent stock." };
  const current = getRecentStocks(storage).filter((item) => item.code !== normalized.code);
  return saveRecentStocks([normalized, ...current], storage);
}

export function removeRecentStock(code, storage = getStorage()) {
  const normalizedCode = normalizeRecentCode(code);
  if (!normalizedCode) return { ok: false, error: "Invalid recent stock code." };
  return saveRecentStocks(
    getRecentStocks(storage).filter((stock) => stock.code !== normalizedCode),
    storage
  );
}

export function clearRecentStocks(storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    storage.removeItem(RECENT_STOCKS_KEY);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function normalizeRecentStock(stock) {
  if (!stock || typeof stock !== "object") return null;
  const code = normalizeRecentCode(stock.code || stock.LocalCode || stock.Code);
  if (!code) return null;
  const safe = {};
  Object.keys(stock).forEach((key) => {
    if (!FORBIDDEN_KEYS.has(key)) safe[key] = stock[key];
  });
  return {
    code,
    name: normalizeText(safe.name || safe.masterName || safe.companyName || code),
    market: normalizeText(safe.market || ""),
    sector: normalizeText(safe.sector || ""),
    dataSource: normalizeText(safe.dataSource || ""),
    viewedAt: normalizeText(safe.viewedAt || new Date().toISOString())
  };
}

export function normalizeRecentCode(code) {
  const text = String(code || "").trim().normalize("NFKC").toUpperCase();
  const match = text.match(/^(\d{4})(?:\.T)?$/);
  return match ? match[1] : null;
}

function dedupeRecentStocks(stocks) {
  const seen = new Set();
  const normalized = [];
  stocks.forEach((item) => {
    const stock = normalizeRecentStock(item);
    if (!stock || seen.has(stock.code)) return;
    seen.add(stock.code);
    normalized.push(stock);
  });
  return normalized;
}

function normalizeText(value) {
  return String(value || "").trim();
}

function getStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}
