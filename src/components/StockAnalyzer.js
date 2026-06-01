import {
  analyzeStockList,
  buildBulkAnalysisSummary,
  filterBulkAnalysisResults,
  sortBulkAnalysisResults
} from "../logic/bulkAnalysis.js";
import { buildExportFilename, downloadCsv, exportAnalysisResultsToCsv } from "../logic/csvExport.js";
import { buildAiSummaryMock } from "../logic/aiSummaryMockBuilder.js";
import { buildPreTradeCheck } from "../logic/preTradeCheckBuilder.js";
import { buildStructuredSummary } from "../logic/structuredSummaryBuilder.js";
import { buildThemeSummary } from "../logic/themeSummaryBuilder.js";
import {
  fetchManyStocks,
  fetchStockData,
  listAvailableStocks,
  listCsvStocks,
  listMockStocks,
  parseStockCsv,
  setCsvStockData
} from "../services/stockDataService.js";
import {
  clearCsvDataStorage,
  loadCsvDataFromStorage,
  saveCsvDataToStorage
} from "../services/csvStorageService.js";
import {
  addFavoriteStock,
  getFavoriteStocks,
  isFavoriteStock,
  normalizeFavoriteStock,
  removeFavoriteStock
} from "../services/favoriteStocksService.js";
import {
  addRecentStock,
  clearRecentStocks,
  getRecentStocks,
  removeRecentStock
} from "../services/recentStocksService.js";
import {
  clearStoredStockMaster,
  downloadStockMasterCsvTemplate,
  getStoredStockMaster,
  getStoredStockMasterMeta,
  parseStockMasterCsvText,
  readCsvFileAsText,
  saveStoredStockMaster
} from "../services/stockMasterCsvService.js";
import {
  MASTER_SYNC_SOURCES,
  buildMasterSyncDryRun,
  syncMaster
} from "../services/masterSyncService.js";
import {
  isStockCodeQuery,
  searchStockCandidates
} from "../services/stockSearchService.js";
import {
  getBackendHealth,
  getBackendJQuantsConnectionCheck,
  getBackendJQuantsStatus
} from "../services/backendStockDataService.js";
import { BulkAnalysisFilters } from "./BulkAnalysisFilters.js";
import { BulkAnalysisSummary } from "./BulkAnalysisSummary.js";
import { BulkAnalysisTable } from "./BulkAnalysisTable.js";
import { AiSummaryMockPanel } from "./AiSummaryMockPanel.js?v=ui-compact-20260531b";
import { CollapsibleSection } from "./CollapsibleSection.js";
import { CompactStatusBar } from "./CompactStatusBar.js";
import { CsvExportButton } from "./CsvExportButton.js";
import { DisclosurePanel } from "./DisclosurePanel.js";
import { FavoriteStocksPanel } from "./FavoriteStocksPanel.js";
import { FinancialSummaryPanel } from "./FinancialSummaryPanel.js";
import { KeyMetricsGrid } from "./KeyMetricsGrid.js";
import { OverheatPanel } from "./OverheatPanel.js";
import { PolicyThemePanel } from "./PolicyThemePanel.js";
import { PrimaryDecisionCard } from "./PrimaryDecisionCard.js";
import { PreTradeCheckPanel } from "./PreTradeCheckPanel.js";
import { RecentStocksPanel } from "./RecentStocksPanel.js";
import { ReasonPanel } from "./ReasonPanel.js";
import { RiskBadge } from "./RiskBadge.js";
import { ScoreGauge } from "./ScoreGauge.js";
import { SignalBadge } from "./SignalBadge.js";
import { StockSearchSuggestions } from "./StockSearchSuggestions.js";
import { StockMasterCsvPanel } from "./StockMasterCsvPanel.js";
import { StructuredSummaryPanel } from "./StructuredSummaryPanel.js";
import { TechnicalPanel } from "./TechnicalPanel.js";
import { ThemeSummaryPanel } from "./ThemeSummaryPanel.js";
import { escapeHtml } from "./formatters.js";

