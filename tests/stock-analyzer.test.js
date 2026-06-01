import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { calculateIndicators } from "../src/logic/indicators.js";
import { calculateFinancialScore, calculateScore, judgeSignal } from "../src/logic/scoring.js";
import { getMockStockData } from "../src/logic/mockStockData.js";
import { buildReasonSummary } from "../src/logic/summaryBuilder.js";
import { buildStructuredSummary } from "../src/logic/structuredSummaryBuilder.js";
import { buildAiSummaryMock, sanitizeAiSummaryInput } from "../src/logic/aiSummaryMockBuilder.js";
import { buildPreTradeCheck } from "../src/logic/preTradeCheckBuilder.js";
import { buildThemeSummary, getMockThemesForStock } from "../src/logic/themeSummaryBuilder.js";
import {
  analyzeStockList,
  buildBulkAnalysisSummary,
  filterBulkAnalysisResults,
  sortBulkAnalysisResults
} from "../src/logic/bulkAnalysis.js";
import { exportAnalysisResultsToCsv } from "../src/logic/csvExport.js";
import {
  getCsvStockData,
  getJQuantsStockData,
  getStockData,
  getTdnetDisclosureData,
  parseStockCsv,
  setCsvStockData
} from "../src/services/stockDataService.js";
import { buildAiSummary, buildRuleBasedSummary } from "../src/services/aiSummaryService.js";
import {
  CSV_STORAGE_KEY,
  buildCsvStorageMeta,
  clearCsvDataStorage,
  hasSavedCsvData,
  loadCsvDataFromStorage,
  saveCsvDataToStorage
} from "../src/services/csvStorageService.js";
import {
  FAVORITE_STOCKS_KEY,
  addFavoriteStock,
  getFavoriteStocks,
  isFavoriteStock,
  normalizeFavoriteCode,
  removeFavoriteStock
} from "../src/services/favoriteStocksService.js";
import {
  RECENT_STOCKS_KEY,
  addRecentStock,
  clearRecentStocks,
  getRecentStocks,
  normalizeRecentCode,
  removeRecentStock
} from "../src/services/recentStocksService.js";
import {
  STOCK_MASTER_CSV_KEY,
  STOCK_MASTER_CSV_META_KEY,
  buildStockMasterCsvTemplate,
  clearStoredStockMaster,
  decodeCsvArrayBuffer,
  detectMojibake,
  getStoredStockMaster,
  getStoredStockMasterMeta,
  mergeStockMasterRows,
  normalizeStockMasterCode,
  parseStockMasterCsvText,
  saveStoredStockMaster
} from "../src/services/stockMasterCsvService.js";
import {
  JQUANTS_MASTER_MOCK_SOURCE,
  buildCsvFromMasterData,
  buildMasterMockDryRun,
  fetchMasterMock,
  normalizeMasterData
} from "../src/services/jquantsMasterService.js";
import {
  MASTER_SYNC_SOURCES,
  CsvMasterSyncProvider,
  JQuantsMasterSyncProvider,
  MasterSyncManager,
  MockMasterSyncProvider,
  buildMasterSyncDryRun,
  syncMaster
} from "../src/services/masterSyncService.js";
import {
  buildSearchIndex,
  isStockCodeQuery,
  mergeDuplicateCandidates,
  normalizeSearchText,
  searchStockCandidates
} from "../src/services/stockSearchService.js";
import {
  getBackendMasterSyncDryRun,
  getBackendHealth,
  getBackendJQuantsConnectionCheck,
  getBackendJQuantsFinancialSummary,
  getBackendJQuantsMappedStockData,
  getBackendJQuantsStatus,
  getBackendStockData,
  postBackendMasterSync
} from "../src/services/backendStockDataService.js";
import { getSafeEnvStatus, loadEnv } from "../server/config/env.js";
import { createServer } from "../server/index.js";
import {
  checkJQuantsApiKeyReady,
  checkJQuantsConnection,
  DEFAULT_RAW_FROM,
  DEFAULT_RAW_TO,
  extractLatestFinancialSummary,
  fetchJQuantsConnectionCheck,
  fetchJQuantsFinancialSummary,
  fetchJQuantsFinancialSummaryInternal,
  fetchJQuantsMappedStockData,
  fetchJQuantsRawDailyBars,
  fetchJQuantsRawDailyBarsInternal,
  JQUANTS_CONNECTION_CHECK_ENDPOINT,
  JQUANTS_FINS_SUMMARY_ENDPOINT,
  JQUANTS_RAW_DAILY_BARS_ENDPOINT,
  getJQuantsStatus as getServerJQuantsStatus,
  getJQuantsRealOrFallbackStockData,
  getJQuantsStockData as getBackendJQuantsStockData,
  sanitizeJQuantsError,
  sanitizeFinancialSummaryResponse,
  sanitizeRawDailyBarsResponse,
  validateJQuantsConfig
} from "../server/services/jquantsClient.js";
import {
  buildJQuantsCacheKey,
  canMakeJQuantsRequest,
  clearJQuantsCache,
  getCachedJQuantsResult,
  getJQuantsCacheStats,
  setCachedJQuantsResult,
  waitForJQuantsRateLimitIfNeeded
} from "../server/services/jquantsCache.js";
import {
  calculateChange as calculateMappedChange,
  calculateRsiFromCloses,
  calculateSimpleMovingAverage,
  mapJQuantsDailyBarsToStockData
} from "../server/services/stockDataMapper.js";
import {
  fetchJQuantsListedInfoPlaceholder,
  getLocalStockMaster,
  getStockMasterInfo,
  getStockMasterStatus,
  mergeStockMasterIntoStockData,
  normalizeStockCode
} from "../server/services/stockMasterService.js";
import {
  getDataSourceDisplay,
  isJQuantsRealStock
} from "../src/components/StockAnalyzer.js";
import { FinancialSummaryPanel } from "../src/components/FinancialSummaryPanel.js";
import { FavoriteStocksPanel } from "../src/components/FavoriteStocksPanel.js";
import { RecentStocksPanel } from "../src/components/RecentStocksPanel.js";
import { AiSummaryMockPanel } from "../src/components/AiSummaryMockPanel.js";
import { StructuredSummaryPanel } from "../src/components/StructuredSummaryPanel.js";
import { ThemeSummaryPanel } from "../src/components/ThemeSummaryPanel.js";
import { CollapsibleSection } from "../src/components/CollapsibleSection.js";
import { CompactStatusBar } from "../src/components/CompactStatusBar.js";
import { PrimaryDecisionCard } from "../src/components/PrimaryDecisionCard.js";
import { KeyMetricsGrid } from "../src/components/KeyMetricsGrid.js";
import { PreTradeCheckPanel } from "../src/components/PreTradeCheckPanel.js";
import { StockSearchSuggestions } from "../src/components/StockSearchSuggestions.js";
import { StockMasterCsvPanel } from "../src/components/StockMasterCsvPanel.js";
import { formatLargeYen, formatPerShareYen } from "../src/components/formatters.js";

const today = new Date("2026-05-24T00:00:00");

function createMockStorage() {
  const store = new Map();
  return {
    getItem: (key) => store.has(key) ? store.get(key) : null,
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key)
  };
}

const toyota = getMockStockData("7203");
assert.equal(toyota.isMock, true);
assert.equal(toyota.isTradableData, false);
assert.equal(toyota.dataSource, "MOCK");
assert.equal(toyota.dataSourceLabel, "モックデータ");

assert.equal(normalizeStockCode("7203"), "7203");
assert.equal(normalizeStockCode("7203.T"), "7203");
assert.equal(normalizeStockCode(" 7203 "), "7203");
assert.equal(normalizeStockCode("ABC"), null);
assert.equal(typeof getLocalStockMaster("7203").name, "string");
assert.equal(getLocalStockMaster("7203.T").market, "プライム");
assert.equal(getLocalStockMaster("9999"), null);
const masterMerged = mergeStockMasterIntoStockData({
  code: "7203",
  name: "7203 J-Quants遒ｺ隱咲畑",
  market: ""
}, getStockMasterInfo("7203"));
assert.equal(typeof masterMerged.name, "string");
assert.equal(masterMerged.market, "プライム");
assert.equal(typeof masterMerged.sector, "string");
assert.equal(masterMerged.stockMasterSource, "LOCAL_MASTER");
const csvNamePreserved = mergeStockMasterIntoStockData({
  code: "7203",
  name: "トヨタ自動車 CSV",
  market: "CSV取込"
}, getStockMasterInfo("7203"));
assert.equal(csvNamePreserved.name, "トヨタ自動車 CSV");
const masterStatus = getStockMasterStatus();
assert.equal(masterStatus.count >= 4, true);
assert.equal(masterStatus.codes.includes("7203"), true);
assert.equal(fetchJQuantsListedInfoPlaceholder().didNetworkRequest, false);

const toyotaIndicators = calculateIndicators(toyota, today);
const toyotaScore = calculateScore(toyota, toyotaIndicators);
assert.equal(toyotaScore.entries.some((entry) => entry.value === 20), true);
assert.equal(toyotaScore.totalScore > 0, true);
assert.equal(typeof judgeSignal(58, ["RSI 75以上"]), "string");

const mockSummary = buildReasonSummary(toyota, toyotaIndicators, toyotaScore);
assert.equal(mockSummary.dataNotice.includes("モックデータ"), true);

const toyotaThemeSummary = buildThemeSummary(toyota);
assert.equal(toyotaThemeSummary.available, true);
assert.equal(toyotaThemeSummary.externalNewsApiUsed, false);
assert.equal(toyotaThemeSummary.externalAiUsed, false);
assert.equal(Array.isArray(toyotaThemeSummary.themes), true);
assert.equal(toyotaThemeSummary.themes.includes("EV"), true);
assert.equal(typeof toyotaThemeSummary.comment, "string");
assert.equal(toyotaThemeSummary.themeScoreApplied, false);
assert.equal(getMockThemesForStock("SPACE_THEME_SAMPLE").themes.includes("SpaceX上場観測"), true);
const disabledThemeSummary = buildThemeSummary(toyota, { enabled: false });
assert.equal(disabledThemeSummary.status.enabled, false);
const manualThemeSummary = buildThemeSummary(toyota, { manualThemes: "SpaceX上場観測, 宇宙関連, 衛星通信" });
assert.equal(manualThemeSummary.themes.includes("SpaceX上場観測"), true);
assert.equal(calculateScore({ ...toyota, themeSummary: toyotaThemeSummary }, toyotaIndicators).totalScore, toyotaScore.totalScore);
assert.equal(JSON.stringify(toyotaThemeSummary).includes("JQUANTS_API_KEY"), false);
assert.equal(JSON.stringify(toyotaThemeSummary).includes("headers"), false);
assert.equal(ThemeSummaryPanel(toyotaThemeSummary).includes("ニュース・テーマ材料"), true);

const csvText = `code,name,market,price,previousClose,volume,averageVolume20d,ma25,ma75,rsi,high52w,highYtd,latestEarningsDate,nextEarningsDate,earningsTrend,hasUpwardRevision,hasDownwardRevision,hasDividendIncrease,hasBuyback,importantDisclosures,policyThemes,policyRelationType,policyDescription,candlePattern,isBeforeEarnings,lastUpdated
7203,トヨタ自動車 CSV,東証プライム,3200,3150,25000000,18000000,3050,2900,64,3350,3350,2026-02-05,2026-05-10,GROWING,true,false,true,false,上方修正を発表,EV・防衛・半導体,DIRECT,EVや電池関連で政策テーマに関連,NORMAL,false,2026-05-24
6758,ソニーグループ CSV,東証プライム,14500,14300,8000000,5000000,13200,12500,78,14700,14700,2026-02-10,2026-05-12,STABLE,false,false,false,false,特になし,AI・半導体,INDIRECT,AI関連需要の一部恩恵,NORMAL,false,2026-05-24`;

const parsed = parseStockCsv(csvText);
assert.equal(parsed.errors.length, 0);
assert.equal(parsed.stocks.length, 2);
assert.equal(typeof parsed.stocks[0].price, "number");
assert.equal(typeof parsed.stocks[0].hasUpwardRevision, "boolean");
assert.equal(parsed.stocks[0].policyThemes.length, 3);
assert.equal(parsed.stocks[0].dataSource, "CSV");
assert.equal(parsed.stocks[0].dataSourceLabel, "CSV取込");
assert.equal(parsed.stocks[0].isMock, false);
assert.equal(parsed.stocks[0].isTradableData, false);
assert.equal(typeof parsed.stocks[0].tradableDataLabel, "string");

assert.equal(parseStockCsv("code,name,price\n7203,CSV,3200").errors.some((error) => error.includes("ma25")), true);
assert.equal(parseStockCsv(`code,name,price,previousClose,volume,ma25,ma75,rsi,high52w,highYtd
,NoCode,1,1,1,1,1,50,1,1`).errors.some((error) => error.includes("code")), true);
assert.equal(parseStockCsv(`code,name,price,previousClose,volume,ma25,ma75,rsi,high52w,highYtd
BAD01,Bad Number,abc,1,1,1,1,50,1,1`).errors.some((error) => error.includes("price")), true);

setCsvStockData(parsed.stocks);
const csvStock = getCsvStockData("7203");
assert.equal(csvStock.dataSource, "CSV");
assert.equal(csvStock.name, "トヨタ自動車 CSV");

const preferred = await getStockData("7203");
assert.equal(preferred.dataSource, "CSV");
assert.equal(preferred.name, "トヨタ自動車 CSV");

const csvIndicators = calculateIndicators(csvStock, today);
const csvScore = calculateScore(csvStock, csvIndicators);
assert.equal(typeof csvScore.totalScore, "number");
const csvSummary = buildRuleBasedSummary(csvStock, csvIndicators, csvScore);
assert.equal(csvSummary.dataNotice.includes("CSV"), true);

const jquantsRealStockForUi = {
  ...toyota,
  dataSource: "J_QUANTS_MAPPED",
  dataSourceLabel: "J-Quants実データ",
  storageSourceLabel: undefined,
  isMock: false,
  isTradableData: false,
  tradableDataLabel: "J-Quants real data check",
  didNetworkRequest: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
};
assert.equal(isJQuantsRealStock(jquantsRealStockForUi), true);
const jquantsDisplay = getDataSourceDisplay(jquantsRealStockForUi);
assert.equal(jquantsDisplay.storageSourceLabel, "バックエンド / J-Quants");
assert.equal(jquantsDisplay.storageSourceLabel === "CSVファイル取込", false);
assert.equal(typeof jquantsDisplay.notice, "string");
assert.equal(jquantsDisplay.notice.includes("モックデータ"), false);
assert.equal(jquantsDisplay.dataPeriod, "2025-09-01 〜 2026-01-31");
assert.equal(typeof buildReasonSummary(jquantsRealStockForUi, calculateIndicators(jquantsRealStockForUi, today), calculateScore(jquantsRealStockForUi, calculateIndicators(jquantsRealStockForUi, today))).dataNotice, "string");
assert.equal(buildReasonSummary(jquantsRealStockForUi, calculateIndicators(jquantsRealStockForUi, today), calculateScore(jquantsRealStockForUi, calculateIndicators(jquantsRealStockForUi, today))).dataNotice.includes("モックデータ"), false);
assert.equal(getDataSourceDisplay(csvStock).storageSourceLabel, "CSVファイル取込");
assert.equal(getDataSourceDisplay(toyota).storageSourceLabel, "モックデータ");
assert.equal(getDataSourceDisplay({ ...toyota, dataSource: "J_QUANTS_MOCK", dataSourceLabel: "J-Quants接続準備用モック" }).storageSourceLabel, "モックデータ");
const fallbackDisplay = getDataSourceDisplay({
  ...toyota,
  dataSource: "J_QUANTS_MOCK",
  dataSourceLabel: "J-Quants取得失敗・mockフォールバック",
  fallbackUsed: true,
  fallbackReason: "J-Quants fetch failed",
  jquantsErrorSummary: { safeError: "Forbidden" }
});
assert.equal(fallbackDisplay.dataSourceLabel, "J-Quants取得失敗・mockフォールバック");
assert.equal(fallbackDisplay.storageSourceLabel, "モックデータ");
assert.equal(fallbackDisplay.fallbackReason, "J-Quants fetch failed");

