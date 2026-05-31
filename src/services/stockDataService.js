import { getMockStockData as readMockStockData, mockStocks } from "../logic/mockStockData.js";
import {
  getCsvStockData as readCsvStockData,
  listCsvStocks,
  parseStockCsv,
  setCsvStockData
} from "./csvStockDataService.js";
import { getBackendStockData } from "./backendStockDataService.js";

export { listCsvStocks, parseStockCsv, setCsvStockData };

export async function getStockData(query, options = {}) {
  const provider = options.dataProvider ?? "AUTO";
  if (provider === "AUTO") {
    try {
      return getCsvStockData(query);
    } catch {
      try {
        return await getBackendStockData(query, { forceRefresh: Boolean(options.forceRefresh) });
      } catch {
        return getMockStockData(query);
      }
    }
  }
  if (provider === "MOCK") return getMockStockData(query);
  if (provider === "J_QUANTS") return getJQuantsStockData(query);
  if (provider === "CSV") return getCsvStockData(query);
  throw new Error(`未対応のデータプロバイダーです: ${provider}`);
}

export async function getMockStockData(query) {
  return readMockStockData(query);
}

export async function getJQuantsStockData() {
  return placeholderResult("J-Quants接続は未実装です。今回は実API通信を行いません。", "J_QUANTS");
}

export async function getTdnetDisclosureData() {
  return placeholderResult("TDnet接続は未実装です。今回は実API通信を行いません。", "TDNET");
}

export function getCsvStockData(query) {
  return readCsvStockData(query);
}

export async function fetchStockData(query, options = {}) {
  return getStockData(query, options);
}

export async function fetchManyStocks(queries, options = {}) {
  return Promise.all(queries.map((query) => getStockData(query, options)));
}

export function listMockStocks() {
  return Object.values(mockStocks).map(({ code, name, dataSource }) => ({ code, name, dataSource }));
}

export function listAvailableStocks() {
  return [...listCsvStocks(), ...Object.values(mockStocks)].map(({ code, name, dataSource, dataSourceLabel, tradableDataLabel, isTradableData }) => ({
    code,
    name,
    dataSource,
    dataSourceLabel,
    tradableDataLabel,
    isTradableData
  }));
}

function placeholderResult(message, dataSource) {
  return {
    implemented: false,
    didNetworkRequest: false,
    dataSource,
    message
  };
}