export function mountStockAnalyzer(root) {
  const state = {
    query: "7203",
    analysis: null,
    watchlist: ["7203", "6758", "8035"],
    batchResults: [],
    csvResult: null,
    csvStocks: [],
    savedCsvMeta: null,
    storageMessage: "",
    storageError: "",
    uiError: "",
    manualThemeInput: "",
    favorites: getFavoriteStocks(),
    favoriteMessage: "",
    recentStocks: getRecentStocks(),
    recentMessage: "",
    preTradeChecklist: getStoredPreTradeChecklist(),
    stockMasterRows: getStoredStockMaster(),
    stockMasterCsvMeta: getStoredStockMasterMeta(),
    stockMasterCsvResult: null,
    stockMasterDryRunResult: null,
    stockMasterCsvMessage: "",
    stockMasterCsvError: "",
    searchCandidates: [],
    searchMessage: "",
    backendStatus: {
      checked: false,
      ok: false,
      label: "未確認",
      message: "バックエンド接続はまだ確認していません。",
      mode: "未確認",
      apiVersion: "v2",
      jquantsEnabled: false,
      externalApiEnabled: false,
      didNetworkRequest: false,
      hasApiKey: false,
      apiKeyStatus: "未確認",
      statusCode: "",
      checkedEndpoint: "",
      dataKind: "",
      connectionResult: "未実行",
      useRealStocks: false,
      fallbackToMock: false,
      realStockFrom: "",
      realStockTo: "",
      cacheEnabled: false,
      cacheTtlMs: "",
      minRequestIntervalMs: "",
      maxRequestsPerMinute: "",
      useFinancials: false,
      financialsFallbackSilent: true,
      useFinancialScore: true,
      missingFields: [],
      error: ""
    },
    bulkFilters: {
      search: "",
      sortKey: "buyScoreDesc",
      signal: "ALL",
      risk: "ALL",
      material: "ALL"
    }
  };

  const setAnalysisFromStock = (stock) => {
    const stockWithTheme = withThemeSummary(stock, state.manualThemeInput);
    const analysis = analyzeStockList([stockWithTheme])[0];
    analysis.structuredSummary = stockWithTheme.structuredSummary || buildStructuredSummary(stockWithTheme, analysis.scoreResult, {
      indicators: analysis.indicators,
      summary: analysis.summary
    });
    analysis.preTradeCheck = stockWithTheme.preTradeCheck || buildPreTradeCheck(stockWithTheme, {
      indicators: analysis.indicators,
      scoreResult: analysis.scoreResult,
      structuredSummary: analysis.structuredSummary
    });
    analysis.structuredSummary = {
      ...analysis.structuredSummary,
      preTrade: analysis.structuredSummary.preTrade || analysis.preTradeCheck.structuredSummaryPreTrade
    };
    analysis.aiSummary = state.manualThemeInput
      ? buildAiSummaryMock(addPreTradeWarningToStructuredSummary(analysis.structuredSummary, analysis.preTradeCheck))
      : stockWithTheme.aiSummary || buildAiSummaryMock(addPreTradeWarningToStructuredSummary(analysis.structuredSummary, analysis.preTradeCheck));
    analysis.aiSummaryStatus = stockWithTheme.aiSummaryStatus;
    state.analysis = analysis;
  };

  const applyManualThemeInput = () => {
    state.manualThemeInput = root.querySelector("#manualThemeInput")?.value || "";
    if (state.analysis?.stock) {
      setAnalysisFromStock({
        ...state.analysis.stock,
        manualThemes: state.manualThemeInput
      });
    }
    render();
  };

  const togglePreTradeChecklist = (event) => {
    const input = event.target;
    const itemId = input?.dataset?.pretradeCheck;
    const code = input?.dataset?.pretradeCode || state.analysis?.stock?.code;
    if (!itemId || !code) return;
    const current = state.preTradeChecklist[code]?.checkedItemIds || [];
    const next = input.checked
      ? [...new Set([...current, itemId])]
      : current.filter((id) => id !== itemId);
    state.preTradeChecklist = {
      ...state.preTradeChecklist,
      [code]: {
        code,
        checkedItemIds: next,
        updatedAt: new Date().toISOString()
      }
    };
    saveStoredPreTradeChecklist(state.preTradeChecklist);
  };

  const syncBackendStatusFromStock = (stock) => {
    if (!isJQuantsRealStock(stock) && stock?.dataSource !== "J_QUANTS_MOCK" && !stock?.fallbackUsed) return;
    state.backendStatus = {
      ...state.backendStatus,
      checked: true,
      ok: true,
      label: "接続OK",
      message: isJQuantsRealStock(stock)
        ? "J-Quants実データをバックエンド経由で取得しました。財務・決算・TDnetは未接続です。"
        : stock.fallbackUsed
          ? "J-Quants取得に失敗したため、モックへフォールバックしています。"
          : "バックエンドのJ-Quantsモックで動作しています。",
      mode: isJQuantsRealStock(stock) ? "real_stock_ok" : "mock",
      apiVersion: "v2",
      jquantsEnabled: isJQuantsRealStock(stock) || Boolean(state.backendStatus.jquantsEnabled),
      externalApiEnabled: isJQuantsRealStock(stock) || Boolean(state.backendStatus.externalApiEnabled),
      didNetworkRequest: Boolean(stock.didNetworkRequest),
      hasApiKey: isJQuantsRealStock(stock) || Boolean(state.backendStatus.hasApiKey),
      apiKeyStatus: isJQuantsRealStock(stock) ? "設定済み" : state.backendStatus.apiKeyStatus,
      useRealStocks: isJQuantsRealStock(stock) || Boolean(state.backendStatus.useRealStocks),
      fallbackToMock: Boolean(state.backendStatus.fallbackToMock || stock.fallbackUsed || isJQuantsRealStock(stock)),
      realStockFrom: stock.realStockFrom || stock.from || state.backendStatus.realStockFrom || "",
      realStockTo: stock.realStockTo || stock.to || state.backendStatus.realStockTo || "",
      useFinancials: Boolean(stock.financialSummary || state.backendStatus.useFinancials),
      useFinancialScore: stock.useFinancialScore !== undefined ? Boolean(stock.useFinancialScore) : Boolean(state.backendStatus.useFinancialScore),
      financialsFallbackSilent: Boolean(state.backendStatus.financialsFallbackSilent),
      error: stock.fallbackUsed ? stock.jquantsErrorSummary?.safeError || "" : ""
    };
  };

  const restoreSavedCsv = () => {
    const restored = loadCsvDataFromStorage();
    if (!restored.ok) {
      state.storageError = restored.error;
      return;
    }
    if (!restored.data) return;
    setCsvStockData(restored.data.stocks);
    state.csvStocks = listCsvStocks();
    state.savedCsvMeta = {
      savedAt: restored.data.savedAt,
      sourceFileName: restored.data.sourceFileName,
      count: restored.data.count,
      version: restored.data.version
    };
    state.csvResult = { stocks: state.csvStocks, errors: [] };
    state.storageMessage = "保存済みCSVデータを復元しました";
    if (state.csvStocks[0]) {
      state.query = state.csvStocks[0].code;
      setAnalysisFromStock(state.csvStocks[0]);
    }
  };

  const buildSearchSources = () => {
    const availableByCode = new Map(listAvailableStocks().map((stock) => [stock.code, stock]));
    const watchlistStocks = state.watchlist.map((item) => {
      const code = String(item || "").trim();
      return availableByCode.get(code) || { code };
    });
    return {
      favorites: state.favorites,
      recentStocks: state.recentStocks,
      watchlist: watchlistStocks,
      csvRows: state.csvStocks,
      stockMasterRows: state.stockMasterRows
    };
  };

  const updateSearchCandidates = (query) => {
    const candidates = searchStockCandidates(query, buildSearchSources());
    const isCode = isStockCodeQuery(query);
    state.searchCandidates = isCode ? candidates.slice(0, 3) : candidates;
    state.searchMessage = "";
    if (query && !isCode && !candidates.length) {
      state.searchMessage = "候補が見つかりません。ローカル銘柄マスター、お気に入り、監視リスト、CSVから検索しています。";
    }
    return candidates;
  };

  const bindSearchCandidateButtons = (scope = root) => {
    scope.querySelectorAll("[data-search-candidate]").forEach((button) => {
      button.addEventListener("click", () => {
        const code = button.dataset.searchCandidate;
        state.query = code;
        state.searchCandidates = [];
        state.searchMessage = "";
        analyze(code);
      });
    });
  };

  const updateSearchSuggestionHost = (query) => {
    updateSearchCandidates(query);
    const host = root.querySelector("#stockSearchSuggestionHost");
    if (!host) return;
    host.innerHTML = StockSearchSuggestions({
      query: state.query,
      candidates: state.searchCandidates,
      message: state.searchMessage
    });
    bindSearchCandidateButtons(host);
  };

  const analyzeFromInput = () => {
    const query = state.query.trim();
    if (!query) return analyze("7203");
    if (isStockCodeQuery(query)) {
      state.searchCandidates = [];
      state.searchMessage = "";
      return analyze(query);
    }
    const candidates = updateSearchCandidates(query);
    if (candidates.length === 1) {
      state.query = candidates[0].code;
      state.searchCandidates = [];
      state.searchMessage = "";
      return analyze(candidates[0].code);
    }
    state.searchMessage = candidates.length
      ? "複数候補があります。分析する銘柄を選択してください。"
      : "候補が見つかりません。銘柄コードか、登録済みの会社名で検索してください。";
    render();
  };

  const analyze = async (query = state.query, options = {}) => {
    try {
      state.query = query || "7203";
      const stock = await fetchStockData(state.query, options);
      setAnalysisFromStock(stock);
      syncBackendStatusFromStock(stock);
      addStockToRecent(stock);
      state.uiError = "";
      state.favoriteMessage = "";
      state.searchCandidates = [];
      state.searchMessage = "";
    } catch (error) {
      state.uiError = error.message;
    }
    render();
  };

  const refreshFavorites = () => {
    state.favorites = getFavoriteStocks();
    updateSearchCandidates(state.query);
  };

  const refreshRecentStocks = () => {
    state.recentStocks = getRecentStocks();
    updateSearchCandidates(state.query);
  };

  const addStockToRecent = (stock) => {
    const result = addRecentStock(stock);
    if (!result.ok) {
      state.recentMessage = result.error;
      return;
    }
    refreshRecentStocks();
    state.recentMessage = "";
  };

  const addCurrentFavorite = () => {
    const source = state.analysis?.stock || { code: state.query };
    const normalized = normalizeFavoriteStock(source);
    if (!normalized) {
      state.favoriteMessage = "お気に入りに追加できる銘柄コードがありません。";
      render();
      return;
    }
    const result = addFavoriteStock(normalized);
    refreshFavorites();
    state.favoriteMessage = result.ok
      ? `${normalized.code} ${normalized.name} をお気に入りに追加しました。`
      : result.error;
    render();
  };

  const removeFavorite = (code) => {
    const ok = globalThis.confirm
      ? globalThis.confirm("お気に入りから削除しますか？")
      : true;
    if (!ok) return;
    const result = removeFavoriteStock(code);
    refreshFavorites();
    state.favoriteMessage = result.ok ? "お気に入りから削除しました。" : result.error;
    render();
  };

  const analyzeFavorite = (code) => {
    state.query = code;
    analyze(code);
  };

  const analyzeRecent = (code) => {
    state.query = code;
    analyze(code);
  };

  const removeRecent = (code) => {
    const result = removeRecentStock(code);
    refreshRecentStocks();
    state.recentMessage = result.ok ? "最近見た銘柄から削除しました。" : result.error;
    render();
  };

  const clearRecent = () => {
    const ok = globalThis.confirm
      ? globalThis.confirm("最近見た銘柄をすべて削除しますか？")
      : true;
    if (!ok) return;
    const result = clearRecentStocks();
    refreshRecentStocks();
    state.recentMessage = result.ok ? "最近見た銘柄をすべて削除しました。" : result.error;
    render();
  };

  const handleStockMasterCsvFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      state.stockMasterCsvError = "銘柄マスターはCSVファイルを選択してください。";
      state.stockMasterCsvMessage = "";
      render();
      return;
    }
    const selectedEncoding = root.querySelector("#stockMasterCsvEncoding")?.value || "auto";
    const decoded = await readCsvFileAsText(file, { encoding: selectedEncoding });
    if (!decoded.ok) {
      state.stockMasterCsvError = decoded.decodeWarning || "銘柄マスターCSVを読み込めませんでした。";
      state.stockMasterCsvMessage = "";
      render();
      return;
    }
    const parsed = parseStockMasterCsvText(decoded.text, decoded);
    state.stockMasterCsvResult = parsed;
    if (!parsed.rows.length) {
      state.stockMasterCsvError = parsed.errors[0] || "有効な銘柄マスター行がありません。";
      state.stockMasterCsvMessage = "";
      render();
      return;
    }
    const saved = saveStoredStockMaster(parsed.rows, undefined, {
      ...parsed.encoding,
      source: MASTER_SYNC_SOURCES.CSV_IMPORT,
      lastSyncSource: MASTER_SYNC_SOURCES.CSV_IMPORT,
      lastSyncCount: parsed.rows.length,
      lastSyncAt: new Date().toISOString()
    });
    if (!saved.ok) {
      state.stockMasterCsvError = saved.error;
      state.stockMasterCsvMessage = "";
      render();
      return;
    }
    state.stockMasterRows = saved.rows;
    state.stockMasterCsvMeta = saved.meta;
    state.stockMasterCsvError = "";
    state.stockMasterCsvMessage = `銘柄マスターCSVを${saved.count}件保存しました。会社名検索候補にCSV_MASTERとして追加されます。`;
    updateSearchCandidates(state.query);
    render();
  };

  const fetchJQuantsMasterMock = async () => {
    const syncResult = await syncMaster(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
    const saved = saveStoredStockMaster(syncResult.records, undefined, {
      source: syncResult.source,
      lastSyncSource: syncResult.source,
      lastSyncCount: syncResult.count,
      lastSyncAt: syncResult.importedAt,
      selectedEncoding: "utf-8",
      detectedEncoding: "utf-8",
      mock: true,
      didNetworkRequest: syncResult.didNetworkRequest
    });
    if (!saved.ok) {
      state.stockMasterCsvError = saved.error;
      state.stockMasterCsvMessage = "";
      render();
      return;
    }
    state.stockMasterRows = saved.rows;
    state.stockMasterCsvMeta = saved.meta;
    state.stockMasterCsvResult = {
      ok: true,
      rows: syncResult.records,
      errors: syncResult.warnings,
      stats: {
        readCount: syncResult.fetchedCount,
        validCount: syncResult.count,
        excludedCount: 0,
        duplicateCount: Math.max(syncResult.fetchedCount - syncResult.count, 0),
        storedCount: saved.count,
        truncatedCount: 0,
        csvCount: syncResult.csvCount
      },
      encoding: saved.meta
    };
    state.stockMasterDryRunResult = null;
    state.stockMasterCsvError = "";
    state.stockMasterCsvMessage = `J-Quants銘柄マスターMockを${saved.count}件反映しました。実API接続は行っていません。`;
    updateSearchCandidates(state.query);
    render();
  };

  const runJQuantsMasterDryRun = async () => {
    const result = await buildMasterSyncDryRun(MASTER_SYNC_SOURCES.JQUANTS_MOCK);
    state.stockMasterDryRunResult = result;
    state.stockMasterCsvError = "";
    state.stockMasterCsvMessage = `J-Quants取得 Dry-run: 取得${result.fetchedCount}件 / CSV${result.csvCount}件。保存・実API接続は行っていません。`;
    render();
  };

  const clearStockMasterCsv = () => {
    const ok = globalThis.confirm
      ? globalThis.confirm("保存済み銘柄マスターCSVを削除しますか？分析用CSVやお気に入りは削除されません。")
      : true;
    if (!ok) return;
    const result = clearStoredStockMaster();
    if (result.ok) {
      state.stockMasterRows = [];
      state.stockMasterCsvMeta = null;
      state.stockMasterCsvResult = null;
      state.stockMasterCsvError = "";
      state.stockMasterCsvMessage = "保存済み銘柄マスターCSVを削除しました。";
      updateSearchCandidates(state.query);
    } else {
      state.stockMasterCsvError = result.error;
    }
    render();
  };

  const addWatch = () => {
    const query = state.query.trim();
    if (query && !state.watchlist.includes(query)) state.watchlist.push(query);
    render();
  };

  const addCsvWatch = (code) => {
    if (!state.watchlist.includes(code)) state.watchlist.push(code);
  };

  const addAllCsvToWatch = () => {
    state.csvStocks.forEach((stock) => addCsvWatch(stock.code));
    render();
  };

  const analyzeWatchlist = async () => {
    const stocks = await fetchManyStocks(state.watchlist, { dataProvider: "MOCK" });
    state.batchResults = analyzeStockList(stocks);
    render();
  };

  const analyzeCsvStocks = () => {
    state.batchResults = analyzeStockList(state.csvStocks);
    if (state.batchResults[0]) state.analysis = state.batchResults[0];
    render();
  };

  const handleCsvFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      state.csvResult = { stocks: [], errors: ["ファイル形式がCSVではありません"] };
      state.csvStocks = [];
      render();
      return;
    }
    const result = parseStockCsv(await file.text());
    setCsvStockData(result.stocks);
    state.csvStocks = listCsvStocks();
    state.csvResult = result;
    state.storageError = "";
    state.storageMessage = "";
    if (result.stocks.length) {
      const saved = saveCsvDataToStorage(state.csvStocks, { sourceFileName: file.name });
      if (saved.ok) {
        state.savedCsvMeta = {
          savedAt: saved.data.savedAt,
          sourceFileName: saved.data.sourceFileName,
          count: saved.data.count,
          version: saved.data.version
        };
        state.storageMessage = "CSVデータをブラウザに保存しました";
      } else {
        state.storageError = saved.error;
      }
      state.query = state.csvStocks[0].code;
      state.batchResults = analyzeStockList(state.csvStocks);
      state.analysis = state.batchResults[0];
    }
    render();
  };

  const clearSavedCsv = () => {
    const ok = globalThis.confirm
      ? globalThis.confirm("保存済みCSVデータを削除しますか？\nこの操作では元のCSVファイルは削除されません。\nブラウザに保存されたデータのみ削除されます。")
      : true;
    if (!ok) return;
    const result = clearCsvDataStorage();
    if (!result.ok) {
      state.storageError = result.error;
      render();
      return;
    }
    setCsvStockData([]);
    state.csvStocks = [];
    state.csvResult = null;
    state.savedCsvMeta = null;
    state.storageMessage = "保存済みCSVデータを削除しました";
    state.storageError = "";
    if (state.analysis?.stock.dataSource === "CSV") state.analysis = null;
    state.batchResults = state.batchResults.filter((resultItem) => resultItem.stock.dataSource !== "CSV");
    render();
  };

  const updateBulkFilters = () => {
    state.bulkFilters.search = root.querySelector("#bulkSearch")?.value ?? "";
    state.bulkFilters.sortKey = root.querySelector("#bulkSort")?.value ?? "buyScoreDesc";
    state.bulkFilters.signal = root.querySelector("#bulkSignal")?.value ?? "ALL";
    state.bulkFilters.risk = root.querySelector("#bulkRisk")?.value ?? "ALL";
    state.bulkFilters.material = root.querySelector("#bulkMaterial")?.value ?? "ALL";
    render();
  };

  const exportVisibleResults = () => {
    const visible = visibleBulkResults(state);
    downloadCsv(buildExportFilename(), exportAnalysisResultsToCsv(visible));
  };

  const checkBackendConnection = async () => {
    state.backendStatus = {
      checked: true,
      ok: false,
      label: "確認中",
      message: "ローカルバックエンドを確認しています。",
      mode: "checking",
      apiVersion: "v2",
      jquantsEnabled: false,
      externalApiEnabled: false,
      didNetworkRequest: false,
      hasApiKey: false,
      apiKeyStatus: "確認中",
      statusCode: "",
      checkedEndpoint: "",
      dataKind: "",
      connectionResult: "確認中",
      useRealStocks: false,
      fallbackToMock: false,
      realStockFrom: "",
      realStockTo: "",
      cacheEnabled: false,
      cacheTtlMs: "",
      minRequestIntervalMs: "",
      maxRequestsPerMinute: "",
      useFinancials: false,
      financialsFallbackSilent: true,
      missingFields: [],
      error: ""
    };
    render();
    const [health, jquantsStatus] = await Promise.all([
      getBackendHealth(),
      getBackendJQuantsStatus()
    ]);
    if (health.ok) {
      const statusOk = Boolean(jquantsStatus.ok);
      const config = jquantsStatus.config || {};
      state.backendStatus = {
        checked: true,
        ok: statusOk,
        label: "接続OK",
        message: jquantsStatus.message || health.message || "Backend is running.",
        mode: jquantsStatus.mode || health.mode || "mock",
        apiVersion: jquantsStatus.apiVersion || health.apiVersion || "v2",
        jquantsEnabled: Boolean(jquantsStatus.enabled ?? health.jquantsEnabled),
        externalApiEnabled: Boolean(jquantsStatus.externalApiEnabled ?? health.externalApiEnabled),
        didNetworkRequest: Boolean(jquantsStatus.didNetworkRequest || health.didNetworkRequest),
        hasApiKey: Boolean(config.hasApiKey),
        apiKeyStatus: config.hasApiKey ? "設定済み" : "未設定",
        statusCode: jquantsStatus.statusCode || "",
        checkedEndpoint: jquantsStatus.checkedEndpoint || "",
        dataKind: jquantsStatus.dataKind || "",
        connectionResult: "未実行",
        useRealStocks: Boolean(config.useRealStocks),
        fallbackToMock: Boolean(config.fallbackToMock),
        realStockFrom: config.realStockFrom || "",
        realStockTo: config.realStockTo || "",
        cacheEnabled: Boolean(config.cacheEnabled),
        cacheTtlMs: config.cacheTtlMs || "",
        minRequestIntervalMs: config.minRequestIntervalMs || "",
        maxRequestsPerMinute: config.maxRequestsPerMinute || "",
        useFinancials: Boolean(config.useFinancials),
        useFinancialScore: Boolean(config.useFinancialScore ?? state.backendStatus.useFinancialScore),
        financialsFallbackSilent: Boolean(config.financialsFallbackSilent),
        missingFields: jquantsStatus.missingFields || [],
        error: statusOk ? "" : jquantsStatus.error || ""
      };
    } else {
      state.backendStatus = {
        checked: true,
        ok: false,
        label: "未起動 / エラー",
        message: health.error || "ローカルバックエンドが起動していません。",
        mode: "unavailable",
        apiVersion: "v2",
        jquantsEnabled: false,
        externalApiEnabled: false,
        didNetworkRequest: false,
        hasApiKey: false,
        apiKeyStatus: "未確認",
        statusCode: "",
        checkedEndpoint: "",
        dataKind: "",
        connectionResult: "未実行",
        useRealStocks: false,
        fallbackToMock: false,
        realStockFrom: "",
        realStockTo: "",
        cacheEnabled: false,
        cacheTtlMs: "",
        minRequestIntervalMs: "",
        maxRequestsPerMinute: "",
      useFinancials: false,
      useFinancialScore: true,
      financialsFallbackSilent: true,
        missingFields: [],
        error: health.detail || ""
      };
    }
    render();
  };

  const runBackendConnectionCheck = async () => {
    const result = await getBackendJQuantsConnectionCheck();
    state.backendStatus = {
      checked: true,
      ok: Boolean(result.ok),
      label: result.ok ? "接続確認OK" : "接続確認エラー",
      message: result.message || result.error || "J-Quants接続確認の結果を取得しました。",
      mode: result.mode || "unknown",
      apiVersion: result.apiVersion || "v2",
      jquantsEnabled: Boolean(result.enabled),
      externalApiEnabled: Boolean(result.externalApiEnabled),
      didNetworkRequest: Boolean(result.didNetworkRequest),
      hasApiKey: Boolean(result.config?.hasApiKey),
      apiKeyStatus: result.config?.hasApiKey ? "設定済み" : "未設定",
      statusCode: result.statusCode ?? "",
      checkedEndpoint: result.checkedEndpoint || "",
      dataKind: result.dataKind || "",
      connectionResult: result.mode === "connection_ok" ? "成功" : result.mode === "connection_error" ? "失敗" : "未実行",
      useRealStocks: Boolean(result.config?.useRealStocks ?? state.backendStatus.useRealStocks),
      fallbackToMock: Boolean(result.config?.fallbackToMock ?? state.backendStatus.fallbackToMock),
      realStockFrom: result.config?.realStockFrom || state.backendStatus.realStockFrom || "",
      realStockTo: result.config?.realStockTo || state.backendStatus.realStockTo || "",
      cacheEnabled: Boolean(result.config?.cacheEnabled ?? state.backendStatus.cacheEnabled),
      cacheTtlMs: result.config?.cacheTtlMs || state.backendStatus.cacheTtlMs || "",
      minRequestIntervalMs: result.config?.minRequestIntervalMs || state.backendStatus.minRequestIntervalMs || "",
      maxRequestsPerMinute: result.config?.maxRequestsPerMinute || state.backendStatus.maxRequestsPerMinute || "",
      useFinancials: Boolean(result.config?.useFinancials ?? state.backendStatus.useFinancials),
      useFinancialScore: Boolean(result.config?.useFinancialScore ?? state.backendStatus.useFinancialScore),
      financialsFallbackSilent: Boolean(result.config?.financialsFallbackSilent ?? state.backendStatus.financialsFallbackSilent),
      missingFields: result.missingFields || [],
      error: result.safeError || result.detail || ""
    };
    render();
  };

  const render = () => {
    root.innerHTML = template(state);
    root.querySelector("#stockQuery").addEventListener("input", (event) => {
      state.query = event.target.value;
      updateSearchSuggestionHost(state.query);
    });
    root.querySelector("#stockQuery").addEventListener("keydown", (event) => {
      if (event.key === "Enter") analyzeFromInput();
    });
    root.querySelector("#analyzeBtn").addEventListener("click", analyzeFromInput);
    root.querySelector("#addWatchBtn").addEventListener("click", addWatch);
    root.querySelector("#batchBtn").addEventListener("click", analyzeWatchlist);
    root.querySelector("#csvFile").addEventListener("change", (event) => handleCsvFile(event.target.files[0]));
    root.querySelector("#stockMasterCsvFile")?.addEventListener("change", (event) => handleStockMasterCsvFile(event.target.files[0]));
    root.querySelector("#clearStockMasterCsvBtn")?.addEventListener("click", clearStockMasterCsv);
    root.querySelector("#downloadStockMasterTemplateBtn")?.addEventListener("click", () => downloadStockMasterCsvTemplate());
    root.querySelector("#fetchJquantsMasterMockBtn")?.addEventListener("click", fetchJQuantsMasterMock);
    root.querySelector("#dryRunJquantsMasterBtn")?.addEventListener("click", runJQuantsMasterDryRun);
    root.querySelector("#addAllCsvBtn")?.addEventListener("click", addAllCsvToWatch);
    root.querySelector("#analyzeCsvBtn")?.addEventListener("click", analyzeCsvStocks);
    root.querySelector("#savedCsvAnalyzeBtn")?.addEventListener("click", analyzeCsvStocks);
    root.querySelector("#savedCsvWatchBtn")?.addEventListener("click", addAllCsvToWatch);
    root.querySelector("#savedCsvClearBtn")?.addEventListener("click", clearSavedCsv);
    root.querySelector("#exportAnalysisCsvBtn")?.addEventListener("click", exportVisibleResults);
    root.querySelector("#backendHealthBtn")?.addEventListener("click", checkBackendConnection);
    root.querySelector("#backendConnectionCheckBtn")?.addEventListener("click", runBackendConnectionCheck);
    root.querySelector("#forceRefreshBtn")?.addEventListener("click", () => analyze(state.query, { forceRefresh: true }));
    root.querySelector("#favoriteCurrentBtn")?.addEventListener("click", addCurrentFavorite);
    root.querySelector("#clearRecentStocksBtn")?.addEventListener("click", clearRecent);
    root.querySelector("#manualThemeInput")?.addEventListener("input", (event) => {
      state.manualThemeInput = event.target.value;
    });
    root.querySelector("#applyThemeBtn")?.addEventListener("click", applyManualThemeInput);
    root.querySelectorAll("[data-pretrade-check]").forEach((input) => input.addEventListener("change", togglePreTradeChecklist));
    ["#bulkSearch", "#bulkSort", "#bulkSignal", "#bulkRisk", "#bulkMaterial"].forEach((selector) => {
      const element = root.querySelector(selector);
      element?.addEventListener(selector === "#bulkSearch" ? "input" : "change", updateBulkFilters);
    });
    root.querySelectorAll("[data-sample]").forEach((button) => {
      button.addEventListener("click", () => analyze(button.dataset.sample));
    });
    root.querySelectorAll("[data-watch]").forEach((button) => {
      button.addEventListener("click", () => analyze(button.dataset.watch));
    });
    root.querySelectorAll("[data-csv-analyze]").forEach((button) => {
      button.addEventListener("click", () => analyze(button.dataset.csvAnalyze));
    });
    root.querySelectorAll("[data-csv-add]").forEach((button) => {
      button.addEventListener("click", () => {
        addCsvWatch(button.dataset.csvAdd);
        render();
      });
    });
    root.querySelectorAll("[data-favorite-analyze]").forEach((button) => {
      button.addEventListener("click", () => analyzeFavorite(button.dataset.favoriteAnalyze));
    });
    root.querySelectorAll("[data-favorite-remove]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        removeFavorite(button.dataset.favoriteRemove);
      });
    });
    root.querySelectorAll("[data-recent-analyze]").forEach((button) => {
      button.addEventListener("click", () => analyzeRecent(button.dataset.recentAnalyze));
    });
    root.querySelectorAll("[data-recent-remove]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        removeRecent(button.dataset.recentRemove);
      });
    });
    bindSearchCandidateButtons(root);
    root.querySelectorAll("[data-bulk-code]").forEach((row) => {
      row.addEventListener("click", () => {
        const found = state.batchResults.find((result) => result.stock.code === row.dataset.bulkCode);
        if (found) {
          state.analysis = found;
          state.query = found.stock.code;
          render();
        }
      });
    });
  };

  restoreSavedCsv();
  render();
  if (!state.analysis) analyze(state.query);
}

