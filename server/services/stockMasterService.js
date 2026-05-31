import { LOCAL_STOCK_MASTER } from "../data/localStockMaster.js";

export function normalizeStockCode(code) {
  const normalized = String(code ?? "")
    .trim()
    .toUpperCase()
    .replace(/\.T$/, "")
    .replace(/\s+/g, "");
  return /^\d{4}$/.test(normalized) ? normalized : null;
}

export function getLocalStockMaster(code) {
  const normalizedCode = normalizeStockCode(code);
  if (!normalizedCode) return null;
  const master = LOCAL_STOCK_MASTER[normalizedCode];
  return master ? { ...master } : null;
}

export function getStockMasterInfo(code) {
  const normalizedCode = normalizeStockCode(code);
  if (!normalizedCode) {
    return {
      code: null,
      found: false,
      master: null,
      message: "Invalid stock code."
    };
  }
  const master = getLocalStockMaster(normalizedCode);
  if (!master) {
    return {
      code: normalizedCode,
      found: false,
      master: null,
      message: "Stock master info was not found."
    };
  }
  return {
    ...master,
    found: true,
    master
  };
}

export function mergeStockMasterIntoStockData(stockData, masterInfo) {
  if (!stockData || typeof stockData !== "object") return stockData;
  const master = masterInfo?.master || (masterInfo?.found ? masterInfo : null);
  if (!master) {
    return {
      ...stockData,
      stockMasterFound: false
    };
  }
  return {
    ...stockData,
    code: normalizeStockCode(stockData.code) || stockData.code,
    name: shouldUseMasterName(stockData.name, stockData.code) ? master.name : stockData.name,
    market: stockData.market || master.market,
    sector: stockData.sector || master.sector,
    stockMasterSource: master.source,
    stockMasterFound: true
  };
}

export function getStockMasterStatus() {
  const codes = Object.keys(LOCAL_STOCK_MASTER).sort();
  return {
    ok: true,
    source: "LOCAL_MASTER",
    count: codes.length,
    codes,
    message: "Local stock master is available."
  };
}

export function fetchJQuantsListedInfoPlaceholder() {
  return {
    ok: false,
    implemented: false,
    didNetworkRequest: false,
    message: "J-Quants listed info fetch is not implemented in this step."
  };
}

function shouldUseMasterName(name, code) {
  const text = String(name || "").trim();
  if (!text) return true;
  const normalizedCode = normalizeStockCode(code);
  if (!normalizedCode) return false;
  return text === normalizedCode
    || text === `${normalizedCode} J-Quants確認用`
    || text.includes("J-Quants確認用")
    || text.includes("銘柄名未取得");
}
