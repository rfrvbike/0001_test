export const FAVORITE_STOCKS_KEY = "stockAnalyzer.favoriteStocks";
export const FAVORITE_STOCKS_MAX = 50;

const FORBIDDEN_KEYS = new Set([
  "apiKey",
  "JQUANTS_API_KEY",
  "headers",
  "rawRows",
  "debugInfo",
  "financialSummary",
  "structuredSummary",
  "aiSummary"
]);

export function getFavoriteStocks(storage = getStorage()) {
  if (!storage) return [];
  try {
    const raw = storage.getItem(FAVORITE_STOCKS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((stock) => normalizeFavoriteStock(stock))
      .filter(Boolean)
      .slice(0, FAVORITE_STOCKS_MAX);
  } catch {
    return [];
  }
}

export function saveFavoriteStocks(favorites, storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    const normalized = dedupeFavorites(Array.isArray(favorites) ? favorites : [])
      .slice(0, FAVORITE_STOCKS_MAX);
    storage.setItem(FAVORITE_STOCKS_KEY, JSON.stringify(normalized));
    return { ok: true, favorites: normalized };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function addFavoriteStock(stock, storage = getStorage()) {
  const normalized = normalizeFavoriteStock(stock);
  if (!normalized) return { ok: false, error: "Invalid favorite stock." };
  const current = getFavoriteStocks(storage)
    .filter((favorite) => favorite.code !== normalized.code);
  const favorites = [normalized, ...current].slice(0, FAVORITE_STOCKS_MAX);
  return saveFavoriteStocks(favorites, storage);
}

export function removeFavoriteStock(code, storage = getStorage()) {
  const normalizedCode = normalizeFavoriteCode(code);
  if (!normalizedCode) return { ok: false, error: "Invalid favorite stock code." };
  const favorites = getFavoriteStocks(storage).filter((favorite) => favorite.code !== normalizedCode);
  return saveFavoriteStocks(favorites, storage);
}

export function isFavoriteStock(code, storage = getStorage()) {
  const normalizedCode = normalizeFavoriteCode(code);
  if (!normalizedCode) return false;
  return getFavoriteStocks(storage).some((favorite) => favorite.code === normalizedCode);
}

export function clearFavoriteStocks(storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    storage.removeItem(FAVORITE_STOCKS_KEY);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function normalizeFavoriteStock(stock) {
  if (!stock || typeof stock !== "object") return null;
  const code = normalizeFavoriteCode(stock.code || stock.LocalCode || stock.Code);
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
    addedAt: safe.addedAt || new Date().toISOString(),
    lastUsedAt: safe.lastUsedAt || ""
  };
}

export function normalizeFavoriteCode(code) {
  const text = String(code || "").trim().toUpperCase();
  const match = text.match(/^(\d{4})(?:\.T)?$/);
  return match ? match[1] : null;
}

function dedupeFavorites(favorites) {
  const seen = new Set();
  const normalized = [];
  favorites.forEach((favorite) => {
    const stock = normalizeFavoriteStock(favorite);
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