function template(state) {
  return `
    <main class="app-shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">JAPAN EQUITY RULE-BASED DASHBOARD</p>
          <h1>AI株分析アプリ</h1>
          <p class="lead">CSV取込またはサンプルデータを、ルールベースで高速にスクリーニングします。</p>
        </div>
        <div class="disclaimer">このダッシュボードは投資助言ではありません。表示データの出所と未接続項目を確認し、実売買判断には必ず公式情報を確認してください。</div>
      </header>
      ${dataNotice(state.analysis?.stock)}
      ${CompactStatusBar(state.backendStatus)}
      ${inputPanel(state)}
      ${RecentStocksPanel({
        recentStocks: state.recentStocks,
        currentCode: state.analysis?.stock?.code || state.query
      })}
      ${state.recentMessage ? `<div class="storage-message recent-message">${escapeHtml(state.recentMessage)}</div>` : ""}
      ${FavoriteStocksPanel({
        favorites: state.favorites,
        currentCode: state.analysis?.stock?.code || state.query,
        currentIsFavorite: isFavoriteStock(state.analysis?.stock?.code || state.query)
      })}
      ${state.favoriteMessage ? `<div class="storage-message favorite-message">${escapeHtml(state.favoriteMessage)}</div>` : ""}
      ${state.uiError ? `<div class="error-box">${escapeHtml(state.uiError)}</div>` : ""}
      ${state.analysis ? dashboardV2(state.analysis, state) : `<div class="loading">分析結果を準備しています...</div>`}
      ${state.batchResults.length ? bulkAnalysisPanel(state) : ""}
      <div class="page-section-title">管理・データ入力</div>
      ${CollapsibleSection({ title: "接続詳細", children: backendPanel(state) })}
      ${CollapsibleSection({ title: "CSV読み込み・保存データ", children: `${stockMasterCsvPanel(state)}${csvImportPanel(state)}${savedCsvPanel(state)}` })}
      ${watchPanel(state)}
    </main>
  `;
}