const storage = createMockStorage();
const meta = buildCsvStorageMeta(parsed.stocks, "sample_stock_data.csv");
assert.equal(meta.count, 2);
assert.equal(meta.sourceFileName, "sample_stock_data.csv");
assert.equal(meta.version, 1);
assert.equal(typeof meta.savedAt, "string");

const saved = saveCsvDataToStorage(parsed.stocks, { sourceFileName: "sample_stock_data.csv" }, storage);
assert.equal(saved.ok, true);
assert.equal(hasSavedCsvData(storage), true);
assert.equal(storage.getItem(CSV_STORAGE_KEY).includes("sample_stock_data.csv"), true);

const loaded = loadCsvDataFromStorage(storage);
assert.equal(loaded.ok, true);
assert.equal(loaded.data.count, 2);
assert.equal(loaded.data.sourceFileName, "sample_stock_data.csv");
assert.equal(loaded.data.stocks[0].dataSource, "CSV");
assert.equal(typeof loaded.data.stocks[0].tradableDataLabel, "string");
assert.equal(loaded.data.stocks[0].storageSourceLabel, "ブラウザ保存済みCSV");

const storedScore = calculateScore(loaded.data.stocks[0], calculateIndicators(loaded.data.stocks[0], today));
assert.equal(typeof storedScore.totalScore, "number");
assert.equal(analyzeStockList(loaded.data.stocks).length, 2);

setCsvStockData(loaded.data.stocks);
const storedPreferred = await getStockData("7203");
assert.equal(storedPreferred.dataSource, "CSV");
assert.equal(storedPreferred.storageSourceLabel, "ブラウザ保存済みCSV");
assert.equal(storedPreferred.name.includes("CSV"), true);

const brokenStorage = createMockStorage();
brokenStorage.setItem(CSV_STORAGE_KEY, "{bad json");
assert.equal(loadCsvDataFromStorage(brokenStorage).ok, false);

const invalidStorage = createMockStorage();
invalidStorage.setItem(CSV_STORAGE_KEY, JSON.stringify({ version: 1, stocks: "bad" }));
assert.equal(loadCsvDataFromStorage(invalidStorage).ok, false);

const favoriteStorage = createMockStorage();
assert.deepEqual(getFavoriteStocks(favoriteStorage), []);
assert.equal(normalizeFavoriteCode("7203"), "7203");
assert.equal(normalizeFavoriteCode("7203.T"), "7203");
assert.equal(addFavoriteStock({
  code: "7203.T",
  name: "トヨタ自動車",
  market: "プライム",
  sector: "輸送用機器",
  headers: { "x-api-key": "test-api-key-value" },
  rawRows: [{ secret: true }],
  debugInfo: { hidden: true },
  financialSummary: { available: true },
  structuredSummary: { raw: true },
  aiSummary: { raw: true }
}, favoriteStorage).ok, true);
assert.equal(addFavoriteStock({ code: "7203", name: "重複テスト" }, favoriteStorage).ok, true);
const favoriteStocks = getFavoriteStocks(favoriteStorage);
assert.equal(favoriteStocks.length, 1);
assert.equal(favoriteStocks[0].code, "7203");
assert.equal(favoriteStocks[0].name, "重複テスト");
assert.equal(isFavoriteStock("7203.T", favoriteStorage), true);
const favoriteRaw = favoriteStorage.getItem(FAVORITE_STOCKS_KEY);
assert.equal(favoriteRaw.includes("test-api-key-value"), false);
assert.equal(favoriteRaw.includes("x-api-key"), false);
assert.equal(favoriteRaw.includes("rawRows"), false);
assert.equal(favoriteRaw.includes("debugInfo"), false);
assert.equal(removeFavoriteStock("7203", favoriteStorage).ok, true);
assert.deepEqual(getFavoriteStocks(favoriteStorage), []);
const brokenFavoriteStorage = createMockStorage();
brokenFavoriteStorage.setItem(FAVORITE_STOCKS_KEY, "{bad json");
assert.deepEqual(getFavoriteStocks(brokenFavoriteStorage), []);

const recentStorage = createMockStorage();
assert.deepEqual(getRecentStocks(recentStorage), []);
assert.equal(normalizeRecentCode("7203.T"), "7203");
assert.equal(addRecentStock({
  code: "7203.T",
  name: "トヨタ自動車",
  market: "プライム",
  sector: "輸送用機器",
  dataSource: "J_QUANTS_MAPPED",
  headers: { "x-api-key": "test-api-key-value" },
  rawRows: [{ secret: true }],
  debugInfo: { hidden: true },
  financialSummary: { available: true },
  structuredSummary: { raw: true },
  aiSummary: { raw: true },
  themeSummary: { raw: true }
}, recentStorage).ok, true);
const firstRecentRaw = recentStorage.getItem(RECENT_STOCKS_KEY);
assert.equal(firstRecentRaw.includes("test-api-key-value"), false);
assert.equal(firstRecentRaw.includes("x-api-key"), false);
assert.equal(firstRecentRaw.includes("rawRows"), false);
assert.equal(firstRecentRaw.includes("debugInfo"), false);
assert.equal(firstRecentRaw.includes("financialSummary"), false);
assert.equal(addRecentStock({ code: "6758", name: "ソニーグループ" }, recentStorage).ok, true);
assert.equal(addRecentStock({ code: "7203", name: "トヨタ自動車 再表示" }, recentStorage).ok, true);
const recentStocks = getRecentStocks(recentStorage);
assert.equal(recentStocks.length, 2);
assert.equal(recentStocks[0].code, "7203");
assert.equal(recentStocks[0].name, "トヨタ自動車 再表示");
assert.equal(removeRecentStock("6758", recentStorage).ok, true);
assert.equal(getRecentStocks(recentStorage).length, 1);
assert.equal(clearRecentStocks(recentStorage).ok, true);
assert.deepEqual(getRecentStocks(recentStorage), []);
const brokenRecentStorage = createMockStorage();
brokenRecentStorage.setItem(RECENT_STOCKS_KEY, "{bad json");
assert.deepEqual(getRecentStocks(brokenRecentStorage), []);

const masterCsv = `code,name,market,sector
9434,ソフトバンク,プライム,情報・通信業
7011,三菱重工業,プライム,機械
5803,フジクラ,プライム,非鉄金属
7203.T,トヨタ自動車CSV,プライム,輸送用機器
7203,トヨタ自動車CSV更新,プライム,輸送用機器`;
const parsedMaster = parseStockMasterCsvText(masterCsv);
assert.equal(parsedMaster.ok, true);
assert.equal(parsedMaster.selectedEncoding, "text");
assert.equal(parsedMaster.rows.some((row) => row.code === "9434" && row.name === "ソフトバンク"), true);
assert.equal(parsedMaster.rows.some((row) => row.code === "7011" && row.sector === "機械"), true);
assert.equal(parsedMaster.rows.some((row) => row.code === "5803" && row.market === "プライム"), true);
assert.equal(normalizeStockMasterCode("7203.T"), "7203");
assert.equal(parsedMaster.rows.filter((row) => row.code === "7203").length, 1);
const utf8MasterBuffer = new TextEncoder().encode(masterCsv).buffer;
const decodedUtf8Master = decodeCsvArrayBuffer(utf8MasterBuffer, "utf-8");
assert.equal(decodedUtf8Master.ok, true);
assert.equal(decodedUtf8Master.text.includes("トヨタ自動車"), true);
const parsedDecodedMaster = parseStockMasterCsvText(decodedUtf8Master.text, decodedUtf8Master);
assert.equal(parsedDecodedMaster.detectedEncoding, "utf-8");
assert.equal(parsedDecodedMaster.rows.some((row) => row.code === "9434"), true);
const shiftJisSample = new Uint8Array([
  ...new TextEncoder().encode("code,name\n7203,"),
  0x82,
  0xa0
]).buffer;
const decodedShiftJis = decodeCsvArrayBuffer(shiftJisSample, "shift-jis");
assert.equal(decodedShiftJis.ok ? decodedShiftJis.text.includes("あ") : decodedShiftJis.decodeWarning.length > 0, true);
assert.equal(detectMojibake("繝医Κ繧ｿ").mojibakeSuspected, true);
assert.equal(parseStockMasterCsvText("code,name\n7203,繝医Κ繧ｿ").mojibakeSuspected, true);
const masterTemplate = buildStockMasterCsvTemplate();
assert.equal(masterTemplate.includes("code,name,market,sector"), true);
assert.equal(masterTemplate.includes("トヨタ自動車"), true);
assert.equal(parseStockMasterCsvText(masterTemplate).rows.some((row) => row.code === "9434"), true);
const jpHeaderMaster = parseStockMasterCsvText(`銘柄コード,銘柄名,市場,業種
9434,ソフトバンク,プライム,情報・通信業`);
assert.equal(jpHeaderMaster.rows[0].code, "9434");
assert.equal(jpHeaderMaster.rows[0].name, "ソフトバンク");
const invalidMaster = parseStockMasterCsvText(`code,name
,名前なし
ABCDE,不正コード`);
assert.equal(invalidMaster.rows.length, 0);
assert.equal(invalidMaster.errors.length >= 1, true);
const masterStorage = createMockStorage();
assert.deepEqual(getStoredStockMaster(masterStorage), []);
const savedMaster = saveStoredStockMaster(parsedMaster.rows, masterStorage, {
  selectedEncoding: "utf-8",
  detectedEncoding: "utf-8",
  mojibakeSuspected: false,
  apiKey: "test-api-key-value",
  rawRows: [{ secret: true }]
});
assert.equal(savedMaster.ok, true);
assert.equal(savedMaster.count, parsedMaster.rows.length);
assert.equal(savedMaster.meta.selectedEncoding, "utf-8");
assert.equal(savedMaster.meta.source, "CSV_IMPORT");
const storedMaster = getStoredStockMaster(masterStorage);
assert.equal(storedMaster.some((row) => row.code === "9434"), true);
const masterRaw = masterStorage.getItem(STOCK_MASTER_CSV_KEY);
assert.equal(masterRaw.includes("JQUANTS_API_KEY"), false);
assert.equal(masterRaw.includes("x-api-key"), false);
assert.equal(masterRaw.includes("rawRows"), false);
assert.equal(masterRaw.includes("debugInfo"), false);
assert.equal(masterRaw.includes("financialSummary"), false);
const masterMetaRaw = masterStorage.getItem(STOCK_MASTER_CSV_META_KEY);
assert.equal(masterMetaRaw.includes("test-api-key-value"), false);
assert.equal(masterMetaRaw.includes("rawRows"), false);
assert.equal(getStoredStockMasterMeta(masterStorage).count, parsedMaster.rows.length);
const brokenMasterStorage = createMockStorage();
brokenMasterStorage.setItem(STOCK_MASTER_CSV_KEY, "{bad json");
assert.deepEqual(getStoredStockMaster(brokenMasterStorage), []);
assert.equal(clearStoredStockMaster(masterStorage).ok, true);
assert.deepEqual(getStoredStockMaster(masterStorage), []);
assert.equal(getStoredStockMasterMeta(masterStorage), null);
assert.equal(mergeStockMasterRows([
  { code: "9434", name: "古い名前" },
  { code: "9434", name: "ソフトバンク", market: "プライム" }
]).length, 1);

