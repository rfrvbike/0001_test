import { applyCsvSourceMeta, validateCsvStockData } from "./csvStockDataService.js";

export const CSV_STORAGE_KEY = "stockAnalyzer.csvData.v1";
export const CSV_STORAGE_VERSION = 1;

export function buildCsvStorageMeta(stocks, fileName = "unknown.csv") {
  return {
    version: CSV_STORAGE_VERSION,
    savedAt: new Date().toISOString(),
    sourceFileName: fileName || "unknown.csv",
    count: Array.isArray(stocks) ? stocks.length : 0
  };
}

export function saveCsvDataToStorage(stocks, meta = {}, storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorageが利用できません" };
  try {
    const normalizedStocks = normalizeStoredStocks(stocks);
    const payload = {
      ...buildCsvStorageMeta(normalizedStocks, meta.sourceFileName),
      ...meta,
      version: CSV_STORAGE_VERSION,
      count: normalizedStocks.length,
      stocks: normalizedStocks
    };
    storage.setItem(CSV_STORAGE_KEY, JSON.stringify(payload));
    return { ok: true, data: payload };
  } catch (error) {
    return { ok: false, error: `CSVデータを保存できませんでした: ${error.message}` };
  }
}

export function loadCsvDataFromStorage(storage = getStorage()) {
  if (!storage) return { ok: false, data: null, error: "localStorageが利用できません" };
  const raw = storage.getItem(CSV_STORAGE_KEY);
  if (!raw) return { ok: true, data: null, error: "" };
  try {
    const parsed = JSON.parse(raw);
    const normalized = normalizeStoredCsvData(parsed);
    return { ok: true, data: normalized, error: "" };
  } catch (error) {
    return { ok: false, data: null, error: `保存済みCSVデータを復元できませんでした。保存データが壊れている可能性があります。${error.message}` };
  }
}

export function clearCsvDataStorage(storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorageが利用できません" };
  try {
    storage.removeItem(CSV_STORAGE_KEY);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: `保存済みCSVデータを削除できませんでした: ${error.message}` };
  }
}

export function hasSavedCsvData(storage = getStorage()) {
  if (!storage) return false;
  try {
    return Boolean(storage.getItem(CSV_STORAGE_KEY));
  } catch {
    return false;
  }
}

export function normalizeStoredCsvData(storageData) {
  if (!storageData || typeof storageData !== "object") throw new Error("保存データの形式が不正です");
  if (storageData.version !== CSV_STORAGE_VERSION) throw new Error("保存データのversionが対応していません");
  if (!Array.isArray(storageData.stocks)) throw new Error("保存データにstocks配列がありません");

  const stocks = normalizeStoredStocks(storageData.stocks);
  return {
    version: CSV_STORAGE_VERSION,
    savedAt: storageData.savedAt || "",
    sourceFileName: storageData.sourceFileName || "unknown.csv",
    count: stocks.length,
    stocks
  };
}

function normalizeStoredStocks(stocks) {
  if (!Array.isArray(stocks)) throw new Error("stocksが配列ではありません");
  return stocks.map((stock, index) => {
    const normalized = applyCsvSourceMeta(stock, {
      storageSourceLabel: "ブラウザ保存済みCSV"
    });
    const errors = validateCsvStockData(normalized, index + 1);
    if (errors.length) throw new Error(errors.join(" / "));
    return normalized;
  });
}

function getStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}