function backendPanel(state) {
  const statusClass = state.backendStatus.ok ? "ok" : (state.backendStatus.checked ? "error" : "idle");
  return `
    <section class="backend-panel">
      <div>
        <div class="panel-title">J-Quants接続準備</div>
        <p>J-Quants V2 APIキーはローカルバックエンド側だけで扱います。ブラウザにはAPIキーを置きません。</p>
        <p>${state.backendStatus.useRealStocks ? "実データモードON時は、銘柄を個別検索したときだけJ-Quants日足データを取得します。" : "実データモードOFF時は、バックエンドのJ-Quantsモックで動作します。"}</p>
      </div>
      <div class="backend-status-card ${statusClass}">
        <div class="backend-grid">
          <div><span>バックエンド状態</span><strong>${escapeHtml(state.backendStatus.label)}</strong></div>
          <div><span>APIバージョン</span><strong>${escapeHtml(state.backendStatus.apiVersion)}</strong></div>
          <div><span>J-Quants</span><strong>${state.backendStatus.jquantsEnabled ? "有効" : "無効"}</strong></div>
          <div><span>APIキー</span><strong>${escapeHtml(state.backendStatus.apiKeyStatus)}</strong></div>
          <div><span>実データモード</span><strong>${state.backendStatus.useRealStocks ? "ON" : "OFF"}</strong></div>
          <div><span>フォールバック</span><strong>${state.backendStatus.fallbackToMock ? "ON" : "OFF"}</strong></div>
          <div><span>外部API通信</span><strong>${state.backendStatus.externalApiEnabled ? "有効" : "無効"}</strong></div>
          <div><span>モード</span><strong>${escapeHtml(state.backendStatus.mode)}</strong></div>
          <div><span>実通信</span><strong>${state.backendStatus.didNetworkRequest ? "あり" : (state.backendStatus.useRealStocks ? "銘柄取得時のみ" : "なし")}</strong></div>
          <div><span>データ期間</span><strong>${escapeHtml(formatDateRange(state.backendStatus.realStockFrom, state.backendStatus.realStockTo))}</strong></div>
          <div><span>キャッシュ</span><strong>${state.backendStatus.cacheEnabled ? "ON" : "OFF"}</strong></div>
          <div><span>キャッシュTTL</span><strong>${escapeHtml(formatMs(state.backendStatus.cacheTtlMs))}</strong></div>
          <div><span>財務スコア</span><strong>${state.backendStatus.useFinancialScore ? "弱く反映" : "表示のみ"}</strong></div>
          <div><span>接続確認結果</span><strong>${escapeHtml(state.backendStatus.connectionResult)}</strong></div>
          <div><span>確認endpoint</span><strong>${escapeHtml(state.backendStatus.checkedEndpoint || "-")}</strong></div>
          <div><span>HTTP status</span><strong>${escapeHtml(String(state.backendStatus.statusCode || "-"))}</strong></div>
        </div>
        ${state.backendStatus.missingFields.length ? `<div class="backend-detail">不足項目：${escapeHtml(state.backendStatus.missingFields.join(", "))}</div>` : ""}
        <div class="backend-message">${escapeHtml(state.backendStatus.message)}</div>
        ${state.backendStatus.error ? `<div class="backend-detail">${escapeHtml(state.backendStatus.error)}</div>` : ""}
        <div class="backend-actions">
          <button id="backendHealthBtn">バックエンド接続確認</button>
          <button id="backendConnectionCheckBtn">J-Quants接続確認</button>
          ${isJQuantsRealStock(state.analysis?.stock) ? `<button id="forceRefreshBtn">J-Quants再取得</button>` : ""}
        </div>
      </div>
    </section>
  `;
}