const jquantsMasterMock = await fetchMasterMock();
assert.equal(jquantsMasterMock.didNetworkRequest, false);
assert.equal(jquantsMasterMock.source, JQUANTS_MASTER_MOCK_SOURCE);
assert.equal(jquantsMasterMock.rows.length, 9);
const normalizedJquantsMaster = normalizeMasterData(jquantsMasterMock.rows);
assert.equal(normalizedJquantsMaster.length, 9);
assert.equal(normalizedJquantsMaster.some((row) => row.code === "7203" && row.name === "トヨタ自動車"), true);
assert.equal(normalizedJquantsMaster.every((row) => row.source === "JQUANTS_MOCK"), true);
const jquantsMasterCsv = buildCsvFromMasterData(normalizedJquantsMaster);
assert.equal(jquantsMasterCsv.count, 9);
assert.equal(jquantsMasterCsv.csvText.includes("7203,トヨタ自動車"), true);
const jquantsMasterDryRun = await buildMasterMockDryRun();
assert.equal(jquantsMasterDryRun.ok, true);
assert.equal(jquantsMasterDryRun.fetchedCount, 9);
assert.equal(jquantsMasterDryRun.csvCount, 9);
assert.equal(jquantsMasterDryRun.sampleRows[0].source, "JQUANTS_MOCK");
const mockMasterSyncProvider = new MockMasterSyncProvider();
const mockMasterSyncResult = await mockMasterSyncProvider.sync();
assert.equal(mockMasterSyncResult.source, MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(mockMasterSyncResult.count, 9);
assert.equal(mockMasterSyncResult.didNetworkRequest, false);
assert.equal(Array.isArray(mockMasterSyncResult.records), true);
const csvMasterSyncProvider = new CsvMasterSyncProvider([{ code: "1111", name: "CSV同期", market: "テスト", sector: "テスト" }]);
const csvMasterSyncResult = await csvMasterSyncProvider.sync();
assert.equal(csvMasterSyncResult.source, MASTER_SYNC_SOURCES.CSV_IMPORT);
assert.equal(csvMasterSyncResult.count, 1);
assert.equal(csvMasterSyncResult.didNetworkRequest, false);
const masterSyncManager = new MasterSyncManager();
const managerMockResult = await masterSyncManager.syncMaster(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(managerMockResult.source, MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(managerMockResult.count, 9);
const masterSyncDryRun = await buildMasterSyncDryRun(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(masterSyncDryRun.source, MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(masterSyncDryRun.count, 9);
assert.equal(masterSyncDryRun.didNetworkRequest, false);
const directSyncResult = await syncMaster(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
assert.equal(directSyncResult.count, 9);
await assert.rejects(
  () => new JQuantsMasterSyncProvider().sync(),
  /not implemented|disabled/
);
const jquantsMasterStorage = createMockStorage();
const savedJquantsMaster = saveStoredStockMaster(normalizedJquantsMaster, jquantsMasterStorage, {
  source: JQUANTS_MASTER_MOCK_SOURCE,
  lastSyncSource: MASTER_SYNC_SOURCES.JQUANTS_MOCK,
  lastSyncCount: normalizedJquantsMaster.length,
  lastSyncAt: "2026-06-01T00:00:00.000Z",
  selectedEncoding: "utf-8",
  detectedEncoding: "utf-8"
});
assert.equal(savedJquantsMaster.ok, true);
assert.equal(savedJquantsMaster.count, 9);
assert.equal(savedJquantsMaster.meta.source, "JQUANTS_MOCK");
assert.equal(getStoredStockMasterMeta(jquantsMasterStorage).source, "JQUANTS_MOCK");
assert.equal(getStoredStockMasterMeta(jquantsMasterStorage).lastSyncSource, "JQUANTS_MOCK");
assert.equal(getStoredStockMasterMeta(jquantsMasterStorage).lastSyncCount, 9);

const cleared = clearCsvDataStorage(storage);
assert.equal(cleared.ok, true);
assert.equal(hasSavedCsvData(storage), false);
assert.equal(loadCsvDataFromStorage(null).ok, false);
assert.equal(saveCsvDataToStorage(parsed.stocks, {}, null).ok, false);
assert.equal(hasSavedCsvData(null), false);

const bulkResults = analyzeStockList([csvStock, parsed.stocks[1], getMockStockData("TEST02"), getMockStockData("9984")]);
const bulkSummary = buildBulkAnalysisSummary(bulkResults);
assert.equal(bulkSummary.total, 4);
assert.equal(bulkSummary.csv, 2);
assert.equal(bulkSummary.mock, 2);
assert.equal(bulkSummary.highRisk >= 1, true);
assert.equal(sortBulkAnalysisResults(bulkResults, "buyScoreDesc")[0].scoreResult.buyScore >= sortBulkAnalysisResults(bulkResults, "buyScoreDesc")[1].scoreResult.buyScore, true);
assert.equal(filterBulkAnalysisResults(bulkResults, { material: "policyTheme" }).every((result) => result.stock.policyThemes.length > 0), true);
assert.equal(filterBulkAnalysisResults(bulkResults, { search: "7203" }).some((result) => result.stock.code === "7203"), true);

const exportedCsv = exportAnalysisResultsToCsv(bulkResults);
assert.equal(exportedCsv.includes("code,name,dataSource"), true);
assert.equal(exportedCsv.includes("DISCLAIMER"), true);
assert.equal(exportedCsv.includes("投資助言ではありません"), true);

const jquants = await getJQuantsStockData("7203");
const tdnet = await getTdnetDisclosureData("7203");
const ai = await buildAiSummary(csvStock, csvIndicators, csvScore);
assert.equal(jquants.didNetworkRequest, false);
assert.equal(tdnet.didNetworkRequest, false);
assert.equal(ai.didNetworkRequest, false);
assert.equal(jquants.implemented, false);
assert.equal(tdnet.implemented, false);
assert.equal(ai.implemented, false);

assert.equal(existsSync("src/services/backendStockDataService.js"), true);

const missingEnv = loadEnv({ envFilePath: path.join(os.tmpdir(), "missing-stock-analyzer.env"), processEnv: {} });
assert.equal(missingEnv.jquantsEnabled, false);
assert.equal(missingEnv.apiVersion, "v2");
assert.equal(missingEnv.jquantsApiKey, "");
assert.equal(missingEnv.serverPort, 8787);
assert.equal(missingEnv.externalApiTimeoutMs, 10000);

const tempEnvDir = mkdtempSync(path.join(os.tmpdir(), "stock-analyzer-env-"));
const tempEnvPath = path.join(tempEnvDir, ".env");
writeFileSync(tempEnvPath, [
  "JQUANTS_ENABLED=true",
  "JQUANTS_API_VERSION=v2",
  "JQUANTS_API_KEY=test-api-key-value",
  "SERVER_PORT=9999",
  "EXTERNAL_API_TIMEOUT_MS=12345"
].join("\n"));
const enabledEnv = loadEnv({ envFilePath: tempEnvPath, processEnv: {} });
assert.equal(enabledEnv.jquantsEnabled, true);
assert.equal(enabledEnv.apiVersion, "v2");
assert.equal(enabledEnv.jquantsApiKey, "test-api-key-value");
assert.equal(enabledEnv.serverPort, 9999);
assert.equal(enabledEnv.externalApiTimeoutMs, 12345);

const safeEnabledEnv = getSafeEnvStatus({ envFilePath: tempEnvPath, processEnv: {} });
assert.equal(safeEnabledEnv.hasApiKey, true);
assert.equal("jquantsApiKey" in safeEnabledEnv, false);
assert.equal(JSON.stringify(safeEnabledEnv).includes("test-api-key-value"), false);
assert.equal(safeEnabledEnv.useRealStocks, false);
assert.equal(safeEnabledEnv.fallbackToMock, true);
assert.equal(safeEnabledEnv.realStockFrom, "2025-09-01");
assert.equal(safeEnabledEnv.realStockTo, "2026-01-31");
assert.equal(safeEnabledEnv.cacheEnabled, true);
assert.equal(safeEnabledEnv.cacheTtlMs, 300000);
assert.equal(safeEnabledEnv.minRequestIntervalMs, 1000);
assert.equal(safeEnabledEnv.maxRequestsPerMinute, 20);
assert.equal(safeEnabledEnv.useFinancials, false);
assert.equal(safeEnabledEnv.financialsFallbackSilent, true);
assert.equal(safeEnabledEnv.useFinancialScore, true);
assert.equal(safeEnabledEnv.aiSummary.mockEnabled, true);
assert.equal(safeEnabledEnv.aiSummary.externalApiEnabled, false);
assert.equal(safeEnabledEnv.aiSummary.provider, "none");
assert.equal(safeEnabledEnv.themeSummary.mockEnabled, true);
assert.equal(safeEnabledEnv.themeSummary.externalNewsApiEnabled, false);
assert.equal(safeEnabledEnv.themeSummary.scoreEnabled, false);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { JQUANTS_USE_FINANCIAL_SCORE: "false" }
}).useFinancialScore, false);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { AI_SUMMARY_MOCK_ENABLED: "false" }
}).aiSummaryMockEnabled, false);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { AI_SUMMARY_EXTERNAL_API_ENABLED: "true" }
}).aiSummaryExternalApiEnabled, true);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { THEME_SUMMARY_MOCK_ENABLED: "false" }
}).themeSummaryMockEnabled, false);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED: "true" }
}).themeSummaryExternalNewsApiEnabled, true);
assert.equal(loadEnv({
  envFilePath: "",
  processEnv: { THEME_SUMMARY_SCORE_ENABLED: "true" }
}).themeSummaryScoreEnabled, true);

assert.equal(validateJQuantsConfig(loadEnv({ processEnv: { JQUANTS_ENABLED: "false" }, envFilePath: "" })).ok, true);
const missingApiKeyConfig = loadEnv({ processEnv: { JQUANTS_ENABLED: "true", JQUANTS_API_KEY: "" }, envFilePath: "" });
assert.deepEqual(validateJQuantsConfig(missingApiKeyConfig).missingFields, ["JQUANTS_API_KEY"]);
const readyConfig = loadEnv({
  processEnv: {
    JQUANTS_ENABLED: "true",
    JQUANTS_API_KEY: "test-api-key-value",
    JQUANTS_MIN_REQUEST_INTERVAL_MS: "0",
    JQUANTS_MAX_REQUESTS_PER_MINUTE: "999"
  },
  envFilePath: ""
});
assert.equal(validateJQuantsConfig(readyConfig).ok, true);
assert.equal(validateJQuantsConfig(readyConfig).apiVersion, "v2");
assert.equal(checkJQuantsApiKeyReady(readyConfig).mode, "api_key_ready");
assert.equal(checkJQuantsApiKeyReady(readyConfig).didNetworkRequest, false);