function dataNotice(stock) {
  const view = getDataSourceDisplay(stock);
  return `
    <section class="mock-notice">
      <div>
        <strong>データ種別を必ず確認してください</strong>
        <p>${escapeHtml(view.notice)}</p>
      </div>
      <span>${escapeHtml(view.badge)}</span>
    </section>
  `;
}

function csvImportPanel(state) {
  const success = state.csvResult?.stocks.length ?? 0;
  const errors = state.csvResult?.errors.length ?? 0;
  return `
    <section class="csv-panel">
      <div class="panel-title">CSVデータを読み込む</div>
      <div class="csv-import-row">
        <label class="file-button"><input id="csvFile" type="file" accept=".csv,text/csv" />ファイルを選択</label>
        <span>対応形式：code,name,price,previousClose,volume,ma25,ma75,rsi などを含むCSV</span>
      </div>
      <div class="csv-help">正常に読み込んだCSVは、このブラウザのlocalStorageに自動保存します。CSV取込データは「要確認」として扱います。</div>
      ${state.csvResult ? `
        <div class="csv-result">
          <div class="csv-result-head">
            <strong>CSV読み込み結果：成功 ${success}件 / エラー ${errors}件</strong>
            <div>${success ? `<button id="addAllCsvBtn">CSV銘柄を全て監視リストへ</button><button id="analyzeCsvBtn">CSV銘柄を一括分析</button>` : ""}</div>
          </div>
          ${success ? `<div class="csv-stock-list">${state.csvStocks.map(csvStockRow).join("")}</div>` : ""}
          ${errors ? `<div class="csv-errors"><strong>CSV読み込みエラー</strong>${state.csvResult.errors.map((error) => `<p>${escapeHtml(error)}</p>`).join("")}</div>` : ""}
        </div>
      ` : ""}
    </section>
  `;
}

function stockMasterCsvPanel(state) {
  return StockMasterCsvPanel({
    rows: state.stockMasterRows,
    meta: state.stockMasterCsvMeta,
    result: state.stockMasterCsvResult,
    dryRunResult: state.stockMasterDryRunResult,
    message: state.stockMasterCsvMessage,
    error: state.stockMasterCsvError
  });
}

function savedCsvPanel(state) {
  return `
    <section class="csv-panel storage-panel">
      <div class="panel-title">保存済みCSVデータ</div>
      ${state.storageMessage ? `<div class="storage-message">${escapeHtml(state.storageMessage)}</div>` : ""}
      ${state.storageError ? `<div class="csv-errors"><strong>保存済みCSVデータを復元できませんでした</strong><p>${escapeHtml(state.storageError)}</p><p>必要であれば保存済みデータを削除してください。</p><button id="savedCsvClearBtn">保存済みCSVを削除</button></div>` : ""}
      ${state.savedCsvMeta ? `
        <div class="storage-grid">
          <div><span>保存元</span><strong>${escapeHtml(state.savedCsvMeta.sourceFileName)}</strong></div>
          <div><span>保存日時</span><strong>${escapeHtml(formatSavedAt(state.savedCsvMeta.savedAt))}</strong></div>
          <div><span>銘柄数</span><strong>${state.savedCsvMeta.count}件</strong></div>
          <div><span>データ種別</span><strong>CSV取込</strong></div>
          <div><span>保存元種別</span><strong>ブラウザ保存済みCSV</strong></div>
          <div><span>実売買利用</span><strong class="negative">要確認</strong></div>
        </div>
        <div class="storage-actions">
          <button id="savedCsvAnalyzeBtn" class="primary">保存済みCSVを一括分析</button>
          <button id="savedCsvWatchBtn">保存済みCSVを監視リストへ追加</button>
          <button id="savedCsvClearBtn">保存済みCSVを削除</button>
        </div>
        <div class="csv-help">保存済みCSVデータはユーザー提供データです。正確性・最新性は保証されません。実売買判断には必ず公式情報を確認してください。</div>
      ` : (!state.storageError ? `<div class="csv-help">保存済みCSVデータはありません。CSVファイルを読み込むと、このブラウザに保存できます。</div>` : "")}
    </section>
  `;
}

function inputPanel(state) {
  return `
    <section class="input-panel">
      <div class="input-row">
        <input id="stockQuery" value="${escapeHtml(state.query)}" placeholder="7203、トヨタ、6758、CSV銘柄コード" />
        <button id="analyzeBtn" class="primary">分析</button>
        <button id="addWatchBtn">監視リスト追加</button>
        <button id="batchBtn">監視リスト一括分析</button>
      </div>
      <div id="stockSearchSuggestionHost">
        ${StockSearchSuggestions({
          query: state.query,
          candidates: state.searchCandidates,
          message: state.searchMessage
        })}
      </div>
      <details class="sample-picker">
        <summary>サンプル銘柄を開く</summary>
        <div class="sample-row">
          ${listMockStocks().map((stock) => `<button data-sample="${stock.code}">${stock.code} ${escapeHtml(stock.name)} <span class="mini-source">${stock.dataSource}</span></button>`).join("")}
        </div>
      </details>
    </section>
  `;
}

function csvStockRow(stock) {
  return `
    <div class="csv-stock-row">
      <span>${stock.code} ${escapeHtml(stock.name)}</span>
      <span><span class="mini-source">CSV</span> <span class="mini-source verify">要確認</span></span>
      <span><button data-csv-analyze="${stock.code}">分析</button><button data-csv-add="${stock.code}">追加</button></span>
    </div>
  `;
}

function bulkAnalysisPanel(state) {
  const visible = visibleBulkResults(state);
  const summary = buildBulkAnalysisSummary(state.batchResults);
  return `
    <section class="panel wide bulk-panel">
      <div class="bulk-head">
        <div>
          <div class="panel-title">一括分析結果テーブル</div>
          <p>CSV取込データはユーザー提供データです。正確性・最新性は保証されません。</p>
        </div>
        ${CsvExportButton(!visible.length)}
      </div>
      ${BulkAnalysisSummary(summary)}
      ${BulkAnalysisFilters(state.bulkFilters)}
      <div class="bulk-count">表示中：${visible.length}件 / 分析対象：${state.batchResults.length}件</div>
      ${BulkAnalysisTable(visible)}
    </section>
  `;
}