let connectionFetchCalled = false;
const connectionSuccess = await fetchJQuantsConnectionCheck(readyConfig, {
  fetchImpl: async (url, options) => {
    connectionFetchCalled = true;
    assert.equal(String(url).includes(JQUANTS_CONNECTION_CHECK_ENDPOINT), true);
    assert.equal(String(url).includes("/v2/bulk/list"), false);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify({ data: [{ Key: "sample.csv" }], pagination_key: "next" }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(connectionFetchCalled, true);
assert.equal(connectionSuccess.ok, true);
assert.equal(connectionSuccess.mode, "connection_ok");
assert.equal(connectionSuccess.didNetworkRequest, true);
assert.equal(connectionSuccess.checkedEndpoint, JQUANTS_CONNECTION_CHECK_ENDPOINT);
assert.equal(connectionSuccess.dataKind, "connection_check_only");
assert.equal(connectionSuccess.count, 1);
assert.equal(JSON.stringify(connectionSuccess).includes("test-api-key-value"), false);
assert.equal("data" in connectionSuccess, false);

const connectionFailure = await fetchJQuantsConnectionCheck(readyConfig, {
  fetchImpl: async () => new Response(JSON.stringify({ message: "Unauthorized" }), {
    status: 401,
    statusText: "Unauthorized",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(connectionFailure.ok, false);
assert.equal(connectionFailure.mode, "connection_error");
assert.equal(connectionFailure.statusCode, 401);
assert.equal(connectionFailure.didNetworkRequest, true);
assert.equal(JSON.stringify(connectionFailure).includes("test-api-key-value"), false);

const connectionForbidden = await fetchJQuantsConnectionCheck(readyConfig, {
  fetchImpl: async () => new Response(JSON.stringify({ message: "Forbidden" }), {
    status: 403,
    statusText: "Forbidden",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(connectionForbidden.ok, false);
assert.equal(connectionForbidden.mode, "connection_error");
assert.equal(connectionForbidden.statusCode, 403);
assert.equal(connectionForbidden.safeError.includes("plan"), true);
assert.equal(connectionForbidden.didNetworkRequest, true);
assert.equal(JSON.stringify(connectionForbidden).includes("test-api-key-value"), false);

assert.equal(sanitizeJQuantsError(`bad test-api-key-value x-api-key:${readyConfig.jquantsApiKey}`, readyConfig).includes("test-api-key-value"), false);

const disabledConnection = await checkJQuantsConnection(loadEnv({ processEnv: { JQUANTS_ENABLED: "false" }, envFilePath: "" }));
assert.equal(disabledConnection.mode, "mock");
assert.equal(disabledConnection.didNetworkRequest, false);
const missingKeyConnection = await checkJQuantsConnection(missingApiKeyConfig);
assert.equal(missingKeyConnection.mode, "config_error");
assert.equal(missingKeyConnection.didNetworkRequest, false);

const rawDisabled = await fetchJQuantsRawDailyBars({ code: "7203" }, loadEnv({ processEnv: { JQUANTS_ENABLED: "false", JQUANTS_API_KEY: "" }, envFilePath: "" }));
assert.equal(rawDisabled.ok, false);
assert.equal(rawDisabled.mode, "mock");
assert.equal(rawDisabled.didNetworkRequest, false);

const rawMissingKey = await fetchJQuantsRawDailyBars({ code: "7203" }, missingApiKeyConfig);
assert.equal(rawMissingKey.ok, false);
assert.equal(rawMissingKey.mode, "config_error");
assert.deepEqual(rawMissingKey.missingFields, ["JQUANTS_API_KEY"]);
assert.equal(rawMissingKey.didNetworkRequest, false);

let rawFetchCalled = false;
const rawSuccess = await fetchJQuantsRawDailyBars({ code: "7203", from: "2026-01-01", to: "2026-01-31" }, readyConfig, {
  fetchImpl: async (url, options) => {
    rawFetchCalled = true;
    const rawUrl = String(url);
    assert.equal(rawUrl.includes(JQUANTS_RAW_DAILY_BARS_ENDPOINT), true);
    assert.equal(rawUrl.includes("code=7203"), true);
    assert.equal(rawUrl.includes("from=2026-01-01"), true);
    assert.equal(rawUrl.includes("to=2026-01-31"), true);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify({
      data: [
        { Date: "2026-01-05", Code: "7203", Open: 3000, High: 3100, Low: 2990, Close: 3080, Volume: 1000 },
        { Date: "2026-01-06", Code: "7203", Open: 3080, High: 3120, Low: 3050, Close: 3100, Volume: 1200 },
        { Date: "2026-01-07", Code: "7203", Open: 3100, High: 3150, Low: 3090, Close: 3140, Volume: 1500 },
        { Date: "2026-01-08", Code: "7203", Open: 3140, High: 3160, Low: 3110, Close: 3120, Volume: 900 }
      ],
      pagination_key: "next"
    }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(rawFetchCalled, true);
assert.equal(rawSuccess.ok, true);
assert.equal(rawSuccess.mode, "raw_fetch_ok");
assert.equal(rawSuccess.didNetworkRequest, true);
assert.equal(rawSuccess.statusCode, 200);
assert.equal(rawSuccess.checkedEndpoint, JQUANTS_RAW_DAILY_BARS_ENDPOINT);
assert.equal(rawSuccess.rowCount, 4);
assert.deepEqual(rawSuccess.columns, ["Date", "Code", "Open", "High", "Low", "Close", "Volume"]);
assert.equal(rawSuccess.sampleRows.length, 3);
assert.equal("data" in rawSuccess, false);
assert.equal("rawRows" in rawSuccess, false);
assert.equal(JSON.stringify(rawSuccess).includes("test-api-key-value"), false);

const rawInternal = await fetchJQuantsRawDailyBarsInternal({ code: "7203", from: "2026-01-01", to: "2026-01-31" }, readyConfig, {
  fetchImpl: async () => new Response(JSON.stringify({
    data: Array.from({ length: 101 }, (_, index) => ({
      Date: new Date(Date.UTC(2025, 8, 1 + index)).toISOString().slice(0, 10),
      Code: "7203",
      AdjC: 1000 + index,
      AdjVo: 100000 + index
    }))
  }), {
    status: 200,
    headers: { "content-type": "application/json" }
  })
});
assert.equal(rawInternal.ok, true);
assert.equal(rawInternal.rawRows.length, 101);
assert.equal(rawInternal.rowCount, 101);

const rawSanitized = sanitizeRawDailyBarsResponse({ data: [{ A: 1 }, { A: 2 }, { A: 3 }, { A: 4 }] });
assert.equal(rawSanitized.rowCount, 4);
assert.equal(rawSanitized.sampleRows.length, 3);

const shortBars = {
  data: [
    { Date: "2026-01-05", Code: "7203", O: 100, H: 110, L: 95, C: 105, V: 1000 },
    { Date: "2026-01-06", Code: "7203", O: 105, H: 112, L: 101, C: 110, V: 1200 },
    { Date: "2026-01-07", Code: "7203", O: 110, H: 115, L: 108, C: 112, V: 1300 }
  ]
};
const mappedShort = mapJQuantsDailyBarsToStockData(shortBars, { code: "7203" });
assert.equal(mappedShort.stockData.dataSource, "J_QUANTS_MAPPED");
assert.equal(mappedShort.stockData.isMock, false);
assert.equal(mappedShort.stockData.isTradableData, false);
assert.equal(mappedShort.stockData.price, 112);
assert.equal(mappedShort.stockData.previousClose, 110);
assert.equal(mappedShort.stockData.change, 2);
assert.equal(mappedShort.stockData.changePercent, 1.82);
assert.equal(mappedShort.stockData.volume, 1300);
assert.equal(mappedShort.stockData.averageVolume20d, null);
assert.equal(mappedShort.stockData.ma25, null);
assert.equal(mappedShort.stockData.ma75, null);
assert.equal(mappedShort.stockData.rsi, null);
assert.equal(mappedShort.calculationWarnings.some((warning) => warning.includes("ma25")), true);
assert.equal(mappedShort.calculationWarnings.some((warning) => warning.includes("RSI")), true);
assert.equal(mappedShort.debugInfo.closeFieldUsed, "C");
assert.equal(mappedShort.debugInfo.volumeFieldUsed, "V");

const adjBars = {
  data: Array.from({ length: 101 }, (_, index) => ({
    Date: `2025-10-${String((index % 28) + 1).padStart(2, "0")}`,
    Code: "7203",
    AdjO: 1000 + index,
    AdjH: 1010 + index,
    AdjL: 990 + index,
    AdjC: 1000 + index,
    AdjVo: 100000 + index
  })).map((row, index) => ({
    ...row,
    Date: new Date(Date.UTC(2025, 8, 1 + index)).toISOString().slice(0, 10)
  }))
};
const mappedAdj = mapJQuantsDailyBarsToStockData(adjBars, { code: "7203" });
assert.equal(mappedAdj.stockData.price, 1100);
assert.equal(mappedAdj.stockData.volume, 100100);
assert.equal(mappedAdj.stockData.averageVolume20d != null, true);
assert.equal(mappedAdj.stockData.ma25 != null, true);
assert.equal(mappedAdj.stockData.ma75 != null, true);
assert.equal(mappedAdj.stockData.rsi != null, true);
assert.equal(mappedAdj.stockData.highYtd != null, true);
assert.equal(mappedAdj.stockData.high52w, null);
assert.equal(mappedAdj.debugInfo.closeFieldUsed, "AdjC");
assert.equal(mappedAdj.debugInfo.volumeFieldUsed, "AdjVo");
assert.equal(mappedAdj.debugInfo.validCloseCount, 101);
assert.equal(mappedAdj.debugInfo.validVolumeCount, 101);
assert.equal(mappedAdj.debugInfo.canCalculateAverageVolume20d, true);
assert.equal(mappedAdj.debugInfo.canCalculateMa25, true);
assert.equal(mappedAdj.debugInfo.canCalculateMa75, true);
assert.equal(mappedAdj.debugInfo.canCalculateRsi, true);
assert.equal(JSON.stringify(mappedAdj.debugInfo).includes("test-api-key-value"), false);

const thirtyBars = {
  data: Array.from({ length: 30 }, (_, index) => ({
    Date: `2026-02-${String(index + 1).padStart(2, "0")}`,
    Code: "7203",
    O: 100 + index,
    H: 101 + index,
    L: 99 + index,
    C: 100 + index,
    V: 1000 + index
  }))
};
const mappedThirty = mapJQuantsDailyBarsToStockData(thirtyBars, { code: "7203" });
assert.equal(mappedThirty.stockData.ma25, calculateSimpleMovingAverage(thirtyBars.data.map((row) => row.C), 25));
assert.equal(mappedThirty.stockData.rsi, calculateRsiFromCloses(thirtyBars.data.map((row) => row.C), 14));
assert.equal(mappedThirty.stockData.averageVolume20d, 1019.5);
assert.deepEqual(calculateMappedChange(105, 100), { change: 5, changePercent: 5 });

const mappedFetch = await fetchJQuantsMappedStockData({ code: "7203", from: "2026-01-01", to: "2026-01-31" }, readyConfig, {
  fetchImpl: async () => new Response(JSON.stringify(adjBars), {
    status: 200,
    headers: { "content-type": "application/json" }
  })
});
assert.equal(mappedFetch.ok, true);
assert.equal(mappedFetch.mode, "mapped_fetch_ok");
assert.equal(mappedFetch.rawRowCount, 101);
assert.equal(typeof mappedFetch.stockData.name, "string");
assert.equal(mappedFetch.stockData.market, "プライム");
assert.equal(mappedFetch.stockData.sector, "輸送用機器");
assert.equal(mappedFetch.stockData.stockMasterSource, "LOCAL_MASTER");
assert.equal(mappedFetch.stockData.stockMasterFound, true);
assert.equal(mappedFetch.debugInfo.validCloseCount, 101);
assert.equal(mappedFetch.debugInfo.validVolumeCount, 101);
assert.equal(mappedFetch.stockData.ma25 != null, true);
assert.equal(mappedFetch.stockData.ma75 != null, true);
assert.equal(mappedFetch.stockData.rsi != null, true);
assert.equal(mappedFetch.stockData.averageVolume20d != null, true);
assert.equal(mappedFetch.didNetworkRequest, true);
assert.equal("sampleRows" in mappedFetch, false);
assert.equal("rawRows" in mappedFetch, false);
assert.equal("data" in mappedFetch, false);
assert.equal(JSON.stringify(mappedFetch).includes("test-api-key-value"), false);

clearJQuantsCache();
const cacheKey = buildJQuantsCacheKey({
  code: "7203",
  from: "2025-09-01",
  to: "2026-01-31",
  endpoint: JQUANTS_RAW_DAILY_BARS_ENDPOINT,
  mode: "stocks"
});
assert.equal(cacheKey, "stocks:7203:2025-09-01:2026-01-31:/v2/equities/bars/daily");
setCachedJQuantsResult(cacheKey, {
  ok: true,
  didNetworkRequest: true,
  stockData: { code: "7203", dataSource: "J_QUANTS_MAPPED" },
  headers: { "x-api-key": "test-api-key-value" }
}, { ttlMs: 300000 }, readyConfig, Date.parse("2026-05-29T00:00:00Z"));
const cacheHit = getCachedJQuantsResult(cacheKey, readyConfig, Date.parse("2026-05-29T00:01:00Z"));
assert.equal(cacheHit.cacheHit, true);
assert.equal(cacheHit.didNetworkRequest, false);
assert.equal(cacheHit.headers, undefined);
assert.equal(JSON.stringify(cacheHit).includes("test-api-key-value"), false);
const cacheStats = getJQuantsCacheStats(readyConfig, Date.parse("2026-05-29T00:01:00Z"));
assert.equal(cacheStats.cacheEnabled, true);
assert.equal(cacheStats.entries.some((entry) => entry.key === cacheKey), true);
assert.equal(JSON.stringify(cacheStats).includes("stockData"), false);
assert.equal(getCachedJQuantsResult(cacheKey, readyConfig, Date.parse("2026-05-29T00:10:01Z")), null);
assert.equal(canMakeJQuantsRequest({ ...readyConfig, minRequestIntervalMs: 0, maxRequestsPerMinute: 999 }, Date.now()).ok, true);

const mappedFetchError = await fetchJQuantsMappedStockData({ code: "7203" }, readyConfig, {
  forceRefresh: true,
  fetchImpl: async () => new Response(JSON.stringify({ message: "Bad Request" }), {
    status: 400,
    statusText: "Bad Request",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(mappedFetchError.ok, false);
assert.equal(mappedFetchError.mode, "mapped_fetch_error");
assert.equal(mappedFetchError.didNetworkRequest, true);

clearJQuantsCache();
let cachedFetchCount = 0;
const cachedFirst = await fetchJQuantsMappedStockData({ code: "7203", from: "2025-09-01", to: "2026-01-31" }, readyConfig, {
  cacheMode: "stocks",
  fetchImpl: async () => {
    cachedFetchCount += 1;
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
const cachedSecond = await fetchJQuantsMappedStockData({ code: "7203", from: "2025-09-01", to: "2026-01-31" }, readyConfig, {
  cacheMode: "stocks",
  fetchImpl: async () => {
    cachedFetchCount += 1;
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(cachedFirst.didNetworkRequest, true);
assert.equal(cachedFirst.cacheHit, false);
assert.equal(cachedFirst.cacheStored, true);
assert.equal(cachedSecond.didNetworkRequest, false);
assert.equal(cachedSecond.cacheHit, true);
assert.equal(typeof cachedSecond.stockData.name, "string");
assert.equal(cachedSecond.stockData.market, "プライム");
assert.equal(cachedSecond.stockData.sector, "輸送用機器");
assert.equal(cachedSecond.stockData.stockMasterSource, "LOCAL_MASTER");
assert.equal(cachedFetchCount, 1);
const forceRefreshed = await fetchJQuantsMappedStockData({ code: "7203", from: "2025-09-01", to: "2026-01-31" }, readyConfig, {
  cacheMode: "stocks",
  forceRefresh: true,
  fetchImpl: async () => {
    cachedFetchCount += 1;
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(forceRefreshed.forceRefresh, true);
assert.equal(forceRefreshed.cacheHit, false);
assert.equal(cachedFetchCount, 2);

const strictRateConfig = { ...readyConfig, minRequestIntervalMs: 100000, maxRequestsPerMinute: 999 };
const rateBlocked = await fetchJQuantsMappedStockData({ code: "6758", from: "2025-09-01", to: "2026-01-31" }, strictRateConfig, {
  cacheMode: "stocks",
  forceRefresh: true,
  fetchImpl: async () => {
    throw new Error("should not fetch while rate limited");
  }
});
assert.equal(rateBlocked.ok, false);
assert.equal(rateBlocked.didNetworkRequest, false);
assert.equal(rateBlocked.statusCode, 429);
assert.equal(rateBlocked.retryAfterMs > 0, true);
const rateFallback = await getJQuantsRealOrFallbackStockData("6758", {
  ...strictRateConfig,
  useRealStocks: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async () => {
    throw new Error("should not fetch while rate limited");
  }
});
assert.equal(rateFallback.ok, true);
assert.equal(rateFallback.fallbackUsed, true);
assert.equal(rateFallback.data.dataSource, "J_QUANTS_MOCK");
assert.equal(rateFallback.data.rateLimitReason, "min_request_interval");
const rateError = await getJQuantsRealOrFallbackStockData("6758", {
  ...strictRateConfig,
  useRealStocks: true,
  fallbackToMock: false,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async () => {
    throw new Error("should not fetch while rate limited");
  }
});
assert.equal(rateError.ok, false);
assert.equal(rateError.status, 429);
assert.equal(rateError.didNetworkRequest, false);

const finsRows = {
  data: [
    {
      DisclosedDate: "2025-10-30",
      DisclosedTime: "15:00",
      LocalCode: "72030",
      TypeOfDocument: "2QFinancialStatements_Consolidated_IFRS",
      Sales: "24000000000000",
      OP: "2500000000000",
      NP: "1800000000000",
      EPS: "120.5",
      DPS: "75",
      FDSales: "47000000000000",
      FDOP: "4800000000000",
      FDNP: "3600000000000",
      FDEPS: "240.25"
    },
    {
      DisclosedDate: "2026-01-30",
      DisclosedTime: "15:30",
      LocalCode: "72030",
      TypeOfDocument: "3QFinancialStatements_Consolidated_IFRS",
      Sales: "36000000000000",
      OP: "3900000000000",
      OdP: "4000000000000",
      NP: "2900000000000",
      EPS: "190.75",
      DPS: "80",
      TA: "90000000000000",
      Eq: "40000000000000",
      EqR: "44.4",
      BPS: "2500",
      CFO: "1000",
      CFI: "-200",
      CFF: "-300",
      Cash: "5000",
      FDSales: "48000000000000",
      FDOP: "5000000000000",
      FDNP: "3700000000000",
      FDEPS: "250.5",
      FDDPS: "85"
    },
    {
      DisclosedDate: "2026-02-01",
      DisclosedTime: "12:00",
      LocalCode: "72030",
      TypeOfDocument: "CorrectionNotice"
    },
    {
      DiscDate: "2024-10-30",
      DiscTime: "15:00",
      Code: "72030",
      DocType: "OldFinancialStatements",
      Sales: "100"
    },
    {
      DisclosedDate: "2024-07-30",
      LocalCode: "72030",
      TypeOfDocument: "Older"
    }
  ]
};
const latestFins = extractLatestFinancialSummary(finsRows.data);
assert.equal(latestFins.disclosedDate, "2026-01-30");
assert.equal(latestFins.typeOfDocument, "3QFinancialStatements_Consolidated_IFRS");
assert.equal(latestFins.netSales, 36000000000000);
assert.equal(latestFins.operatingProfit, 3900000000000);
assert.equal(latestFins.ordinaryProfit, 4000000000000);
assert.equal(latestFins.profit, 2900000000000);
assert.equal(latestFins.earningsPerShare, 190.75);
assert.equal(latestFins.dividendPerShareAnnual, 80);
assert.equal(latestFins.totalAssets, 90000000000000);
assert.equal(latestFins.equity, 40000000000000);
assert.equal(latestFins.equityRatio, 44.4);
assert.equal(latestFins.bookValuePerShare, 2500);
assert.equal(latestFins.cashFlowsFromOperatingActivities, 1000);
assert.equal(latestFins.cashFlowsFromInvestingActivities, -200);
assert.equal(latestFins.cashFlowsFromFinancingActivities, -300);
assert.equal(latestFins.cashAndEquivalents, 5000);
assert.equal(latestFins.forecastNetSales, 48000000000000);
assert.equal(latestFins.forecastOperatingProfit, 5000000000000);
assert.equal(latestFins.forecastProfit, 3700000000000);
assert.equal(latestFins.forecastEarningsPerShare, 250.5);
assert.equal(latestFins.forecastDividendPerShareAnnual, 85);
assert.equal(latestFins.fieldHints.netSales, "Sales");
assert.equal(latestFins.fieldHints.operatingProfit, "OP");
assert.equal(latestFins.fieldHints.ordinaryProfit, "OdP");
assert.equal(latestFins.fieldHints.profit, "NP");
assert.equal(latestFins.fieldHints.earningsPerShare, "EPS");
assert.equal(latestFins.fieldHints.dividendPerShareAnnual, "DPS");
assert.equal(latestFins.selectedBy, "latest_row_with_financial_values");
assert.equal(latestFins.hasFinancialValues, true);
const sanitizedFins = sanitizeFinancialSummaryResponse(finsRows, { code: "7203" });
assert.equal(sanitizedFins.rowCount, 5);
assert.equal(sanitizedFins.sampleRows.length, 3);
assert.deepEqual(Object.keys(sanitizedFins.sampleRows[0]), [
  "disclosedDate",
  "disclosedTime",
  "localCode",
  "typeOfDocument",
  "sales",
  "operatingProfit",
  "profit",
  "earningsPerShare",
  "dividendPerShareAnnual"
]);
assert.equal(sanitizedFins.latestDisclosure.profit, 2900000000000);
assert.equal(sanitizedFins.importantColumns.includes("DisclosedDate"), true);
assert.equal(sanitizedFins.importantColumns.includes("Sales"), true);
assert.equal(sanitizedFins.debugInfo.latestRowSelectedBy, "latest_row_with_financial_values");
assert.equal(sanitizedFins.debugInfo.latestRowHasFinancialValues, true);
assert.equal(sanitizedFins.debugInfo.financialValueRowCount, 3);
assert.equal(sanitizedFins.debugInfo.salesFieldUsed, "Sales");
assert.equal(sanitizedFins.debugInfo.operatingProfitFieldUsed, "OP");
assert.equal(sanitizedFins.debugInfo.profitFieldUsed, "NP");
assert.equal(sanitizedFins.debugInfo.epsFieldUsed, "EPS");
assert.equal(sanitizedFins.debugInfo.dividendFieldUsed, "DPS");
assert.equal(JSON.stringify(sanitizedFins.sampleRows).includes("TA"), false);
assert.equal(JSON.stringify(sanitizedFins.sampleRows).includes("CFO"), false);
assert.equal(JSON.stringify(sanitizedFins).includes("test-api-key-value"), false);

const finsDisabled = await fetchJQuantsFinancialSummary({ code: "7203" }, loadEnv({ processEnv: { JQUANTS_ENABLED: "false", JQUANTS_API_KEY: "" }, envFilePath: "" }));
assert.equal(finsDisabled.ok, false);
assert.equal(finsDisabled.mode, "mock");
assert.equal(finsDisabled.didNetworkRequest, false);
const finsMissingKey = await fetchJQuantsFinancialSummary({ code: "7203" }, missingApiKeyConfig);
assert.equal(finsMissingKey.ok, false);
assert.equal(finsMissingKey.mode, "config_error");
assert.equal(finsMissingKey.didNetworkRequest, false);
assert.deepEqual(finsMissingKey.missingFields, ["JQUANTS_API_KEY"]);

clearJQuantsCache();
let finsFetchCount = 0;
const finsFirst = await fetchJQuantsFinancialSummary({ code: "7203" }, readyConfig, {
  fetchImpl: async (url, options) => {
    finsFetchCount += 1;
    assert.equal(String(url).includes(`${JQUANTS_FINS_SUMMARY_ENDPOINT}?code=7203`), true);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify(finsRows), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(finsFirst.ok, true);
assert.equal(finsFirst.mode, "fins_summary_ok");
assert.equal(finsFirst.didNetworkRequest, true);
assert.equal(finsFirst.cacheHit, false);
assert.equal(finsFirst.cacheStored, true);
assert.equal(finsFirst.rowCount, 5);
assert.equal(finsFirst.sampleRows.length, 3);
assert.equal(finsFirst.latestDisclosure.netSales, 36000000000000);
assert.equal(finsFirst.latestDisclosure.operatingProfit, 3900000000000);
assert.equal(finsFirst.latestDisclosure.ordinaryProfit, 4000000000000);
assert.equal(finsFirst.latestDisclosure.earningsPerShare, 190.75);
assert.equal(finsFirst.debugInfo.salesFieldUsed, "Sales");
assert.equal(JSON.stringify(finsFirst).includes("test-api-key-value"), false);
assert.equal("rawRows" in finsFirst, false);
assert.equal("data" in finsFirst, false);
const finsSecond = await fetchJQuantsFinancialSummary({ code: "7203" }, readyConfig, {
  fetchImpl: async () => {
    finsFetchCount += 1;
    throw new Error("should not fetch cached fins summary");
  }
});
assert.equal(finsSecond.cacheHit, true);
assert.equal(finsSecond.didNetworkRequest, false);
assert.equal(finsSecond.latestDisclosure.operatingProfit, 3900000000000);
assert.equal(finsFetchCount, 1);
const finsForce = await fetchJQuantsFinancialSummary({ code: "7203" }, readyConfig, {
  forceRefresh: true,
  fetchImpl: async () => {
    finsFetchCount += 1;
    return new Response(JSON.stringify(finsRows), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(finsForce.forceRefresh, true);
assert.equal(finsForce.cacheHit, false);
assert.equal(finsFetchCount, 2);
const finsInternalError = await fetchJQuantsFinancialSummaryInternal({ code: "7203" }, readyConfig, {
  fetchImpl: async () => new Response(JSON.stringify({ message: "Bad Request" }), {
    status: 400,
    statusText: "Bad Request",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(finsInternalError.ok, false);
assert.equal(finsInternalError.mode, "fins_summary_error");
assert.equal(finsInternalError.safeError.includes("Bad Request"), true);
assert.equal(JSON.stringify(finsInternalError).includes("test-api-key-value"), false);
const finsRateBlocked = await fetchJQuantsFinancialSummary({ code: "6758" }, { ...readyConfig, minRequestIntervalMs: 100000 }, {
  forceRefresh: true,
  fetchImpl: async () => {
    throw new Error("should not fetch while financial summary is rate limited");
  }
});
assert.equal(finsRateBlocked.ok, false);
assert.equal(finsRateBlocked.mode, "rate_limited");
assert.equal(finsRateBlocked.didNetworkRequest, false);
assert.equal(finsRateBlocked.statusCode, 429);

for (const [status, expected] of [
  [400, "Bad Request"],
  [401, "Unauthorized"],
  [403, "Forbidden"],
  [429, "Too Many Requests"]
]) {
  const rawError = await fetchJQuantsRawDailyBars({ code: "7203" }, readyConfig, {
    fetchImpl: async () => new Response(JSON.stringify({ message: expected }), {
      status,
      statusText: expected,
      headers: { "content-type": "application/json" }
    })
  });
  assert.equal(rawError.ok, false);
  assert.equal(rawError.mode, "raw_fetch_error");
  assert.equal(rawError.didNetworkRequest, true);
  assert.equal(rawError.safeError.includes(expected), true);
  assert.equal(JSON.stringify(rawError).includes("test-api-key-value"), false);
}

assert.equal(DEFAULT_RAW_FROM, "2026-01-01");
assert.equal(DEFAULT_RAW_TO, "2026-01-31");

const originalFetch = globalThis.fetch;
globalThis.fetch = async () => {
  throw new Error("connection refused");
};
const offlineHealth = await getBackendHealth("http://127.0.0.1:65530");
assert.equal(offlineHealth.ok, false);
assert.equal(offlineHealth.didExternalRequest, false);
assert.equal(typeof offlineHealth.error, "string");
globalThis.fetch = originalFetch;

const backendClientStatus = getServerJQuantsStatus(loadEnv({ processEnv: { JQUANTS_ENABLED: "false", JQUANTS_API_KEY: "" }, envFilePath: "" }));
assert.equal(backendClientStatus.enabled, false);
assert.equal(backendClientStatus.didNetworkRequest, false);
assert.equal(backendClientStatus.mode, "mock");

const configErrorStatus = getServerJQuantsStatus(missingApiKeyConfig);
assert.equal(configErrorStatus.ok, false);
assert.equal(configErrorStatus.mode, "config_error");
assert.equal(configErrorStatus.apiVersion, "v2");
assert.deepEqual(configErrorStatus.missingFields, ["JQUANTS_API_KEY"]);
assert.equal(JSON.stringify(configErrorStatus).includes("test-api-key-value"), false);

const apiKeyReadyStatus = getServerJQuantsStatus(readyConfig);
assert.equal(apiKeyReadyStatus.ok, true);
assert.equal(apiKeyReadyStatus.mode, "api_key_ready");
assert.equal(apiKeyReadyStatus.apiVersion, "v2");
assert.equal(apiKeyReadyStatus.config.hasApiKey, true);
assert.equal(apiKeyReadyStatus.didNetworkRequest, false);
assert.equal(JSON.stringify(apiKeyReadyStatus).includes("test-api-key-value"), false);

const backendMock = await getBackendJQuantsStockData("7203", loadEnv({ processEnv: { JQUANTS_ENABLED: "false", JQUANTS_API_KEY: "" }, envFilePath: "" }));
assert.equal(backendMock.ok, true);
assert.equal(backendMock.data.dataSource, "J_QUANTS_MOCK");
assert.equal(backendMock.data.isMock, true);
assert.equal(backendMock.data.isTradableData, false);
const backendMockScore = calculateScore(backendMock.data, calculateIndicators(backendMock.data, today));
assert.equal(typeof backendMockScore.totalScore, "number");

const configErrorStock = await getBackendJQuantsStockData("7203", { ...missingApiKeyConfig, useRealStocks: true, fallbackToMock: false });
assert.equal(configErrorStock.ok, false);
assert.equal(configErrorStock.didNetworkRequest, false);
assert.deepEqual(configErrorStock.missingFields, ["JQUANTS_API_KEY"]);

const apiKeyReadyStock = await getBackendJQuantsStockData("7203", readyConfig);
assert.equal(apiKeyReadyStock.ok, true);
assert.equal(apiKeyReadyStock.didNetworkRequest, false);
assert.equal(apiKeyReadyStock.mode, "mock");

const realModeOff = await getBackendJQuantsStockData("7203", { ...readyConfig, useRealStocks: false });
assert.equal(realModeOff.data.dataSource, "J_QUANTS_MOCK");
assert.equal(realModeOff.didNetworkRequest, false);

clearJQuantsCache();
const realModeSuccess = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async () => new Response(JSON.stringify(adjBars), {
    status: 200,
    headers: { "content-type": "application/json" }
  })
});
assert.equal(realModeSuccess.ok, true);
assert.equal(realModeSuccess.mode, "real_stock_ok");
assert.equal(realModeSuccess.didNetworkRequest, true);
assert.equal(realModeSuccess.data.dataSource, "J_QUANTS_MAPPED");
assert.equal(realModeSuccess.data.isMock, false);
assert.equal(realModeSuccess.data.isTradableData, false);
assert.equal(realModeSuccess.data.tradableDataLabel, "J-Quants\u5b9f\u30c7\u30fc\u30bf\u30fb\u8981\u78ba\u8a8d");
assert.equal(realModeSuccess.data.ma25 != null, true);
assert.equal(realModeSuccess.data.ma75 != null, true);
assert.equal(realModeSuccess.data.rsi != null, true);
assert.equal("financialSummary" in realModeSuccess.data, false);
assert.equal(realModeSuccess.data.financialSummaryStatus.enabled, false);
assert.equal(realModeSuccess.cacheKey.includes("financials-off"), true);
assert.equal(JSON.stringify(realModeSuccess).includes("test-api-key-value"), false);

clearJQuantsCache();
let financialIntegratedFetchCount = 0;
const realModeWithFinancials = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  useFinancials: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async (url) => {
    financialIntegratedFetchCount += 1;
    if (String(url).includes(JQUANTS_FINS_SUMMARY_ENDPOINT)) {
      return new Response(JSON.stringify(finsRows), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(realModeWithFinancials.ok, true);
assert.equal(realModeWithFinancials.mode, "real_stock_ok");
assert.equal(realModeWithFinancials.didNetworkRequest, true);
assert.equal(realModeWithFinancials.data.financialSummary.available, true);
assert.equal(realModeWithFinancials.data.financialSummary.netSales, 36000000000000);
assert.equal(realModeWithFinancials.data.financialSummary.operatingProfit, 3900000000000);
assert.equal(realModeWithFinancials.data.financialSummary.profit, 2900000000000);
assert.equal(realModeWithFinancials.data.financialSummary.earningsPerShare, 190.75);
assert.equal(realModeWithFinancials.data.financialSignals.hasFinancialSummary, true);
assert.equal(realModeWithFinancials.data.financialSignals.financialScore, 5);
assert.equal(realModeWithFinancials.data.financialSignals.hasPositiveOperatingCashFlow, true);
assert.equal(realModeWithFinancials.data.useFinancialScore, true);
assert.equal(realModeWithFinancials.cacheKey.includes("financials-on"), true);
assert.equal(financialIntegratedFetchCount, 2);
const financialScore = calculateScore(realModeWithFinancials.data, calculateIndicators(realModeWithFinancials.data, today));
const noFinancialScore = calculateScore(realModeSuccess.data, calculateIndicators(realModeSuccess.data, today));
assert.equal(financialScore.financialScore, 5);
assert.equal(financialScore.appliedFinancialScore, 5);
assert.equal(financialScore.totalScore, noFinancialScore.totalScore + 5);
assert.equal(financialScore.entries.some((entry) => entry.label === "財務参考評価" && entry.value === 5), true);
const financialScoreDisabled = calculateScore({
  ...realModeWithFinancials.data,
  useFinancialScore: false
}, calculateIndicators(realModeWithFinancials.data, today));
assert.equal(financialScoreDisabled.financialScore, 5);
assert.equal(financialScoreDisabled.appliedFinancialScore, 0);
assert.equal(financialScoreDisabled.totalScore, noFinancialScore.totalScore);
const financialReasonSummary = buildReasonSummary(realModeWithFinancials.data, calculateIndicators(realModeWithFinancials.data, today), financialScore);
assert.equal(JSON.stringify(financialReasonSummary).length > 0, true);
assert.equal(JSON.stringify(financialReasonSummary).includes("TDnet"), true);
const structuredFinancialSummary = buildStructuredSummary(realModeWithFinancials.data, financialScore, {
  indicators: calculateIndicators(realModeWithFinancials.data, today),
  summary: financialReasonSummary
});
assert.equal(structuredFinancialSummary.generatedBy, "RULE_BASED");
assert.equal(structuredFinancialSummary.aiReady, true);
assert.equal(structuredFinancialSummary.aiGenerated, false);
assert.equal(typeof structuredFinancialSummary.decision.label, "string");
assert.equal(structuredFinancialSummary.technical.price, realModeWithFinancials.data.price);
assert.equal(structuredFinancialSummary.financial.available, true);
assert.equal(structuredFinancialSummary.financial.score, 5);
assert.equal(realModeWithFinancials.data.themeSummary.available, true);
assert.equal(realModeWithFinancials.data.themeSummary.externalNewsApiUsed, false);
assert.equal(realModeWithFinancials.data.themeSummary.externalAiUsed, false);
assert.equal(Array.isArray(structuredFinancialSummary.theme.themes), true);
assert.equal(structuredFinancialSummary.theme.externalNewsApiUsed, false);
assert.equal(Array.isArray(structuredFinancialSummary.positives), true);
assert.equal(Array.isArray(structuredFinancialSummary.cautions), true);
assert.equal(structuredFinancialSummary.positives.some((item) => item.includes("テーマ性")), true);
assert.equal(structuredFinancialSummary.cautions.some((item) => item.includes("外部ニュースAPI")), true);
assert.equal(Array.isArray(structuredFinancialSummary.entryPlan.ifBuying), true);
assert.equal(JSON.stringify(structuredFinancialSummary.aiPromptPayload).includes("test-api-key-value"), false);
assert.equal(JSON.stringify(structuredFinancialSummary.aiPromptPayload).includes("x-api-key"), false);
assert.equal(JSON.stringify(structuredFinancialSummary.aiPromptPayload).includes("rawRows"), false);
const preTradeCheck = buildPreTradeCheck(realModeWithFinancials.data, {
  indicators: calculateIndicators(realModeWithFinancials.data, today),
  scoreResult: financialScore,
  structuredSummary: structuredFinancialSummary
});
assert.equal(preTradeCheck.available, true);
assert.equal(preTradeCheck.tradeAdvice, false);
assert.equal(typeof preTradeCheck.overallStatus, "string");
assert.equal(preTradeCheck.dataSource.label, "J-Quants実データ");
assert.equal(preTradeCheck.financial.available, true);
assert.equal(preTradeCheck.newsAndDisclosure.newsApiConnected, false);
assert.equal(preTradeCheck.newsAndDisclosure.tdnetConnected, false);
assert.equal(Array.isArray(preTradeCheck.checklist), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "official_price_check"), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "ir_check"), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "tdnet_check"), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "news_check"), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "entry_plan_check"), true);
assert.equal(preTradeCheck.checklist.some((item) => item.id === "loss_rule_check"), true);
assert.equal(JSON.stringify(preTradeCheck).includes("JQUANTS_API_KEY"), false);
assert.equal(JSON.stringify(preTradeCheck).includes("headers"), false);
assert.equal(JSON.stringify(preTradeCheck).includes("rawRows"), false);
const preTradeMock = buildPreTradeCheck({ ...toyota, isMock: true, dataSource: "MOCK" });
assert.equal(preTradeMock.overallStatus, "モックのため実売買不可");
const preTradeCsv = buildPreTradeCheck({ ...csvStock, dataSource: "CSV", isMock: false });
assert.equal(preTradeCsv.overallStatus, "CSVデータのため公式情報確認必須");
const preTradeNoFinancial = buildPreTradeCheck({ ...realModeSuccess.data, financialSummary: { available: false } });
assert.equal(preTradeNoFinancial.financial.available, false);
assert.equal(PreTradeCheckPanel(undefined), "");
assert.equal(PreTradeCheckPanel(preTradeCheck, { code: "7203", checkedItemIds: ["ir_check"] }).includes("実売買前チェック"), true);
assert.equal(PreTradeCheckPanel(preTradeCheck).includes("名乗り警告"), false);
assert.equal(financialScore.totalScore, calculateScore(realModeWithFinancials.data, calculateIndicators(realModeWithFinancials.data, today)).totalScore);
const neutralFinancialStock = {
  ...realModeWithFinancials.data,
  price: 3300,
  ma25: 3200,
  ma75: 3000,
  rsi: 55,
  high52w: 4000
};
const neutralFinancialScore = calculateScore(neutralFinancialStock, calculateIndicators(neutralFinancialStock, today));
const neutralStructuredSummary = buildStructuredSummary(neutralFinancialStock, neutralFinancialScore, {
  indicators: calculateIndicators(neutralFinancialStock, today)
});
assert.equal(["買い候補", "押し目待ち"].includes(neutralStructuredSummary.decision.label), true);
const noFinancialStructuredSummary = buildStructuredSummary({
  ...realModeSuccess.data,
  financialSummaryStatus: { enabled: false }
}, noFinancialScore, {
  indicators: calculateIndicators(realModeSuccess.data, today)
});
assert.equal(noFinancialStructuredSummary.financial.available, false);
assert.equal(noFinancialStructuredSummary.financial.label, "財務未取得");
assert.equal(noFinancialScore.totalScore, calculateScore(realModeSuccess.data, calculateIndicators(realModeSuccess.data, today)).totalScore);
const negativeFinancialEvaluation = calculateFinancialScore({
  financialSummary: {
    available: true,
    operatingProfit: -1,
    profit: -1,
    earningsPerShare: -1,
    cashFlowsFromOperatingActivities: -1,
    dividendPerShareAnnual: null
  }
});
assert.equal(negativeFinancialEvaluation.score, -5);
const unavailableFinancialEvaluation = calculateFinancialScore({ financialSummary: { available: false } });
assert.equal(unavailableFinancialEvaluation.score, 0);
const overheatedFinancialStock = {
  ...realModeWithFinancials.data,
  rsi: 85,
  price: 3900,
  ma25: 3400,
  high52w: 3920
};
const overheatedFinancialScore = calculateScore(overheatedFinancialStock, calculateIndicators(overheatedFinancialStock, today));
const overheatedStructuredSummary = buildStructuredSummary(overheatedFinancialStock, overheatedFinancialScore, {
  indicators: calculateIndicators(overheatedFinancialStock, today)
});
assert.equal(overheatedFinancialScore.warnings.length > 0, true);
assert.notEqual(overheatedFinancialScore.signal, "買い候補・強い");
assert.notEqual(overheatedStructuredSummary.decision.label, "買い候補");
assert.equal(formatLargeYen(3_807_640_000_000), "3.8兆円");
assert.equal(formatLargeYen(120_000_000), "1.2億円");
assert.equal(formatLargeYen(null), "未取得");
assert.equal(formatLargeYen(undefined), "未取得");
assert.equal(formatLargeYen(""), "未取得");
assert.equal(formatLargeYen(Number.NaN), "未取得");
assert.equal(formatPerShareYen(232.55), "232.55円");
assert.equal(formatPerShareYen(null), "未取得");
assert.equal(typeof FinancialSummaryPanel, "function");
assert.equal(FinancialSummaryPanel(realModeWithFinancials.data).includes("財務参考評価"), true);
assert.equal(FinancialSummaryPanel({}).includes("財務サマリー"), true);
assert.equal(StructuredSummaryPanel(structuredFinancialSummary).includes("判断サマリー"), true);
assert.equal(StructuredSummaryPanel(structuredFinancialSummary).includes("AI要約"), true);
assert.equal(CompactStatusBar({
  ok: true,
  checked: true,
  jquantsEnabled: true,
  useRealStocks: true,
  useFinancials: true
}).includes("接続状態"), true);
assert.equal(PrimaryDecisionCard({
  stock: realModeWithFinancials.data,
  scoreResult: financialScore,
  structuredSummary: structuredFinancialSummary
}).includes("総合スコア"), true);
assert.equal(PrimaryDecisionCard({
  stock: realModeWithFinancials.data,
  scoreResult: financialScore,
  structuredSummary: undefined
}).includes("総合スコア"), true);
assert.equal(KeyMetricsGrid({
  stock: realModeWithFinancials.data,
  indicators: calculateIndicators(realModeWithFinancials.data, today),
  scoreResult: financialScore
}).includes("テーマ数"), true);
const closedDetails = CollapsibleSection({ title: "テクニカル詳細", children: "<p>detail</p>" });
const openDetails = CollapsibleSection({ title: "接続詳細", defaultOpen: true, children: "<p>detail</p>" });
assert.equal(closedDetails.includes("<details"), true);
assert.equal(closedDetails.includes("open"), false);
assert.equal(openDetails.includes("open"), true);
assert.equal(StructuredSummaryPanel(undefined), "");
assert.equal(AiSummaryMockPanel(undefined), "");
assert.equal(ThemeSummaryPanel(undefined), "");
assert.equal(FavoriteStocksPanel({ favorites: undefined }).includes("お気に入り銘柄"), true);
assert.equal(FavoriteStocksPanel({
  favorites: [{ code: "7203", name: "トヨタ自動車", market: "プライム", sector: "輸送用機器" }],
  currentCode: "7203",
  currentIsFavorite: true
}).includes("data-favorite-analyze=\"7203\""), true);
assert.equal(RecentStocksPanel({ recentStocks: undefined }).includes("最近見た銘柄"), true);
assert.equal(RecentStocksPanel({
  recentStocks: [{ code: "7203", name: "トヨタ自動車", market: "プライム", sector: "輸送用機器" }],
  currentCode: "7203"
}).includes("data-recent-analyze=\"7203\""), true);
assert.equal(RecentStocksPanel({
  recentStocks: [{ code: "7203", name: "トヨタ自動車" }]
}).includes("data-recent-remove=\"7203\""), true);
assert.equal(StockMasterCsvPanel({ rows: undefined }).includes("銘柄マスターCSV"), true);
assert.equal(StockMasterCsvPanel({ rows: undefined }).includes("stockMasterCsvEncoding"), true);
assert.equal(StockMasterCsvPanel({ rows: undefined }).includes("downloadStockMasterTemplateBtn"), true);
assert.equal(StockMasterCsvPanel({ rows: undefined }).includes("fetchJquantsMasterMockBtn"), true);
assert.equal(StockMasterCsvPanel({ rows: undefined }).includes("dryRunJquantsMasterBtn"), true);
assert.equal(StockMasterCsvPanel({
  rows: normalizedJquantsMaster,
  meta: {
    source: "JQUANTS_MOCK",
    count: normalizedJquantsMaster.length,
    lastSyncSource: "JQUANTS_MOCK",
    lastSyncCount: normalizedJquantsMaster.length,
    lastSyncAt: "2026-06-01T00:00:00.000Z"
  },
  dryRunResult: jquantsMasterDryRun
}).includes("J-Quants取得 Dry-run結果"), true);
assert.equal(StockMasterCsvPanel({
  rows: normalizedJquantsMaster,
  meta: { source: "JQUANTS_MOCK", lastSyncSource: "JQUANTS_MOCK", lastSyncCount: 9 }
}).includes("Current Source"), true);
assert.equal(StockMasterCsvPanel({
  rows: [{ code: "9434", name: "ソフトバンク", market: "プライム", sector: "情報・通信業", source: "CSV_MASTER" }]
}).includes("CSV_MASTER"), true);
const longUiAiSummary = AiSummaryMockPanel({
  title: "AI要約プレビュー（モック）",
  shortComment: "1文目です。2文目です。3文目です。4文目です。",
  bullets: ["要点1", "要点2", "要点3", "要点4", "要点5"],
  warnings: ["注意1", "注意2", "注意3", "注意4"]
});
assert.equal(longUiAiSummary.includes("4文目です"), false);
assert.equal(longUiAiSummary.includes("要点5"), false);
assert.equal(longUiAiSummary.includes("注意4"), false);
assert.equal(StructuredSummaryPanel(structuredFinancialSummary).includes("判断サマリー"), true);
assert.equal(StructuredSummaryPanel(structuredFinancialSummary).includes("外部AI APIには接続していません"), true);
const aiSummaryMock = buildAiSummaryMock(structuredFinancialSummary);
assert.equal(aiSummaryMock.available, true);
assert.equal(aiSummaryMock.mode, "rule_based_mock");
assert.equal(aiSummaryMock.aiGenerated, false);
assert.equal(aiSummaryMock.externalApiUsed, false);
assert.equal(aiSummaryMock.provider, "none");
assert.equal(typeof aiSummaryMock.shortComment, "string");
assert.equal(aiSummaryMock.shortComment.length > 20, true);
assert.equal(Array.isArray(aiSummaryMock.bullets), true);
assert.equal(Array.isArray(aiSummaryMock.warnings), true);
assert.equal(aiSummaryMock.shortComment.includes("テーマ"), true);
assert.equal(aiSummaryMock.bullets.some((bullet) => bullet.includes("テーマ")), true);
assert.equal(aiSummaryMock.warnings.some((warning) => warning.includes("外部ニュースAPI")), true);
assert.equal(aiSummaryMock.warnings.some((warning) => warning.includes("ルールベース")), true);
assert.equal(JSON.stringify(aiSummaryMock).includes("test-api-key-value"), false);
assert.equal(JSON.stringify(aiSummaryMock).includes("x-api-key"), false);
assert.equal(JSON.stringify(aiSummaryMock).includes("rawRows"), false);
const aiSummaryBeforeScore = financialScore.totalScore;
buildAiSummaryMock(structuredFinancialSummary);
assert.equal(financialScore.totalScore, aiSummaryBeforeScore);
const waitAiSummary = buildAiSummaryMock({
  ...structuredFinancialSummary,
  decision: { label: "押し目待ち" }
});
assert.equal(waitAiSummary.shortComment.includes("押し目"), true);
const highGrabAiSummary = buildAiSummaryMock({
  ...structuredFinancialSummary,
  decision: { label: "高値掴み注意" },
  risks: { highGrabRisk: "high", comment: "高値掴みリスクがあります。" }
});
assert.equal(highGrabAiSummary.shortComment.includes("高値掴み"), true);
const insufficientAiSummary = buildAiSummaryMock({
  ...structuredFinancialSummary,
  decision: { label: "データ不足" },
  stock: { code: "TEST" }
});
assert.equal(insufficientAiSummary.shortComment.includes("判断材料"), true);
const disabledAiSummary = buildAiSummaryMock(structuredFinancialSummary, { enabled: false });
assert.equal(disabledAiSummary.enabled, false);
assert.equal(disabledAiSummary.externalApiUsed, false);
const sanitizedAiInput = sanitizeAiSummaryInput({
  ...structuredFinancialSummary,
  rawRows: [{ secret: "row" }],
  headers: { "x-api-key": "test-api-key-value" },
  localStorage: { token: "secret" }
});
assert.equal(JSON.stringify(sanitizedAiInput).includes("test-api-key-value"), false);
assert.equal(JSON.stringify(sanitizedAiInput).includes("rawRows"), false);
assert.equal(AiSummaryMockPanel(aiSummaryMock).includes("AI要約プレビュー"), true);
assert.equal(AiSummaryMockPanel(aiSummaryMock).includes("外部AI未接続"), true);
assert.equal(JSON.stringify(realModeWithFinancials).includes("test-api-key-value"), false);
const cachedRealModeWithFinancials = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  useFinancials: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  fetchImpl: async () => {
    throw new Error("should not fetch while stock and financial summaries are cached");
  }
});
assert.equal(cachedRealModeWithFinancials.data.cacheHit, true);
assert.equal(cachedRealModeWithFinancials.data.financialSummary.cacheHit, true);
assert.equal(cachedRealModeWithFinancials.didNetworkRequest, false);

await new Promise((resolve) => setTimeout(resolve, 10));
clearJQuantsCache();
let financialWaitFetchCount = 0;
const realModeFinancialWait = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  useFinancials: true,
  fallbackToMock: true,
  minRequestIntervalMs: 5,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  financialRateLimitMaxWaitMs: 100,
  fetchImpl: async (url) => {
    financialWaitFetchCount += 1;
    if (String(url).includes(JQUANTS_FINS_SUMMARY_ENDPOINT)) {
      return new Response(JSON.stringify(finsRows), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(realModeFinancialWait.ok, true);
assert.equal(realModeFinancialWait.data.financialSummary.available, true);
assert.equal(realModeFinancialWait.data.financialSummary.netSales, 36000000000000);
assert.equal(financialWaitFetchCount, 2);

const tooLongWait = await waitForJQuantsRateLimitIfNeeded({ ...readyConfig, minRequestIntervalMs: 100000 }, { maxWaitMs: 1 });
assert.equal(tooLongWait.ok, false);
assert.equal(tooLongWait.reason, "min_request_interval");

clearJQuantsCache();
const realModeFinancialFailure = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  useFinancials: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async (url) => {
    if (String(url).includes(JQUANTS_FINS_SUMMARY_ENDPOINT)) {
      return new Response(JSON.stringify({ message: "Forbidden" }), {
        status: 403,
        statusText: "Forbidden",
        headers: { "content-type": "application/json" }
      });
    }
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  }
});
assert.equal(realModeFinancialFailure.ok, true);
assert.equal(realModeFinancialFailure.data.dataSource, "J_QUANTS_MAPPED");
assert.equal(realModeFinancialFailure.data.financialSummary.available, false);
assert.equal(realModeFinancialFailure.data.financialSummaryUnavailable, true);
assert.equal(realModeFinancialFailure.data.financialSummary.safeError.includes("Forbidden"), true);
assert.equal(realModeFinancialFailure.data.financialSignals.hasFinancialSummary, false);

const realModeFallback = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  fallbackToMock: true,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async () => new Response(JSON.stringify({ message: "Bad Request" }), {
    status: 400,
    statusText: "Bad Request",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(realModeFallback.ok, true);
assert.equal(realModeFallback.fallbackUsed, true);
assert.equal(realModeFallback.didNetworkRequest, true);
assert.equal(realModeFallback.data.dataSource, "J_QUANTS_MOCK");
assert.equal(realModeFallback.data.fallbackUsed, true);
assert.equal(JSON.stringify(realModeFallback).includes("test-api-key-value"), false);

const realModeError = await getJQuantsRealOrFallbackStockData("7203", {
  ...readyConfig,
  useRealStocks: true,
  fallbackToMock: false,
  realStockFrom: "2025-09-01",
  realStockTo: "2026-01-31"
}, {
  forceRefresh: true,
  fetchImpl: async () => new Response(JSON.stringify({ message: "Bad Request" }), {
    status: 400,
    statusText: "Bad Request",
    headers: { "content-type": "application/json" }
  })
});
assert.equal(realModeError.ok, false);
assert.equal(realModeError.fallbackUsed, false);
assert.equal(realModeError.didNetworkRequest, true);

const server = createServer();
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const { port } = server.address();
const backendBaseUrl = `http://127.0.0.1:${port}`;
const originalJquantsEnv = {
  JQUANTS_ENABLED: process.env.JQUANTS_ENABLED,
  JQUANTS_API_VERSION: process.env.JQUANTS_API_VERSION,
  JQUANTS_API_KEY: process.env.JQUANTS_API_KEY,
  JQUANTS_USE_REAL_STOCKS: process.env.JQUANTS_USE_REAL_STOCKS,
  JQUANTS_FALLBACK_TO_MOCK: process.env.JQUANTS_FALLBACK_TO_MOCK,
  JQUANTS_REAL_STOCK_FROM: process.env.JQUANTS_REAL_STOCK_FROM,
  JQUANTS_REAL_STOCK_TO: process.env.JQUANTS_REAL_STOCK_TO,
  JQUANTS_CACHE_ENABLED: process.env.JQUANTS_CACHE_ENABLED,
  JQUANTS_CACHE_TTL_MS: process.env.JQUANTS_CACHE_TTL_MS,
  JQUANTS_MIN_REQUEST_INTERVAL_MS: process.env.JQUANTS_MIN_REQUEST_INTERVAL_MS,
  JQUANTS_MAX_REQUESTS_PER_MINUTE: process.env.JQUANTS_MAX_REQUESTS_PER_MINUTE,
  JQUANTS_USE_FINANCIALS: process.env.JQUANTS_USE_FINANCIALS,
  JQUANTS_FINANCIALS_FALLBACK_SILENT: process.env.JQUANTS_FINANCIALS_FALLBACK_SILENT,
  JQUANTS_USE_FINANCIAL_SCORE: process.env.JQUANTS_USE_FINANCIAL_SCORE,
  AI_SUMMARY_MOCK_ENABLED: process.env.AI_SUMMARY_MOCK_ENABLED,
  AI_SUMMARY_EXTERNAL_API_ENABLED: process.env.AI_SUMMARY_EXTERNAL_API_ENABLED,
  THEME_SUMMARY_MOCK_ENABLED: process.env.THEME_SUMMARY_MOCK_ENABLED,
  THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED: process.env.THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED,
  THEME_SUMMARY_SCORE_ENABLED: process.env.THEME_SUMMARY_SCORE_ENABLED
};

try {
  process.env.JQUANTS_ENABLED = "false";
  process.env.JQUANTS_API_VERSION = "v2";
  process.env.JQUANTS_API_KEY = "";
  process.env.JQUANTS_USE_REAL_STOCKS = "false";
  process.env.JQUANTS_FALLBACK_TO_MOCK = "true";
  process.env.JQUANTS_CACHE_ENABLED = "true";
  process.env.JQUANTS_CACHE_TTL_MS = "300000";
  process.env.AI_SUMMARY_MOCK_ENABLED = "true";
  process.env.AI_SUMMARY_EXTERNAL_API_ENABLED = "false";
  process.env.THEME_SUMMARY_MOCK_ENABLED = "true";
  process.env.THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED = "false";
  process.env.THEME_SUMMARY_SCORE_ENABLED = "false";
  process.env.JQUANTS_MIN_REQUEST_INTERVAL_MS = "0";
  process.env.JQUANTS_MAX_REQUESTS_PER_MINUTE = "999";
  process.env.JQUANTS_USE_FINANCIALS = "false";
  process.env.JQUANTS_FINANCIALS_FALLBACK_SILENT = "true";

  const healthResponse = await fetch(`${backendBaseUrl}/api/health`).then((response) => response.json());
  assert.equal(healthResponse.ok, true);
  assert.equal(healthResponse.themeSummary.mockEnabled, true);
  assert.equal(healthResponse.themeSummary.externalNewsApiEnabled, false);
  assert.equal(healthResponse.themeSummary.scoreEnabled, false);
  assert.equal(healthResponse.externalApiEnabled, false);
  assert.equal(healthResponse.didNetworkRequest, false);
  assert.equal(healthResponse.apiVersion, "v2");

  const statusResponse = await fetch(`${backendBaseUrl}/api/jquants/status`).then((response) => response.json());
  assert.equal(statusResponse.enabled, false);
  assert.equal(statusResponse.didNetworkRequest, false);
  assert.equal(statusResponse.mode, "mock");
  assert.equal(statusResponse.apiVersion, "v2");
  assert.equal(statusResponse.config.hasApiKey, false);
  assert.equal(statusResponse.config.cacheEnabled, true);
  assert.equal(statusResponse.config.cacheTtlMs, 300000);
  assert.equal(statusResponse.config.aiSummary.mockEnabled, true);
  assert.equal(statusResponse.config.aiSummary.externalApiEnabled, false);
  assert.equal(statusResponse.config.themeSummary.mockEnabled, true);
  assert.equal(statusResponse.config.themeSummary.externalNewsApiEnabled, false);
  assert.equal(statusResponse.config.themeSummary.scoreEnabled, false);
  assert.equal(JSON.stringify(statusResponse).includes("secret"), false);

  const masterApi = await fetch(`${backendBaseUrl}/api/stocks/master/7203`).then((response) => response.json());
  assert.equal(masterApi.ok, true);
  assert.equal(masterApi.found, true);
  assert.equal(typeof masterApi.master.name, "string");
  assert.equal(masterApi.master.market, "プライム");
  const missingMasterApi = await fetch(`${backendBaseUrl}/api/stocks/master/9999`).then((response) => response.json());
  assert.equal(missingMasterApi.ok, true);
  assert.equal(missingMasterApi.found, false);
  const masterStatusApi = await fetch(`${backendBaseUrl}/api/stocks/master/status`).then((response) => response.json());
  assert.equal(masterStatusApi.ok, true);
  assert.equal(masterStatusApi.count >= 4, true);
  assert.equal(masterStatusApi.codes.includes("7203"), true);

  const masterSyncDryRunApi = await fetch(`${backendBaseUrl}/api/master-sync/dry-run?source=JQUANTS_MOCK`).then((response) => response.json());
  assert.equal(masterSyncDryRunApi.ok, true);
  assert.equal(masterSyncDryRunApi.source, "JQUANTS_MOCK");
  assert.equal(masterSyncDryRunApi.didNetworkRequest, false);
  assert.equal(masterSyncDryRunApi.count, 9);
  assert.equal(masterSyncDryRunApi.sampleRows.length > 0, true);
  const masterSyncApiResponse = await fetch(`${backendBaseUrl}/api/master-sync/sync`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ source: "JQUANTS_MOCK" })
  });
  const masterSyncApi = await masterSyncApiResponse.json();
  assert.equal(masterSyncApiResponse.status, 200);
  assert.equal(masterSyncApi.ok, true);
  assert.equal(masterSyncApi.source, "JQUANTS_MOCK");
  assert.equal(masterSyncApi.didNetworkRequest, false);
  assert.equal(masterSyncApi.count, 9);
  assert.equal(Array.isArray(masterSyncApi.records), true);
  assert.equal(masterSyncApi.records.some((row) => row.code === "7203"), true);
  const masterSyncRealResponse = await fetch(`${backendBaseUrl}/api/master-sync/dry-run?source=JQUANTS_REAL`);
  const masterSyncReal = await masterSyncRealResponse.json();
  assert.equal(masterSyncRealResponse.status, 501);
  assert.equal(masterSyncReal.ok, false);
  assert.equal(masterSyncReal.error.includes("JQUANTS_REAL is not implemented"), true);
  assert.equal(masterSyncReal.didNetworkRequest, false);

  const stockResponse = await fetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  assert.equal(stockResponse.ok, true);
  assert.equal(stockResponse.dataSource, "J_QUANTS_MOCK");
  assert.equal(stockResponse.isTradableData, false);
  assert.equal(stockResponse.didNetworkRequest, false);
  assert.equal(stockResponse.structuredSummary.generatedBy, "RULE_BASED");
  assert.equal(stockResponse.structuredSummary.aiReady, true);
  assert.equal(stockResponse.structuredSummary.aiGenerated, false);
  assert.equal(stockResponse.structuredSummary.aiPromptPayload.data.code, "7203");
  assert.equal(JSON.stringify(stockResponse.structuredSummary).includes("secret"), false);
  assert.equal(JSON.stringify(stockResponse.structuredSummary).includes("rawRows"), false);
  assert.equal(stockResponse.aiSummary.mode, "rule_based_mock");
  assert.equal(stockResponse.aiSummary.aiGenerated, false);
  assert.equal(stockResponse.aiSummary.externalApiUsed, false);
  assert.equal(stockResponse.aiSummary.provider, "none");
  assert.equal(typeof stockResponse.aiSummary.shortComment, "string");
  assert.equal(Array.isArray(stockResponse.aiSummary.bullets), true);
  assert.equal(Array.isArray(stockResponse.aiSummary.warnings), true);
  assert.equal(JSON.stringify(stockResponse.aiSummary).includes("secret"), false);
  assert.equal(JSON.stringify(stockResponse.aiSummary).includes("rawRows"), false);

  const stockListResponse = await fetch(`${backendBaseUrl}/api/stocks?codes=7203,6758`).then((response) => response.json());
  assert.equal(stockListResponse.ok, true);
  assert.equal(stockListResponse.count, 2);

  const notFoundResponse = await fetch(`${backendBaseUrl}/api/stocks/NOPE`);
  const notFoundBody = await notFoundResponse.json();
  assert.equal(notFoundResponse.status, 404);
  assert.equal(notFoundBody.ok, false);
  assert.equal(notFoundBody.error.includes("NOPE"), true);

  const frontendHealth = await getBackendHealth(backendBaseUrl);
  assert.equal(frontendHealth.ok, true);
  assert.equal(frontendHealth.didExternalRequest, false);
  assert.equal(frontendHealth.didNetworkRequest, false);

  const frontendStatus = await getBackendJQuantsStatus(backendBaseUrl);
  assert.equal(frontendStatus.ok, true);
  assert.equal(frontendStatus.mode, "mock");
  assert.equal(frontendStatus.apiVersion, "v2");
  assert.equal(frontendStatus.didNetworkRequest, false);

  const frontendMasterSyncDryRun = await getBackendMasterSyncDryRun("JQUANTS_MOCK", backendBaseUrl);
  assert.equal(frontendMasterSyncDryRun.ok, true);
  assert.equal(frontendMasterSyncDryRun.source, "JQUANTS_MOCK");
  assert.equal(frontendMasterSyncDryRun.didNetworkRequest, false);
  const frontendMasterSync = await postBackendMasterSync("JQUANTS_MOCK", backendBaseUrl);
  assert.equal(frontendMasterSync.ok, true);
  assert.equal(frontendMasterSync.source, "JQUANTS_MOCK");
  assert.equal(frontendMasterSync.count, 9);
  assert.equal(frontendMasterSync.didNetworkRequest, false);

  const frontendConnectionCheck = await getBackendJQuantsConnectionCheck(backendBaseUrl);
  assert.equal(frontendConnectionCheck.ok, true);
  assert.equal(frontendConnectionCheck.mode, "mock");
  assert.equal(frontendConnectionCheck.didNetworkRequest, false);

  const frontendStock = await getBackendStockData("7203", backendBaseUrl);
  assert.equal(frontendStock.dataSource, "J_QUANTS_MOCK");
  assert.equal(frontendStock.isMock, true);
  assert.equal(frontendStock.isTradableData, false);
  assert.equal(typeof calculateScore(frontendStock, calculateIndicators(frontendStock, today)).totalScore, "number");

  process.env.JQUANTS_ENABLED = "true";
  process.env.JQUANTS_API_VERSION = "v2";
  process.env.JQUANTS_API_KEY = "";
  process.env.JQUANTS_USE_REAL_STOCKS = "true";
  process.env.JQUANTS_FALLBACK_TO_MOCK = "false";

  const configErrorApiStatus = await fetch(`${backendBaseUrl}/api/jquants/status`).then((response) => response.json());
  assert.equal(configErrorApiStatus.ok, false);
  assert.equal(configErrorApiStatus.mode, "config_error");
  assert.equal(configErrorApiStatus.apiVersion, "v2");
  assert.deepEqual(configErrorApiStatus.missingFields, ["JQUANTS_API_KEY"]);
  assert.equal(configErrorApiStatus.didNetworkRequest, false);
  assert.equal(JSON.stringify(configErrorApiStatus).includes("secret"), false);

  const configErrorApiStockResponse = await fetch(`${backendBaseUrl}/api/stocks/7203`);
  const configErrorApiStock = await configErrorApiStockResponse.json();
  assert.equal(configErrorApiStockResponse.status, 400);
  assert.equal(configErrorApiStock.didNetworkRequest, false);
  assert.deepEqual(configErrorApiStock.missingFields, ["JQUANTS_API_KEY"]);

  process.env.JQUANTS_API_KEY = "test-api-key-value";
  process.env.JQUANTS_FALLBACK_TO_MOCK = "true";
  const apiKeyReadyApiStatus = await fetch(`${backendBaseUrl}/api/jquants/status`).then((response) => response.json());
  assert.equal(apiKeyReadyApiStatus.ok, true);
  assert.equal(apiKeyReadyApiStatus.mode, "api_key_ready");
  assert.equal(apiKeyReadyApiStatus.config.hasApiKey, true);
  assert.equal(apiKeyReadyApiStatus.config.useRealStocks, true);
  assert.equal(apiKeyReadyApiStatus.config.cacheEnabled, true);
  assert.equal(apiKeyReadyApiStatus.config.maxRequestsPerMinute, 999);
  assert.equal(apiKeyReadyApiStatus.didNetworkRequest, false);
  assert.equal(JSON.stringify(apiKeyReadyApiStatus).includes("test-api-key-value"), false);

  const currentFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith(backendBaseUrl)) return currentFetch(url, options);
    assert.equal(String(url).includes(`api.jquants.com${JQUANTS_CONNECTION_CHECK_ENDPOINT}`), true);
    assert.equal(String(url).includes("/v2/bulk/list"), false);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify({ data: [{ Key: "sample.csv" }] }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  const apiKeyReadyConnectionCheck = await currentFetch(`${backendBaseUrl}/api/jquants/connection-check`).then((response) => response.json());
  globalThis.fetch = currentFetch;
  assert.equal(apiKeyReadyConnectionCheck.ok, true);
  assert.equal(apiKeyReadyConnectionCheck.mode, "connection_ok");
  assert.equal(apiKeyReadyConnectionCheck.didNetworkRequest, true);
  assert.equal(apiKeyReadyConnectionCheck.statusCode, 200);
  assert.equal(JSON.stringify(apiKeyReadyConnectionCheck).includes("test-api-key-value"), false);

  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith(backendBaseUrl)) return currentFetch(url, options);
    assert.equal(String(url).includes(`api.jquants.com${JQUANTS_RAW_DAILY_BARS_ENDPOINT}`), true);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify({ data: [{ Date: "2026-01-05", Code: "7203", Close: 3000 }] }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  const rawApiResponse = await currentFetch(`${backendBaseUrl}/api/jquants/raw/7203?from=2026-01-01&to=2026-01-31`).then((response) => response.json());
  globalThis.fetch = currentFetch;
  assert.equal(rawApiResponse.ok, true);
  assert.equal(rawApiResponse.mode, "raw_fetch_ok");
  assert.equal(rawApiResponse.didNetworkRequest, true);
  assert.equal(rawApiResponse.rowCount, 1);
  assert.equal(rawApiResponse.sampleRows.length, 1);
  assert.equal(JSON.stringify(rawApiResponse).includes("test-api-key-value"), false);

  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith(backendBaseUrl)) return currentFetch(url, options);
    assert.equal(String(url).includes(`api.jquants.com${JQUANTS_RAW_DAILY_BARS_ENDPOINT}`), true);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify({ data: [
      { Date: "2026-01-05", Code: "7203", C: 3000, V: 1000 },
      { Date: "2026-01-06", Code: "7203", C: 3010, V: 1100 }
    ] }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  const mappedApiResponse = await currentFetch(`${backendBaseUrl}/api/jquants/mapped/7203?from=2026-01-01&to=2026-01-31&forceRefresh=true`).then((response) => response.json());
  globalThis.fetch = currentFetch;
  assert.equal(mappedApiResponse.ok, true);
  assert.equal(mappedApiResponse.mode, "mapped_fetch_ok");
  assert.equal(mappedApiResponse.didNetworkRequest, true);
  assert.equal(mappedApiResponse.stockData.dataSource, "J_QUANTS_MAPPED");
  assert.equal(mappedApiResponse.stockData.price, 3010);
  assert.equal(mappedApiResponse.stockData.previousClose, 3000);
  assert.equal(mappedApiResponse.stockData.isTradableData, false);
  assert.equal(mappedApiResponse.debugInfo.closeFieldUsed, "C");
  assert.equal(mappedApiResponse.debugInfo.validCloseCount, 2);
  assert.equal("sampleRows" in mappedApiResponse, false);
  assert.equal(JSON.stringify(mappedApiResponse).includes("test-api-key-value"), false);

  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith(backendBaseUrl)) return currentFetch(url, options);
    assert.equal(String(url).includes(`api.jquants.com${JQUANTS_FINS_SUMMARY_ENDPOINT}?code=7203`), true);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    return new Response(JSON.stringify(finsRows), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  clearJQuantsCache();
  const finsApiResponse = await currentFetch(`${backendBaseUrl}/api/jquants/fins/summary/7203`).then((response) => response.json());
  globalThis.fetch = currentFetch;
  assert.equal(finsApiResponse.ok, true);
  assert.equal(finsApiResponse.mode, "fins_summary_ok");
  assert.equal(finsApiResponse.didNetworkRequest, true);
  assert.equal(finsApiResponse.cacheHit, false);
  assert.equal(finsApiResponse.rowCount, 5);
  assert.equal(finsApiResponse.sampleRows.length, 3);
  assert.equal(finsApiResponse.latestDisclosure.netSales, 36000000000000);
  assert.equal(finsApiResponse.latestDisclosure.operatingProfit, 3900000000000);
  assert.equal(finsApiResponse.debugInfo.salesFieldUsed, "Sales");
  assert.equal(JSON.stringify(finsApiResponse).includes("test-api-key-value"), false);
  assert.equal("rawRows" in finsApiResponse, false);
  assert.equal("data" in finsApiResponse, false);
  const finsApiCacheHit = await currentFetch(`${backendBaseUrl}/api/jquants/fins/summary/7203`).then((response) => response.json());
  assert.equal(finsApiCacheHit.cacheHit, true);
  assert.equal(finsApiCacheHit.didNetworkRequest, false);
  const frontendFins = await getBackendJQuantsFinancialSummary("7203", backendBaseUrl);
  assert.equal(frontendFins.ok, true);
  assert.equal(frontendFins.cacheHit, true);

  process.env.JQUANTS_USE_FINANCIALS = "true";
  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith(backendBaseUrl)) return currentFetch(url, options);
    assert.equal(options.headers["x-api-key"], "test-api-key-value");
    if (String(url).includes(JQUANTS_FINS_SUMMARY_ENDPOINT)) {
      return new Response(JSON.stringify(finsRows), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    assert.equal(String(url).includes(`api.jquants.com${JQUANTS_RAW_DAILY_BARS_ENDPOINT}`), true);
    return new Response(JSON.stringify(adjBars), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  clearJQuantsCache();
  const stockStillMock = await currentFetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  globalThis.fetch = currentFetch;
  assert.equal(stockStillMock.dataSource, "J_QUANTS_MAPPED");
  assert.equal(stockStillMock.didNetworkRequest, true);
  assert.equal(stockStillMock.isMock, false);
  assert.equal(stockStillMock.isTradableData, false);
  assert.equal(typeof stockStillMock.tradableDataLabel, "string");
  assert.equal(typeof stockStillMock.name, "string");
  assert.equal(stockStillMock.market, "プライム");
  assert.equal(stockStillMock.sector, "輸送用機器");
  assert.equal(stockStillMock.stockMasterSource, "LOCAL_MASTER");
  assert.equal(stockStillMock.cacheHit, false);
  assert.equal(stockStillMock.cacheStored, true);
  assert.equal("latestDisclosure" in stockStillMock, false);
  assert.equal(stockStillMock.financialSummary.available, true);
  assert.equal(stockStillMock.financialSummary.netSales, 36000000000000);
  assert.equal(stockStillMock.financialSignals.hasFinancialSummary, true);
  assert.equal(stockStillMock.preTradeCheck.available, true);
  assert.equal(stockStillMock.preTradeCheck.tradeAdvice, false);
  assert.equal(stockStillMock.preTradeCheck.newsAndDisclosure.tdnetConnected, false);
  assert.equal(stockStillMock.structuredSummary.preTrade.tradeAdvice, false);
  assert.equal(stockStillMock.aiSummary.mode, "rule_based_mock");
  assert.equal(stockStillMock.aiSummary.externalApiUsed, false);

  const stockCacheHit = await currentFetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  assert.equal(stockCacheHit.dataSource, "J_QUANTS_MAPPED");
  assert.equal(stockCacheHit.didNetworkRequest, false);
  assert.equal(stockCacheHit.cacheHit, true);
  assert.equal(stockCacheHit.financialSummary.cacheHit, true);
  assert.equal(typeof stockCacheHit.name, "string");
  assert.equal(stockCacheHit.market, "プライム");
  assert.equal(stockCacheHit.stockMasterSource, "LOCAL_MASTER");
  assert.equal(stockCacheHit.aiSummary.aiGenerated, false);
  assert.equal(stockCacheHit.preTradeCheck.available, true);

  process.env.AI_SUMMARY_MOCK_ENABLED = "false";
  clearJQuantsCache();
  const stockAiDisabled = await currentFetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  assert.equal(stockAiDisabled.aiSummaryStatus.enabled, false);
  assert.equal("aiSummary" in stockAiDisabled, false);
  process.env.AI_SUMMARY_MOCK_ENABLED = "true";

  process.env.JQUANTS_USE_REAL_STOCKS = "false";
  process.env.THEME_SUMMARY_MOCK_ENABLED = "false";
  clearJQuantsCache();
  const stockThemeDisabled = await currentFetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  assert.equal(stockThemeDisabled.themeSummaryStatus.enabled, false);
  assert.equal("themeSummary" in stockThemeDisabled, false);
  process.env.THEME_SUMMARY_MOCK_ENABLED = "true";

  const cacheStatusApi = await currentFetch(`${backendBaseUrl}/api/jquants/cache/status`).then((response) => response.json());
  assert.equal(cacheStatusApi.ok, true);
  assert.equal(cacheStatusApi.entryCount >= 0, true);
  assert.equal(JSON.stringify(cacheStatusApi).includes("stockData"), false);
  assert.equal(JSON.stringify(cacheStatusApi).includes("test-api-key-value"), false);
  const cacheClearApi = await currentFetch(`${backendBaseUrl}/api/jquants/cache/clear`).then((response) => response.json());
  assert.equal(cacheClearApi.cleared, true);

  process.env.JQUANTS_USE_REAL_STOCKS = "false";
  const stockMockAgain = await currentFetch(`${backendBaseUrl}/api/stocks/7203`).then((response) => response.json());
  assert.equal(stockMockAgain.dataSource, "J_QUANTS_MOCK");
  assert.equal(stockMockAgain.didNetworkRequest, false);
} finally {
  for (const [key, value] of Object.entries(originalJquantsEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  await new Promise((resolve) => server.close(resolve));
}

const jquantsClientSource = readFileSync("server/services/jquantsClient.js", "utf8");
assert.equal(jquantsClientSource.includes("fetchImpl(url"), true);
assert.equal(jquantsClientSource.includes("x-api-key"), true);
assert.equal(jquantsClientSource.includes("test-api-key-value"), false);
assert.equal(jquantsClientSource.includes("/v2/bulk/list"), false);
assert.equal(jquantsClientSource.includes("/v2/markets/calendar"), true);
assert.equal(jquantsClientSource.includes("/v2/equities/bars/daily"), true);
assert.equal(jquantsClientSource.includes("mapped_fetch_ok"), true);
const envExample = readFileSync("server/.env.example", "utf8");
assert.equal(/JQUANTS_API_KEY=\S/.test(envExample), false);
assert.equal(envExample.includes("JQUANTS_API_VERSION=v2"), true);
assert.equal(envExample.includes("JQUANTS_CACHE_ENABLED=true"), true);
assert.equal(envExample.includes("JQUANTS_CACHE_TTL_MS=300000"), true);
assert.equal(envExample.includes("JQUANTS_MIN_REQUEST_INTERVAL_MS=1000"), true);
assert.equal(envExample.includes("JQUANTS_MAX_REQUESTS_PER_MINUTE=20"), true);
assert.equal(envExample.includes("AI_SUMMARY_MOCK_ENABLED=true"), true);
assert.equal(envExample.includes("AI_SUMMARY_EXTERNAL_API_ENABLED=false"), true);
assert.equal(envExample.includes("THEME_SUMMARY_MOCK_ENABLED=true"), true);
assert.equal(envExample.includes("THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED=false"), true);
assert.equal(envExample.includes("THEME_SUMMARY_SCORE_ENABLED=false"), true);
assert.equal(envExample.includes("NEWS_API_KEY"), false);
assert.equal(envExample.includes("OPENAI_API_KEY"), false);
assert.equal(envExample.includes("CLAUDE_API_KEY"), false);
assert.equal(/JQUANTS_EMAIL=\S/.test(envExample), false);
assert.equal(/JQUANTS_PASSWORD=\S/.test(envExample), false);
assert.equal(/JQUANTS_REFRESH_TOKEN=\S/.test(envExample), false);
assert.equal(envExample.includes("# JQUANTS_USE_REFRESH_TOKEN=false"), true);
assert.equal(envExample.includes("EXTERNAL_API_TIMEOUT_MS=10000"), true);
assert.equal(readFileSync(".gitignore", "utf8").includes("server/.env"), true);
assert.equal(readFileSync("src/services/csvStorageService.js", "utf8").includes("JQUANTS_API_KEY"), false);
assert.equal(readFileSync("src/services/backendStockDataService.js", "utf8").includes("JQUANTS_API_KEY"), false);
const stockAnalyzerSource = readFileSync("src/components/StockAnalyzer.js", "utf8");
assert.equal(stockAnalyzerSource.includes("useRealStocks"), true);
assert.equal(stockAnalyzerSource.includes("フォールバック"), true);
assert.equal(stockAnalyzerSource.includes("バックエンド / J-Quants"), true);
assert.equal(stockAnalyzerSource.includes("ThemeSummaryPanel"), true);
assert.equal(stockAnalyzerSource.includes("manualThemeInput"), true);

assert.equal(normalizeSearchText(" ト ヨ タ "), "とよた");
assert.equal(isStockCodeQuery("7203"), true);
assert.equal(isStockCodeQuery("7203.T"), true);
assert.equal(isStockCodeQuery("トヨタ"), false);
const toyotaCandidates = searchStockCandidates("トヨタ", {});
assert.equal(toyotaCandidates[0].code, "7203");
assert.equal(toyotaCandidates[0].name, "トヨタ自動車");
const sonyCandidates = searchStockCandidates("ソニー", {});
assert.equal(sonyCandidates[0].code, "6758");
const softbankCandidates = searchStockCandidates("ソフト", {});
assert.equal(softbankCandidates.some((candidate) => candidate.code === "9984"), true);
const recruitCandidates = searchStockCandidates("リクルート", {});
assert.equal(recruitCandidates.some((candidate) => candidate.code === "6098"), true);
const favoriteSearch = searchStockCandidates("キーエンス", {
  favorites: [{ code: "6861", name: "キーエンス", market: "プライム", sector: "電気機器" }]
});
assert.equal(favoriteSearch[0].isFavorite, true);
const recentSearch = searchStockCandidates("ソニー", {
  recentStocks: [{ code: "6758", name: "ソニーグループ", market: "プライム", sector: "電気機器" }]
});
assert.equal(recentSearch[0].isRecent, true);
const watchSearch = searchStockCandidates("トヨタ", {
  watchlist: [{ code: "7203", name: "トヨタ自動車", market: "プライム" }]
});
assert.equal(watchSearch[0].isWatchlist, true);
const csvSearch = searchStockCandidates("テストCSV", {
  csvRows: [{ code: "1111", name: "テストCSV銘柄", market: "テスト市場", sector: "テスト業種" }]
});
assert.equal(csvSearch[0].code, "1111");
assert.equal(csvSearch[0].isCsv, true);
const csvMasterSearch = searchStockCandidates("ソフト", {
  stockMasterRows: [{ code: "9434", name: "ソフトバンク", market: "プライム", sector: "情報・通信業" }]
});
assert.equal(csvMasterSearch.some((candidate) => candidate.code === "9434" && candidate.isCsvMaster), true);
const mergedCandidates = mergeDuplicateCandidates([
  { code: "7203", name: "7203", sources: ["WATCHLIST"] },
  { code: "7203", name: "トヨタ自動車", market: "プライム", sector: "輸送用機器", sources: ["LOCAL_MASTER"] },
  { code: "7203", name: "トヨタ自動車CSV", sources: ["CSV_MASTER"] },
  { code: "7203", name: "トヨタ自動車", sources: ["RECENT"] },
  { code: "7203", name: "トヨタ自動車 CSV", sources: ["CSV"], financialSummary: { raw: true }, debugInfo: { raw: true } }
]);
assert.equal(mergedCandidates.length, 1);
assert.equal(mergedCandidates[0].name, "トヨタ自動車");
assert.equal(mergedCandidates[0].sources.includes("WATCHLIST"), true);
assert.equal(mergedCandidates[0].sources.includes("LOCAL_MASTER"), true);
assert.equal(mergedCandidates[0].sources.includes("RECENT"), true);
assert.equal(mergedCandidates[0].sources.includes("CSV_MASTER"), true);
assert.equal(mergedCandidates[0].sources.includes("CSV"), true);
assert.equal(JSON.stringify(mergedCandidates).includes("financialSummary"), false);
assert.equal(JSON.stringify(mergedCandidates).includes("debugInfo"), false);
const searchIndex = buildSearchIndex({
  favorites: [{ code: "6758", name: "ソニーグループ" }],
  recentStocks: [{ code: "8035", name: "東京エレクトロン" }],
  watchlist: ["7203"],
  stockMasterRows: [{ code: "9434", name: "ソフトバンク" }],
  csvRows: [{ code: "1111", name: "テストCSV銘柄" }]
});
assert.equal(searchIndex.some((candidate) => candidate.code === "7203"), true);
assert.equal(searchIndex.some((candidate) => candidate.code === "1111"), true);
assert.equal(searchIndex.some((candidate) => candidate.code === "8035" && candidate.sources.includes("RECENT")), true);
assert.equal(searchIndex.some((candidate) => candidate.code === "9434" && candidate.sources.includes("CSV_MASTER")), true);
assert.equal(StockSearchSuggestions({ query: "", candidates: [] }), "");
assert.equal(StockSearchSuggestions({ query: "トヨタ", candidates: toyotaCandidates }).includes("7203"), true);
assert.equal(StockSearchSuggestions({ query: "unknown", candidates: [] }).includes("候補が見つかりません"), true);
const stockSearchServiceSource = readFileSync("src/services/stockSearchService.js", "utf8");
assert.equal(stockSearchServiceSource.includes("fetch("), false);
assert.equal(stockSearchServiceSource.includes("http://"), false);
assert.equal(stockSearchServiceSource.includes("https://"), false);
assert.equal(stockSearchServiceSource.includes("JQUANTS_API_KEY"), true);
const jquantsMasterServiceSource = readFileSync("src/services/jquantsMasterService.js", "utf8");
assert.equal(jquantsMasterServiceSource.includes("fetch("), false);
assert.equal(jquantsMasterServiceSource.includes("localStorage"), false);
assert.equal(jquantsMasterServiceSource.includes("JQUANTS_API_KEY"), false);
assert.equal(jquantsMasterServiceSource.includes("api.jquants"), false);
const masterSyncServiceSource = readFileSync("src/services/masterSyncService.js", "utf8");
assert.equal(masterSyncServiceSource.includes("fetch("), false);
assert.equal(masterSyncServiceSource.includes("localStorage"), false);
assert.equal(masterSyncServiceSource.includes("JQUANTS_API_KEY"), false);
assert.equal(masterSyncServiceSource.includes("api.jquants"), false);
const masterSyncRouteSource = readFileSync("server/routes/masterSync.js", "utf8");
assert.equal(masterSyncRouteSource.includes("api.jquants.com"), false);
assert.equal(masterSyncRouteSource.includes("JQUANTS_API_KEY"), false);
assert.equal(masterSyncRouteSource.includes("x-api-key"), false);
assert.equal(masterSyncRouteSource.includes("fetch("), false);
assert.equal(stockAnalyzerSource.includes("searchStockCandidates"), true);

console.log("stock-analyzer backend foundation tests passed");