function dashboardV2({ stock, indicators, scoreResult, summary, structuredSummary, aiSummary, aiSummaryStatus }, state) {
  const effectiveStructuredSummary = structuredSummary || stock.structuredSummary;
  const preTradeCheck = stock.preTradeCheck || state.analysis?.preTradeCheck;
  return `
    <section class="hero-card compact-hero">
      <div>
        <div class="stock-id">${stock.code} ${escapeHtml(stock.name)}</div>
        <div class="stock-meta-line">
          ${stock.market ? `<span>市場：${escapeHtml(stock.market)}</span>` : ""}
          ${stock.sector ? `<span>業種：${escapeHtml(stock.sector)}</span>` : ""}
        </div>
        <div class="source-badges">
          <span class="data-badge ${stock.dataSource.toLowerCase()}">${stock.dataSource}</span>
          <span class="data-badge">${escapeHtml(stock.dataSourceLabel)}</span>
          <span class="data-badge danger">${escapeHtml(tradableLabel(stock))}</span>
        </div>
      </div>
      <div class="hero-sub">
        <span>信頼度 ${scoreResult.confidence}%</span>
        <span>過熱リスク ${RiskBadge(scoreResult.overheatRisk)}</span>
      </div>
    </section>
    ${PrimaryDecisionCard({ stock, scoreResult, structuredSummary: effectiveStructuredSummary })}
    <section class="dashboard-grid prioritized-dashboard">
      ${AiSummaryMockPanel(aiSummary || stock.aiSummary || aiSummaryStatus || stock.aiSummaryStatus)}
      ${PreTradeCheckPanel(preTradeCheck, {
        code: stock.code,
        checkedItemIds: state.preTradeChecklist?.[stock.code]?.checkedItemIds || [],
        compact: true
      })}
      ${StructuredSummaryPanel(effectiveStructuredSummary)}
      ${KeyMetricsGrid({ stock, indicators, scoreResult })}
      <div class="detail-group-title">分析詳細</div>
      ${CollapsibleSection({ title: "理由・買い材料・注意点", children: ReasonPanel(summary), className: "wide" })}
      ${CollapsibleSection({ title: "テクニカル詳細", children: `${TechnicalPanel(stock, indicators)}${OverheatPanel(stock, indicators, scoreResult)}`, className: "wide" })}
      ${CollapsibleSection({ title: "財務サマリー詳細", children: FinancialSummaryPanel(stock), className: "wide" })}
      ${CollapsibleSection({ title: "ニュース・テーマ材料", children: `${compactThemeInput(state)}${ThemeSummaryPanel(stock.themeSummary || stock.themeSummaryStatus)}`, className: "wide" })}
      <div class="detail-group-title">データ確認</div>
      ${CollapsibleSection({ title: "開示・国策テーマ詳細", children: `${DisclosurePanel(stock, indicators)}${PolicyThemePanel(stock)}`, className: "wide" })}
      ${CollapsibleSection({ title: "スコア内訳", children: scoreDetails(scoreResult, stock), className: "wide" })}
      ${CollapsibleSection({ title: "データソース詳細", children: dataSourcePanel(stock), className: "wide" })}
    </section>
  `;
}

function compactThemeInput(state) {
  return `
    <div class="theme-input-row detail-theme-input">
      <input id="manualThemeInput" value="${escapeHtml(state?.manualThemeInput || "")}" placeholder="SpaceX上場観測, 宇宙関連, 衛星通信" />
      <button id="applyThemeBtn">テーマ反映</button>
      <span>手動テーマは外部APIへ送信しません</span>
    </div>
  `;
}

function dashboard({ stock, indicators, scoreResult, summary, structuredSummary, aiSummary, aiSummaryStatus, preTradeCheck }) {
  return `
    <section class="hero-card">
      <div>
        <div class="stock-id">${stock.code} ${escapeHtml(stock.name)}</div>
        <div class="source-badges">
          <span class="data-badge ${stock.dataSource.toLowerCase()}">${stock.dataSource}</span>
          <span class="data-badge">${escapeHtml(stock.dataSourceLabel)}</span>
          ${stock.storageSourceLabel ? `<span class="data-badge">${escapeHtml(stock.storageSourceLabel)}</span>` : ""}
          <span class="data-badge danger">${escapeHtml(tradableLabel(stock))}</span>
        </div>
        ${SignalBadge(scoreResult.signal)}
        <div class="hero-sub">
          <span>信頼度 ${scoreResult.confidence}%</span>
          <span>過熱リスク ${RiskBadge(scoreResult.overheatRisk)}</span>
        </div>
      </div>
      <div>
        ${ScoreGauge(scoreResult)}
        ${dataSourcePanel(stock)}
      </div>
    </section>
    <section class="dashboard-grid">
      ${TechnicalPanel(stock, indicators)}
      ${OverheatPanel(stock, indicators, scoreResult)}
      ${DisclosurePanel(stock, indicators)}
      ${FinancialSummaryPanel(stock)}
      ${PreTradeCheckPanel(preTradeCheck || stock.preTradeCheck, { code: stock.code })}
      ${StructuredSummaryPanel(structuredSummary || stock.structuredSummary)}
      ${ThemeSummaryPanel(stock.themeSummary || stock.themeSummaryStatus)}
      ${AiSummaryMockPanel(aiSummary || stock.aiSummary || aiSummaryStatus || stock.aiSummaryStatus)}
      ${PolicyThemePanel(stock)}
      ${ReasonPanel(summary)}
      ${scoreDetails(scoreResult, stock)}
    </section>
  `;
}

function dataSourcePanel(stock) {
  const view = getDataSourceDisplay(stock);
  return `
    <div class="data-source-panel">
      <div><span>データ種別</span><strong>${escapeHtml(view.dataSourceLabel)}</strong></div>
      <div><span>保存元</span><strong>${escapeHtml(view.storageSourceLabel)}</strong></div>
      <div><span>最終更新</span><strong>${escapeHtml(stock.lastUpdated)}</strong></div>
      <div><span>実売買利用</span><strong class="negative">${escapeHtml(tradableLabel(stock))}</strong></div>
      ${view.networkLabel ? `<div><span>実通信</span><strong>${escapeHtml(view.networkLabel)}</strong></div>` : ""}
      ${view.fetchLabel ? `<div><span>データ取得</span><strong>${escapeHtml(view.fetchLabel)}</strong></div>` : ""}
      ${view.dataPeriod ? `<div><span>データ期間</span><strong>${escapeHtml(view.dataPeriod)}</strong></div>` : ""}
      ${view.unconnectedLabel ? `<div><span>財務・決算・TDnet</span><strong>${escapeHtml(view.unconnectedLabel)}</strong></div>` : ""}
      ${stock.market ? `<div><span>市場</span><strong>${escapeHtml(stock.market)}</strong></div>` : ""}
      ${stock.sector ? `<div><span>業種</span><strong>${escapeHtml(stock.sector)}</strong></div>` : ""}
      ${stock.stockMasterSource ? `<div><span>銘柄マスター</span><strong>${escapeHtml(stock.stockMasterSource)}</strong></div>` : ""}
      ${view.fallbackReason ? `<div><span>フォールバック理由</span><strong>${escapeHtml(view.fallbackReason)}</strong></div>` : ""}
      ${view.errorSummary ? `<div><span>J-Quantsエラー概要</span><strong>${escapeHtml(view.errorSummary)}</strong></div>` : ""}
    </div>
  `;
}

function scoreDetails(scoreResult, stock) {
  const note = getScoreNotice(stock);
  return `
    <section class="panel wide">
      <div class="panel-title">スコア内訳</div>
      <div class="score-list">
        ${scoreResult.entries.map((entry) => `
          <div class="score-entry">
            <span>${escapeHtml(entry.label)}</span>
            <strong class="${entry.value >= 0 ? "positive" : "negative"}">${entry.value > 0 ? "+" : ""}${entry.value}</strong>
            ${entry.note ? `<small>${escapeHtml(entry.note)}</small>` : ""}
          </div>
        `).join("")}
      </div>
      <div class="summary-box">${note}</div>
    </section>
  `;
}

function watchPanel(state) {
  return `
    <section class="watch-panel">
      <div class="panel-title">監視リスト</div>
      <div class="watch-list">${state.watchlist.map((item) => watchButton(item)).join("")}</div>
    </section>
  `;
}

function watchButton(item) {
  const stock = listAvailableStocks().find((candidate) => candidate.code === item || candidate.name === item);
  const label = stock ? `${stock.code} ${stock.name}` : item;
  const source = stock?.dataSourceLabel || "モックデータ";
  const stored = stock?.storageSourceLabel ? ` / ${stock.storageSourceLabel}` : "";
  const tradable = stock ? tradableLabel(stock) : "実売買不可";
  return `<button data-watch="${escapeHtml(item)}"><span>${escapeHtml(label)}</span><small>${escapeHtml(source)}${escapeHtml(stored)} / ${escapeHtml(tradable)}</small></button>`;
}

function visibleBulkResults(state) {
  return sortBulkAnalysisResults(filterBulkAnalysisResults(state.batchResults, state.bulkFilters), state.bulkFilters.sortKey);
}

function tradableLabel(stock) {
  if (stock.tradableDataLabel) return String(stock.tradableDataLabel).replace("・要確認", "（要確認）");
  return stock.isTradableData ? "可" : "実売買不可";
}

const PRE_TRADE_CHECKLIST_KEY = "stockAnalyzer.preTradeChecklist";

function getStoredPreTradeChecklist() {
  try {
    const raw = globalThis.localStorage?.getItem(PRE_TRADE_CHECKLIST_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    return Object.fromEntries(Object.entries(parsed).map(([code, value]) => [
      String(code),
      {
        code: String(value?.code || code),
        checkedItemIds: Array.isArray(value?.checkedItemIds) ? value.checkedItemIds.map(String) : [],
        updatedAt: String(value?.updatedAt || "")
      }
    ]));
  } catch {
    return {};
  }
}

function saveStoredPreTradeChecklist(value) {
  try {
    const safe = {};
    Object.entries(value || {}).forEach(([code, entry]) => {
      safe[code] = {
        code: String(entry?.code || code),
        checkedItemIds: Array.isArray(entry?.checkedItemIds) ? entry.checkedItemIds.map(String) : [],
        updatedAt: String(entry?.updatedAt || new Date().toISOString())
      };
    });
    globalThis.localStorage?.setItem(PRE_TRADE_CHECKLIST_KEY, JSON.stringify(safe));
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

function addPreTradeWarningToStructuredSummary(structuredSummary, preTradeCheck) {
  if (!structuredSummary || !preTradeCheck) return structuredSummary;
  const caution = "実売買前には証券会社アプリ、会社IR、TDnet、最新ニュースを確認してください。";
  return {
    ...structuredSummary,
    preTrade: structuredSummary.preTrade || preTradeCheck.structuredSummaryPreTrade,
    cautions: [...new Set([...(structuredSummary.cautions || []), caution])],
    risks: {
      ...structuredSummary.risks,
      warnings: [...new Set([...(structuredSummary.risks?.warnings || []), caution])]
    }
  };
}

function withThemeSummary(stock, manualThemeInput = "") {
  if (!stock) return stock;
  const manualThemes = String(manualThemeInput || "").trim();
  if (!manualThemes && (stock.themeSummary || stock.themeSummaryStatus)) return stock;
  return {
    ...stock,
    manualThemes,
    themeSummary: buildThemeSummary(stock, { manualThemes })
  };
}

export function isJQuantsRealStock(stock) {
  return stock?.dataSource === "J_QUANTS_MAPPED" || stock?.dataSource === "J_QUANTS_REAL";
}

export function getDataSourceDisplay(stock) {
  if (!stock) {
    return {
      dataSourceLabel: "未選択",
      storageSourceLabel: "-",
      notice: "銘柄を選択すると、データ種別に応じた注意事項を表示します。",
      badge: "未選択"
    };
  }
  if (stock.fallbackUsed) {
    return {
      dataSourceLabel: "J-Quants取得失敗・mockフォールバック",
      storageSourceLabel: "モックデータ",
      notice: "J-Quants取得に失敗したためモックデータへフォールバックしています。実売買判断には使用しないでください。",
      badge: "mockフォールバック",
      fetchLabel: "J-Quants取得失敗・mockフォールバック",
      fallbackReason: stock.fallbackReason || "",
      errorSummary: stock.jquantsErrorSummary?.safeError || stock.jquantsErrorSummary?.message || ""
    };
  }
  if (isJQuantsRealStock(stock)) {
    return {
      dataSourceLabel: "J-Quants実データ",
      storageSourceLabel: "バックエンド / J-Quants",
      notice: "J-Quants日足データを使用しています。ただし財務・決算・TDnetは未接続であり、無料プランではデータ遅延や取得範囲制限があります。実売買判断には必ず公式情報を確認してください。",
      badge: "J-Quants実データ・要確認",
      networkLabel: stock.didNetworkRequest ? "あり" : "",
      fetchLabel: stock.cacheHit ? "キャッシュ利用" : stock.didNetworkRequest ? "J-Quants実通信" : "バックエンド取得",
      dataPeriod: formatDateRange(stock.realStockFrom || stock.from, stock.realStockTo || stock.to),
      unconnectedLabel: "未接続"
    };
  }
  if (stock.dataSource === "CSV") {
    return {
      dataSourceLabel: stock.dataSourceLabel || "CSV取込",
      storageSourceLabel: stock.storageSourceLabel || "CSVファイル取込",
      notice: "CSV取込データはユーザー提供データです。正確性・最新性は保証されません。実売買判断には必ず公式情報を確認してください。",
      badge: "CSV取込・要確認"
    };
  }
  return {
    dataSourceLabel: "モックデータ",
    storageSourceLabel: "モックデータ",
    notice: "現在はモックデータです。実売買判断には使用しないでください。",
    badge: "モックデータ"
  };
}

function getScoreNotice(stock) {
  if (isJQuantsRealStock(stock)) {
    return "J-Quants日足データを使ったテクニカル中心の参考スコアです。財務・決算・TDnetは未接続です。最終判断には公式情報確認が必要です。";
  }
  if (stock.dataSource === "CSV") {
    return "CSVデータはユーザー提供データです。正確性・最新性は保証されません。実売買判断には必ず公式情報を確認してください。";
  }
  if (stock.fallbackUsed) {
    return "J-Quants取得に失敗したためモックデータで表示しています。実際の投資判断には使えません。";
  }
  return "この判定はモックデータに基づくテスト結果です。実際の投資判断には使えません。";
}

function formatDateRange(from, to) {
  if (!from && !to) return "-";
  if (from && to) return `${from} 〜 ${to}`;
  return from || to || "-";
}

function formatMs(value) {
  const ms = Number(value);
  if (!Number.isFinite(ms) || ms <= 0) return "-";
  if (ms % 60000 === 0) return `${ms / 60000}分`;
  if (ms % 1000 === 0) return `${ms / 1000}秒`;
  return `${ms}ms`;
}

function formatSavedAt(value) {
  if (!value) return "不明";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (num) => String(num).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
