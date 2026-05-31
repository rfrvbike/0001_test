import { getInternalEnv } from "../config/env.js";
import { jquantsMockStocks } from "../data/jquantsMockData.js";
import {
  mapJQuantsDailyBarsToStockData,
  mapJQuantsMockToStockData
} from "./stockDataMapper.js";
import {
  buildJQuantsCacheKey,
  canMakeJQuantsRequest,
  getCachedJQuantsResult,
  recordJQuantsRequest,
  setCachedJQuantsResult,
  waitForJQuantsRateLimitIfNeeded
} from "./jquantsCache.js";
import {
  getStockMasterInfo,
  mergeStockMasterIntoStockData
} from "./stockMasterService.js";
import { calculateIndicators } from "../../src/logic/indicators.js";
import { calculateScore } from "../../src/logic/scoring.js";
import { buildReasonSummary } from "../../src/logic/summaryBuilder.js";
import { buildStructuredSummary } from "../../src/logic/structuredSummaryBuilder.js";
import { buildAiSummaryMock } from "../../src/logic/aiSummaryMockBuilder.js";
import { buildThemeSummary } from "../../src/logic/themeSummaryBuilder.js";
import { buildPreTradeCheck } from "../../src/logic/preTradeCheckBuilder.js";

export const JQUANTS_CONNECTION_CHECK_ENDPOINT = "/v2/markets/calendar";
export const JQUANTS_RAW_DAILY_BARS_ENDPOINT = "/v2/equities/bars/daily";
export const JQUANTS_FINS_SUMMARY_ENDPOINT = "/v2/fins/summary";
export const DEFAULT_RAW_FROM = "2026-01-01";
export const DEFAULT_RAW_TO = "2026-01-31";

// Future implementation notes:
// - J-Quants V2 authentication uses an API key in the x-api-key header.
// - The API key must stay only in this backend and must never be sent to the browser.
// - Production credentials should be read from server/.env.
// - The frontend should call only this local backend API.
// - This step intentionally performs no J-Quants stock/finance data request.

export function getJQuantsStatus(config = getInternalEnv()) {
  const validation = validateJQuantsConfig(config);
  const safeConfig = safeJQuantsConfig(config);

  if (!config.jquantsEnabled) {
    return {
      ok: true,
      enabled: false,
      apiVersion: config.apiVersion,
      mode: "mock",
      externalApiEnabled: false,
      didNetworkRequest: false,
      config: safeConfig,
      message: "J-Quants is disabled. Mock mode is active. No external request was made."
    };
  }

  if (!validation.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "config_error",
      externalApiEnabled: true,
      didNetworkRequest: false,
      config: safeConfig,
      missingFields: validation.missingFields,
      message: "J-Quants is enabled, but JQUANTS_API_KEY is missing. No external request was made."
    };
  }

  return {
    ok: true,
    enabled: true,
    apiVersion: config.apiVersion,
    mode: "api_key_ready",
    externalApiEnabled: true,
    didNetworkRequest: false,
    implemented: false,
    config: safeConfig,
    message: config.useRealStocks
      ? "J-Quants API key is configured. Real stock mode is enabled for /api/stocks/:code. No status-check external request was made."
      : "J-Quants API key is configured. Real stock mode is disabled, so /api/stocks/:code uses mock data. No external request was made."
  };
}

export function validateJQuantsConfig(config = getInternalEnv()) {
  if (!config.jquantsEnabled) {
    return {
      ok: true,
      enabled: false,
      apiVersion: config.apiVersion,
      missingFields: []
    };
  }

  const missingFields = config.jquantsApiKey ? [] : ["JQUANTS_API_KEY"];
  return {
    ok: missingFields.length === 0,
    enabled: true,
    apiVersion: config.apiVersion,
    missingFields
  };
}

export function checkJQuantsApiKeyReady(config = getInternalEnv()) {
  const validation = validateJQuantsConfig(config);
  if (!validation.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "config_error",
      didNetworkRequest: false,
      missingFields: validation.missingFields,
      message: "J-Quants is enabled, but JQUANTS_API_KEY is missing. No external request was made."
    };
  }

  return {
    ok: true,
    enabled: Boolean(config.jquantsEnabled),
    apiVersion: config.apiVersion,
    mode: config.jquantsEnabled ? "api_key_ready" : "mock",
    didNetworkRequest: false,
    implemented: false,
    config: safeJQuantsConfig(config),
    message: config.jquantsEnabled
      ? "J-Quants API key is configured. Real stock data fetch is not implemented in this step."
      : "J-Quants is disabled. Mock mode is active."
  };
}

export function checkJQuantsConnection(config = getInternalEnv()) {
  const ready = checkJQuantsApiKeyReady(config);
  if (!ready.ok) return ready;
  if (!config.jquantsEnabled) {
    return {
      ok: true,
      enabled: false,
      apiVersion: config.apiVersion,
      mode: "mock",
      implemented: false,
      didNetworkRequest: false,
      externalApiEnabled: false,
      config: safeJQuantsConfig(config),
      message: "J-Quants is disabled. Connection check was not executed."
    };
  }

  return fetchJQuantsConnectionCheck(config);
}

export async function fetchJQuantsConnectionCheck(config = getInternalEnv(), options = {}) {
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const checkedEndpoint = JQUANTS_CONNECTION_CHECK_ENDPOINT;
  const url = buildJQuantsUrl(config, checkedEndpoint);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.externalApiTimeoutMs);

  try {
    const response = await fetchImpl(url, {
      method: "GET",
      headers: {
        accept: "application/json",
        "x-api-key": config.jquantsApiKey
      },
      signal: controller.signal
    });
    const contentType = response.headers?.get?.("content-type") || "";
    const isJson = contentType.includes("application/json");
    const bodySummary = isJson ? await summarizeJsonResponse(response) : {};

    if (!response.ok) {
      return {
        ok: false,
        enabled: true,
        apiVersion: config.apiVersion,
        mode: "connection_error",
        externalApiEnabled: true,
        didNetworkRequest: true,
        statusCode: response.status,
        checkedEndpoint,
        dataKind: "connection_check_only",
        isJson,
        ...bodySummary,
        message: buildConnectionErrorMessage(response.status),
        safeError: buildSafeHttpError(response.status, response.statusText, config)
      };
    }

    return {
      ok: true,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "connection_ok",
      externalApiEnabled: true,
      didNetworkRequest: true,
      statusCode: response.status,
      checkedEndpoint,
      dataKind: "connection_check_only",
      isJson,
      ...bodySummary,
      message: "J-Quants connection check succeeded. No stock analysis data was fetched."
    };
  } catch (error) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "connection_error",
      externalApiEnabled: true,
      didNetworkRequest: true,
      statusCode: 0,
      checkedEndpoint,
      dataKind: "connection_check_only",
      message: "J-Quants connection check failed. Check API key or network status.",
      safeError: sanitizeJQuantsError(error, config)
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function getJQuantsStockData(code, config = getInternalEnv(), options = {}) {
  if (config.useRealStocks) return getJQuantsRealOrFallbackStockData(code, config, options);
  return getJQuantsMockStockData(code, config, {
    dataSourceLabel: "J-Quants接続準備用モック",
    tradableDataLabel: "実データ未取得",
    realStockMode: false
  });
}

function getJQuantsMockStockData(code, config = getInternalEnv(), options = {}) {
  const stock = jquantsMockStocks[String(code)];
  if (!stock) {
    return {
      ok: false,
      status: 404,
      didNetworkRequest: false,
      error: `J-Quants mock stock not found: ${code}`
    };
  }

  const mapped = mapJQuantsMockToStockData(stock, {
    dataSourceLabel: options.dataSourceLabel,
    tradableDataLabel: options.tradableDataLabel
  });
  const data = addStructuredSummaryToStockData({
    ...mapped,
    fallbackUsed: Boolean(options.fallbackUsed),
    fallbackReason: options.fallbackReason,
    jquantsErrorSummary: options.jquantsErrorSummary,
    retryAfterMs: options.retryAfterMs,
    rateLimitReason: options.rateLimitReason,
    realStockMode: Boolean(options.realStockMode)
  }, config);
  return {
    ok: true,
    didNetworkRequest: Boolean(options.didNetworkRequest),
    implemented: false,
    mode: "mock",
    apiVersion: config.apiVersion,
    fallbackUsed: Boolean(options.fallbackUsed),
    fallbackReason: options.fallbackReason,
    jquantsErrorSummary: options.jquantsErrorSummary,
    data
  };
}

export async function getJQuantsRealOrFallbackStockData(code, config = getInternalEnv(), options = {}) {
  if (!config.jquantsEnabled) {
    return fallbackOrError(code, config, {
      didNetworkRequest: false,
      fallbackReason: "J-Quants is disabled",
      safeError: "J-Quants is disabled"
    });
  }

  const validation = validateJQuantsConfig(config);
  if (!validation.ok) {
    return fallbackOrError(code, config, {
      didNetworkRequest: false,
      fallbackReason: "J-Quants API key is missing",
      safeError: "J-Quants API key is missing",
      missingFields: validation.missingFields
    });
  }

  const mapped = await fetchJQuantsMappedStockData({
    code,
    from: config.realStockFrom,
    to: config.realStockTo
  }, config, {
    ...options,
    cacheMode: config.useFinancials ? "stocks-financials-on" : "stocks-financials-off"
  });

  if (!mapped.ok) {
    return fallbackOrError(code, config, {
      didNetworkRequest: Boolean(mapped.didNetworkRequest),
      fallbackReason: mapped.safeError || mapped.message || "J-Quants mapped fetch failed",
      safeError: mapped.safeError || mapped.message || "J-Quants mapped fetch failed",
      statusCode: mapped.statusCode,
      retryAfterMs: mapped.retryAfterMs,
      rateLimitReason: mapped.rateLimitReason
    });
  }

  let stockData = {
    ...mapped.stockData,
    dataSource: "J_QUANTS_MAPPED",
    dataSourceLabel: "J-Quants実データ",
    isMock: false,
    isTradableData: false,
    tradableDataLabel: "J-Quants実データ・要確認",
    calculationWarnings: mapped.calculationWarnings,
    debugInfo: mapped.debugInfo,
    realStockFrom: config.realStockFrom,
    realStockTo: config.realStockTo,
    cacheHit: Boolean(mapped.cacheHit),
    cacheStored: Boolean(mapped.cacheStored),
    cacheKey: mapped.cacheKey,
    cacheSavedAt: mapped.cacheSavedAt,
    cacheExpiresAt: mapped.cacheExpiresAt,
    cacheTtlMs: mapped.cacheTtlMs,
    forceRefresh: Boolean(mapped.forceRefresh),
    useFinancialScore: Boolean(config.useFinancialScore),
    importantDisclosures: ["J-Quants日足データから変換した実データです。財務・決算・開示は未接続です"]
  };

  let financialResult = null;
  if (config.useFinancials) {
    financialResult = await fetchJQuantsFinancialSummary({ code }, config, {
      ...options,
      waitForRateLimit: true,
      rateLimitMaxWaitMs: options.financialRateLimitMaxWaitMs ?? 1500
    });
    stockData = mergeFinancialSummaryIntoStockData(stockData, financialResult);
  } else {
    stockData.financialSummaryStatus = {
      enabled: false,
      message: "Financial summary integration is disabled."
    };
  }

  const didNetworkRequest = Boolean(mapped.didNetworkRequest || financialResult?.didNetworkRequest);

  stockData = addStructuredSummaryToStockData(stockData, config);

  return {
    ok: true,
    didNetworkRequest,
    implemented: true,
    mode: "real_stock_ok",
    apiVersion: config.apiVersion,
    calculationWarnings: mapped.calculationWarnings,
    debugInfo: mapped.debugInfo,
    realStockFrom: config.realStockFrom,
    realStockTo: config.realStockTo,
    cacheHit: Boolean(mapped.cacheHit),
    cacheStored: Boolean(mapped.cacheStored),
    cacheKey: mapped.cacheKey,
    cacheSavedAt: mapped.cacheSavedAt,
    cacheExpiresAt: mapped.cacheExpiresAt,
    cacheTtlMs: mapped.cacheTtlMs,
    forceRefresh: Boolean(mapped.forceRefresh),
    data: stockData
  };

  return {
    ok: true,
    didNetworkRequest: mapped.didNetworkRequest,
    implemented: true,
    mode: "real_stock_ok",
    apiVersion: config.apiVersion,
    calculationWarnings: mapped.calculationWarnings,
    debugInfo: mapped.debugInfo,
    realStockFrom: config.realStockFrom,
    realStockTo: config.realStockTo,
    cacheHit: Boolean(mapped.cacheHit),
    cacheStored: Boolean(mapped.cacheStored),
    cacheKey: mapped.cacheKey,
    cacheSavedAt: mapped.cacheSavedAt,
    cacheExpiresAt: mapped.cacheExpiresAt,
    cacheTtlMs: mapped.cacheTtlMs,
    forceRefresh: Boolean(mapped.forceRefresh),
    data: {
      ...mapped.stockData,
      dataSource: "J_QUANTS_MAPPED",
      dataSourceLabel: "J-Quants実データ",
      isMock: false,
      isTradableData: false,
      tradableDataLabel: "J-Quants実データ・要確認",
      calculationWarnings: mapped.calculationWarnings,
      debugInfo: mapped.debugInfo,
      realStockFrom: config.realStockFrom,
      realStockTo: config.realStockTo,
      cacheHit: Boolean(mapped.cacheHit),
      cacheStored: Boolean(mapped.cacheStored),
      cacheKey: mapped.cacheKey,
      cacheSavedAt: mapped.cacheSavedAt,
      cacheExpiresAt: mapped.cacheExpiresAt,
      cacheTtlMs: mapped.cacheTtlMs,
      forceRefresh: Boolean(mapped.forceRefresh),
      importantDisclosures: ["J-Quants日足データから変換した実データです。財務・決算・開示は未接続です"]
    }
  };
}

function fallbackOrError(code, config, details) {
  if (!config.fallbackToMock) {
    return {
      ok: false,
      status: details.statusCode || 400,
      didNetworkRequest: details.didNetworkRequest,
      mode: "real_stock_error",
      fallbackUsed: false,
      missingFields: details.missingFields,
      retryAfterMs: details.retryAfterMs,
      rateLimitReason: details.rateLimitReason,
      safeError: details.safeError,
      error: details.safeError
    };
  }

  return getJQuantsMockStockData(code, config, {
    dataSourceLabel: "J-Quants取得失敗・mockフォールバック",
    tradableDataLabel: "実売買不可",
    didNetworkRequest: Boolean(details.didNetworkRequest),
    fallbackUsed: true,
    fallbackReason: details.fallbackReason,
    jquantsErrorSummary: details.safeError,
    retryAfterMs: details.retryAfterMs,
    rateLimitReason: details.rateLimitReason,
    realStockMode: true
  });
}

export function getJQuantsStockList(codes = [], config = getInternalEnv()) {
  const validation = validateJQuantsConfig(config);
  if (!validation.ok) {
    return {
      ok: false,
      status: 400,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "config_error",
      didNetworkRequest: false,
      missingFields: validation.missingFields,
      error: "J-Quants is enabled, but JQUANTS_API_KEY is missing. No external request was made."
    };
  }

  const targetCodes = codes.length ? codes : Object.keys(jquantsMockStocks);
  const apiKeyReady = config.jquantsEnabled;
  const stocks = targetCodes
    .map((code) => jquantsMockStocks[String(code)])
    .filter(Boolean)
    .map((stock) => mapJQuantsMockToStockData(stock, apiKeyReady ? {
      dataSourceLabel: "J-Quants APIキー設定済み・実データ未取得",
      tradableDataLabel: "実データ未取得"
    } : {}));
  return {
    ok: true,
    didNetworkRequest: false,
    implemented: false,
    mode: apiKeyReady ? "api_key_ready" : "mock",
    apiVersion: config.apiVersion,
    dataSource: "J_QUANTS_MOCK",
    count: stocks.length,
    stocks
  };
}

export async function fetchJQuantsRawDailyBars({ code, from = DEFAULT_RAW_FROM, to = DEFAULT_RAW_TO } = {}, config = getInternalEnv(), options = {}) {
  const internal = await fetchJQuantsRawDailyBarsInternal({ code, from, to }, config, options);
  if (!internal.ok) return internal;
  return {
    ...withoutRawRows(internal),
    ...sanitizeRawDailyBarsResponse({ data: internal.rawRows, pagination_key: internal.hasPaginationKey ? "present" : undefined }),
    message: "J-Quants raw stock data fetch succeeded. This data is for structure check only and is not used for scoring yet."
  };
}

export async function fetchJQuantsRawDailyBarsInternal({ code, from = DEFAULT_RAW_FROM, to = DEFAULT_RAW_TO } = {}, config = getInternalEnv(), options = {}) {
  const validation = validateJQuantsConfig(config);
  const checkedEndpoint = JQUANTS_RAW_DAILY_BARS_ENDPOINT;
  const normalizedCode = String(code || "").trim();
  const normalizedFrom = String(from || DEFAULT_RAW_FROM);
  const normalizedTo = String(to || DEFAULT_RAW_TO);

  if (!config.jquantsEnabled) {
    return {
      ok: false,
      enabled: false,
      apiVersion: config.apiVersion,
      mode: "mock",
      dataKind: "jquants_raw_check_only",
      didNetworkRequest: false,
      checkedEndpoint,
      code: normalizedCode,
      from: normalizedFrom,
      to: normalizedTo,
      message: "J-Quants is disabled. Raw data fetch was not executed."
    };
  }

  if (!validation.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "config_error",
      dataKind: "jquants_raw_check_only",
      didNetworkRequest: false,
      checkedEndpoint,
      code: normalizedCode,
      from: normalizedFrom,
      to: normalizedTo,
      missingFields: validation.missingFields,
      message: "J-Quants API key is missing. Raw data fetch was not executed."
    };
  }

  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const url = buildJQuantsUrl(
    config,
    `${checkedEndpoint}?code=${encodeURIComponent(normalizedCode)}&from=${encodeURIComponent(normalizedFrom)}&to=${encodeURIComponent(normalizedTo)}`
  );
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.externalApiTimeoutMs);

  try {
    const response = await fetchImpl(url, {
      method: "GET",
      headers: {
        accept: "application/json",
        "x-api-key": config.jquantsApiKey
      },
      signal: controller.signal
    });
    const contentType = response.headers?.get?.("content-type") || "";
    const isJson = contentType.includes("application/json");

    if (!response.ok) {
      return {
        ok: false,
        enabled: true,
        apiVersion: config.apiVersion,
        mode: "raw_fetch_error",
        dataKind: "jquants_raw_check_only",
        didNetworkRequest: true,
        statusCode: response.status,
        checkedEndpoint,
        code: normalizedCode,
        from: normalizedFrom,
        to: normalizedTo,
        contentType,
        safeError: buildRawSafeHttpError(response.status, response.statusText, config),
        message: "J-Quants raw stock data fetch failed. Check code, date range, API key, plan status, or rate limit."
      };
    }

    const body = isJson ? await response.json().catch(() => null) : null;
    const rawRows = Array.isArray(body?.data) ? body.data : Array.isArray(body) ? body : [];
    return {
      ok: true,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "raw_fetch_ok",
      dataKind: "jquants_raw_check_only",
      didNetworkRequest: true,
      statusCode: response.status,
      checkedEndpoint,
      code: normalizedCode,
      from: normalizedFrom,
      to: normalizedTo,
      contentType,
      rawRows,
      rowCount: rawRows.length,
      hasPaginationKey: Boolean(body?.pagination_key),
      message: "J-Quants raw stock data fetch succeeded. This data is for structure check only and is not used for scoring yet."
    };
  } catch (error) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "raw_fetch_error",
      dataKind: "jquants_raw_check_only",
      didNetworkRequest: true,
      statusCode: 0,
      checkedEndpoint,
      code: normalizedCode,
      from: normalizedFrom,
      to: normalizedTo,
      safeError: sanitizeJQuantsError(error, config),
      message: "J-Quants raw stock data fetch failed. Check code, date range, API key, plan status, rate limit, or network status."
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchJQuantsMappedStockData({ code, from = DEFAULT_RAW_FROM, to = DEFAULT_RAW_TO } = {}, config = getInternalEnv(), options = {}) {
  const normalizedCode = String(code || "").trim();
  const normalizedFrom = String(from || DEFAULT_RAW_FROM);
  const normalizedTo = String(to || DEFAULT_RAW_TO);
  const cacheMode = options.cacheMode || "mapped";
  const forceRefresh = String(options.forceRefresh || "").toLowerCase() === "true" || options.forceRefresh === true;
  const cacheKey = buildJQuantsCacheKey({
    code: normalizedCode,
    from: normalizedFrom,
    to: normalizedTo,
    endpoint: JQUANTS_RAW_DAILY_BARS_ENDPOINT,
    mode: cacheMode
  });

  const validation = validateJQuantsConfig(config);
  if (!config.jquantsEnabled || !validation.ok) {
    const rawResult = await fetchJQuantsRawDailyBarsInternal({ code, from, to }, config, options);
    return {
      ...rawResult,
      mode: "mapped_fetch_error",
      dataKind: "jquants_mapped_check_only",
      cacheHit: false,
      cacheKey,
      forceRefresh,
      message: "J-Quants mapped fetch failed. Check code, date range, API key, or plan status."
    };
  }

  if (!forceRefresh) {
    const cached = getCachedJQuantsResult(cacheKey, config);
    if (cached) return cached;
  }

  const rateLimit = canMakeJQuantsRequest(config);
  if (!rateLimit.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "mapped_fetch_error",
      dataKind: "jquants_mapped_check_only",
      didNetworkRequest: false,
      statusCode: 429,
      checkedEndpoint: JQUANTS_RAW_DAILY_BARS_ENDPOINT,
      code: normalizedCode,
      from: normalizedFrom,
      to: normalizedTo,
      cacheHit: false,
      cacheKey,
      forceRefresh,
      rateLimited: true,
      rateLimitReason: rateLimit.reason,
      retryAfterMs: rateLimit.retryAfterMs,
      safeError: `Rate limited: ${rateLimit.reason}`,
      message: "J-Quants request was blocked by local rate control. No external request was made."
    };
  }

  const rawResult = await fetchJQuantsRawDailyBarsInternal({ code, from, to }, config, options);
  if (rawResult.didNetworkRequest) recordJQuantsRequest(Date.now(), config);
  if (!rawResult.ok) {
    return {
      ...rawResult,
      mode: "mapped_fetch_error",
      dataKind: "jquants_mapped_check_only",
      cacheHit: false,
      cacheKey,
      forceRefresh,
      message: "J-Quants mapped fetch failed. Check code, date range, API key, or plan status."
    };
  }

  const mapped = mapJQuantsDailyBarsToStockData({ data: rawResult.rawRows }, { code });
  const masterInfo = getStockMasterInfo(normalizedCode);
  const stockData = mergeStockMasterIntoStockData(mapped.stockData, masterInfo);
  const result = {
    ok: true,
    enabled: true,
    apiVersion: rawResult.apiVersion,
    mode: "mapped_fetch_ok",
    dataKind: "jquants_mapped_check_only",
    didNetworkRequest: rawResult.didNetworkRequest,
    statusCode: rawResult.statusCode,
    checkedEndpoint: rawResult.checkedEndpoint,
    code: rawResult.code,
    from: rawResult.from,
    to: rawResult.to,
    rawRowCount: rawResult.rowCount,
    stockData,
    calculationWarnings: mapped.calculationWarnings,
    debugInfo: mapped.debugInfo,
    cacheHit: false,
    cacheStored: false,
    cacheKey,
    cacheTtlMs: config.cacheTtlMs,
    forceRefresh,
    message: "J-Quants raw data was mapped to stockData format. This endpoint is for structure check only and is not used for scoring yet."
  };
  const cacheResult = setCachedJQuantsResult(cacheKey, result, { ttlMs: config.cacheTtlMs }, config);
  return {
    ...result,
    cacheStored: Boolean(cacheResult.stored),
    cacheSavedAt: cacheResult.savedAt,
    cacheExpiresAt: cacheResult.expiresAt
  };
}

export async function fetchJQuantsFinancialSummary({ code } = {}, config = getInternalEnv(), options = {}) {
  const normalizedCode = String(code || "").trim();
  const forceRefresh = String(options.forceRefresh || "").toLowerCase() === "true" || options.forceRefresh === true;
  const cacheKey = buildJQuantsCacheKey({
    code: normalizedCode,
    from: "",
    to: "",
    endpoint: JQUANTS_FINS_SUMMARY_ENDPOINT,
    mode: "fins-summary"
  });
  const validation = validateJQuantsConfig(config);

  if (!config.jquantsEnabled || !validation.ok) {
    const internal = await fetchJQuantsFinancialSummaryInternal({ code: normalizedCode }, config, options);
    return {
      ...internal,
      cacheHit: false,
      cacheKey,
      forceRefresh,
      message: internal.message || "J-Quants financial summary fetch was not executed."
    };
  }

  if (!forceRefresh) {
    const cached = getCachedJQuantsResult(cacheKey, config);
    if (cached) return cached;
  }

  if (options.waitForRateLimit) {
    const waitResult = await waitForJQuantsRateLimitIfNeeded(config, {
      maxWaitMs: options.rateLimitMaxWaitMs ?? 1500
    });
    if (!waitResult.ok) {
      return {
        ok: false,
        enabled: true,
        apiVersion: config.apiVersion,
        mode: "rate_limited",
        dataKind: "jquants_fins_summary_check_only",
        didNetworkRequest: false,
        statusCode: 429,
        checkedEndpoint: JQUANTS_FINS_SUMMARY_ENDPOINT,
        code: normalizedCode,
        cacheHit: false,
        cacheKey,
        forceRefresh,
        rateLimited: true,
        rateLimitReason: waitResult.reason,
        retryAfterMs: waitResult.retryAfterMs,
        rateLimitWaited: Boolean(waitResult.waited),
        rateLimitWaitedMs: waitResult.waitedMs || 0,
        message: "J-Quants request was blocked by local rate control."
      };
    }
  }

  const rateLimit = canMakeJQuantsRequest(config);
  if (!rateLimit.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "rate_limited",
      dataKind: "jquants_fins_summary_check_only",
      didNetworkRequest: false,
      statusCode: 429,
      checkedEndpoint: JQUANTS_FINS_SUMMARY_ENDPOINT,
      code: normalizedCode,
      cacheHit: false,
      cacheKey,
      forceRefresh,
      rateLimited: true,
      rateLimitReason: rateLimit.reason,
      retryAfterMs: rateLimit.retryAfterMs,
      message: "J-Quants request was blocked by local rate control."
    };
  }

  const internal = await fetchJQuantsFinancialSummaryInternal({ code: normalizedCode }, config, options);
  if (internal.didNetworkRequest) recordJQuantsRequest(Date.now(), config);
  if (!internal.ok) {
    return {
      ...internal,
      cacheHit: false,
      cacheKey,
      forceRefresh,
      message: internal.message || "J-Quants financial summary fetch failed. Check code, API key, plan status, or endpoint parameters."
    };
  }

  const sanitized = sanitizeFinancialSummaryResponse({ data: internal.rawRows }, { code: normalizedCode });
  const result = {
    ok: true,
    enabled: true,
    apiVersion: internal.apiVersion,
    mode: "fins_summary_ok",
    dataKind: "jquants_fins_summary_check_only",
    didNetworkRequest: internal.didNetworkRequest,
    statusCode: internal.statusCode,
    checkedEndpoint: internal.checkedEndpoint,
    code: internal.code,
    contentType: internal.contentType,
    ...sanitized,
    cacheHit: false,
    cacheStored: false,
    cacheKey,
    cacheTtlMs: config.cacheTtlMs,
    forceRefresh,
    message: "J-Quants financial summary fetch succeeded. This endpoint is for structure check only and is not used for scoring yet."
  };
  const cacheResult = setCachedJQuantsResult(cacheKey, result, { ttlMs: config.cacheTtlMs }, config);
  return {
    ...result,
    cacheStored: Boolean(cacheResult.stored),
    cacheSavedAt: cacheResult.savedAt,
    cacheExpiresAt: cacheResult.expiresAt
  };
}

export async function fetchJQuantsFinancialSummaryInternal({ code } = {}, config = getInternalEnv(), options = {}) {
  const validation = validateJQuantsConfig(config);
  const checkedEndpoint = JQUANTS_FINS_SUMMARY_ENDPOINT;
  const normalizedCode = String(code || "").trim();

  if (!config.jquantsEnabled) {
    return {
      ok: false,
      enabled: false,
      apiVersion: config.apiVersion,
      mode: "mock",
      dataKind: "jquants_fins_summary_check_only",
      didNetworkRequest: false,
      checkedEndpoint,
      code: normalizedCode,
      message: "J-Quants is disabled. Financial summary fetch was not executed."
    };
  }

  if (!validation.ok) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "config_error",
      dataKind: "jquants_fins_summary_check_only",
      didNetworkRequest: false,
      checkedEndpoint,
      code: normalizedCode,
      missingFields: validation.missingFields,
      message: "J-Quants API key is missing. Financial summary fetch was not executed."
    };
  }

  const fetchImpl = options.fetchImpl || globalThis.fetch;
  const url = buildJQuantsUrl(config, `${checkedEndpoint}?code=${encodeURIComponent(normalizedCode)}`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.externalApiTimeoutMs);

  try {
    const response = await fetchImpl(url, {
      method: "GET",
      headers: {
        accept: "application/json",
        "x-api-key": config.jquantsApiKey
      },
      signal: controller.signal
    });
    const contentType = response.headers?.get?.("content-type") || "";
    const isJson = contentType.includes("application/json");

    if (!response.ok) {
      return {
        ok: false,
        enabled: true,
        apiVersion: config.apiVersion,
        mode: "fins_summary_error",
        dataKind: "jquants_fins_summary_check_only",
        didNetworkRequest: true,
        statusCode: response.status,
        checkedEndpoint,
        code: normalizedCode,
        contentType,
        safeError: buildFinancialSafeHttpError(response.status, response.statusText, config),
        message: "J-Quants financial summary fetch failed. Check code, API key, plan status, or endpoint parameters."
      };
    }

    const body = isJson ? await response.json().catch(() => null) : null;
    const rawRows = Array.isArray(body?.data) ? body.data : Array.isArray(body) ? body : [];
    return {
      ok: true,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "fins_summary_raw_ok",
      dataKind: "jquants_fins_summary_check_only",
      didNetworkRequest: true,
      statusCode: response.status,
      checkedEndpoint,
      code: normalizedCode,
      contentType,
      rawRows,
      rowCount: rawRows.length,
      hasPaginationKey: Boolean(body?.pagination_key),
      message: "J-Quants financial summary raw fetch succeeded."
    };
  } catch (error) {
    return {
      ok: false,
      enabled: true,
      apiVersion: config.apiVersion,
      mode: "fins_summary_error",
      dataKind: "jquants_fins_summary_check_only",
      didNetworkRequest: true,
      statusCode: 0,
      checkedEndpoint,
      code: normalizedCode,
      safeError: sanitizeJQuantsError(error, config),
      message: "J-Quants financial summary fetch failed. Check code, API key, plan status, rate limit, or network status."
    };
  } finally {
    clearTimeout(timeout);
  }
}

export function sanitizeFinancialSummaryResponse(raw, options = {}) {
  const rows = Array.isArray(raw?.data) ? raw.data : Array.isArray(raw) ? raw : [];
  const columns = rows[0] && typeof rows[0] === "object" ? Object.keys(rows[0]) : [];
  const latestDisclosure = extractLatestFinancialSummary(rows);
  const importantColumns = [
    "DisclosedDate", "DiscDate", "DisclosedTime", "DiscTime", "LocalCode", "Code",
    "TypeOfDocument", "DocType", "Sales", "NetSales", "OP", "OperatingProfit",
    "OdP", "OrdinaryProfit", "NP", "Profit", "EPS", "EarningsPerShare", "DPS",
    "DividendPerShareAnnual", "FDSales", "ForecastNetSales", "FDOP",
    "ForecastOperatingProfit", "FDNP", "ForecastProfit", "FDEPS",
    "ForecastEarningsPerShare", "FDDPS", "ForecastDividendPerShareAnnual"
  ].filter((column) => columns.includes(column));
  return {
    rowCount: rows.length,
    columnsCount: columns.length,
    importantColumns,
    sampleRows: rows.slice(0, 3).map(sanitizeFinancialSampleRow),
    latestDisclosure,
    debugInfo: {
      code: options.code || "",
      rowCount: rows.length,
      latestDisclosureFound: Boolean(latestDisclosure),
      latestDisclosureFieldHints: latestDisclosure?.fieldHints || undefined,
      latestRowSelectedBy: latestDisclosure?.selectedBy || undefined,
      latestRowHasFinancialValues: Boolean(latestDisclosure?.hasFinancialValues),
      financialValueRowCount: rows.filter(hasFinancialValues).length,
      salesFieldUsed: latestDisclosure?.fieldHints?.netSales || null,
      operatingProfitFieldUsed: latestDisclosure?.fieldHints?.operatingProfit || null,
      profitFieldUsed: latestDisclosure?.fieldHints?.profit || null,
      epsFieldUsed: latestDisclosure?.fieldHints?.earningsPerShare || null,
      dividendFieldUsed: latestDisclosure?.fieldHints?.dividendPerShareAnnual || null
    }
  };
}

export function extractLatestFinancialSummary(rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const sorted = [...rows].sort((a, b) => compareFinancialRows(a, b));
  const latestByDate = sorted[sorted.length - 1] || {};
  const financialRows = sorted.filter(hasFinancialValues);
  const latestFinancial = financialRows[financialRows.length - 1] || null;
  const latest = hasFinancialValues(latestByDate) ? latestByDate : latestFinancial || latestByDate;
  const selectedBy = latest === latestByDate
    ? "latest_disclosure_date"
    : "latest_row_with_financial_values";
  const fieldHints = {};
  const pick = (name, candidates, type = "string") => {
    const field = candidates.find((candidate) => latest[candidate] !== undefined && latest[candidate] !== null && latest[candidate] !== "");
    fieldHints[name] = field || null;
    const value = field ? latest[field] : null;
    return type === "number" ? toFiniteNumberOrNull(value) : value ?? null;
  };

  return {
    disclosedDate: pick("disclosedDate", ["DisclosedDate", "DiscDate"]),
    disclosedTime: pick("disclosedTime", ["DisclosedTime", "DiscTime"]),
    localCode: pick("localCode", ["LocalCode", "Code"]),
    typeOfDocument: pick("typeOfDocument", ["TypeOfDocument", "DocType"]),
    netSales: pick("netSales", ["NetSales", "Sales"], "number"),
    operatingProfit: pick("operatingProfit", ["OperatingProfit", "OP"], "number"),
    ordinaryProfit: pick("ordinaryProfit", ["OrdinaryProfit", "OdP"], "number"),
    profit: pick("profit", ["Profit", "NP"], "number"),
    earningsPerShare: pick("earningsPerShare", ["EarningsPerShare", "EPS"], "number"),
    dividendPerShareAnnual: pick("dividendPerShareAnnual", ["DividendPerShareAnnual", "DPS"], "number"),
    totalAssets: pick("totalAssets", ["TotalAssets", "TA"], "number"),
    equity: pick("equity", ["Equity", "Eq"], "number"),
    equityRatio: pick("equityRatio", ["EquityRatio", "EqR"], "number"),
    bookValuePerShare: pick("bookValuePerShare", ["BookValuePerShare", "BPS"], "number"),
    cashFlowsFromOperatingActivities: pick("cashFlowsFromOperatingActivities", ["CashFlowsFromOperatingActivities", "CFO"], "number"),
    cashFlowsFromInvestingActivities: pick("cashFlowsFromInvestingActivities", ["CashFlowsFromInvestingActivities", "CFI"], "number"),
    cashFlowsFromFinancingActivities: pick("cashFlowsFromFinancingActivities", ["CashFlowsFromFinancingActivities", "CFF"], "number"),
    cashAndEquivalents: pick("cashAndEquivalents", ["CashAndEquivalents", "Cash"], "number"),
    forecastNetSales: pick("forecastNetSales", ["ForecastNetSales", "FDSales"], "number"),
    forecastOperatingProfit: pick("forecastOperatingProfit", ["ForecastOperatingProfit", "FDOP"], "number"),
    forecastOrdinaryProfit: pick("forecastOrdinaryProfit", ["ForecastOrdinaryProfit"], "number"),
    forecastProfit: pick("forecastProfit", ["ForecastProfit", "FDNP"], "number"),
    forecastEarningsPerShare: pick("forecastEarningsPerShare", ["ForecastEarningsPerShare", "FDEPS"], "number"),
    forecastDividendPerShareAnnual: pick("forecastDividendPerShareAnnual", ["ForecastDividendPerShareAnnual", "FDDPS"], "number"),
    fieldHints,
    selectedBy,
    hasFinancialValues: hasFinancialValues(latest)
  };
}

export function mapFinancialSummaryToStockFinancialData(summary) {
  if (!summary) return null;
  return {
    available: true,
    source: "J_QUANTS_FINS_SUMMARY",
    checkedEndpoint: JQUANTS_FINS_SUMMARY_ENDPOINT,
    latestEarningsDate: summary.disclosedDate || "",
    disclosedDate: summary.disclosedDate || "",
    disclosedTime: summary.disclosedTime || "",
    localCode: summary.localCode || "",
    typeOfDocument: summary.typeOfDocument || "",
    netSales: summary.netSales ?? null,
    operatingProfit: summary.operatingProfit ?? null,
    ordinaryProfit: summary.ordinaryProfit ?? null,
    profit: summary.profit ?? null,
    earningsPerShare: summary.earningsPerShare ?? null,
    dividendPerShareAnnual: summary.dividendPerShareAnnual ?? null,
    totalAssets: summary.totalAssets ?? null,
    equity: summary.equity ?? null,
    equityRatio: summary.equityRatio ?? null,
    bookValuePerShare: summary.bookValuePerShare ?? null,
    cashFlowsFromOperatingActivities: summary.cashFlowsFromOperatingActivities ?? null,
    cashFlowsFromInvestingActivities: summary.cashFlowsFromInvestingActivities ?? null,
    cashFlowsFromFinancingActivities: summary.cashFlowsFromFinancingActivities ?? null,
    cashAndEquivalents: summary.cashAndEquivalents ?? null,
    forecastNetSales: summary.forecastNetSales ?? null,
    forecastOperatingProfit: summary.forecastOperatingProfit ?? null,
    forecastProfit: summary.forecastProfit ?? null,
    forecastEarningsPerShare: summary.forecastEarningsPerShare ?? null,
    forecastDividendPerShareAnnual: summary.forecastDividendPerShareAnnual ?? null
  };
}

export function buildFinancialSignals(financialSummary) {
  const scoreResult = calculateFinancialSignalScore(financialSummary);
  if (!financialSummary?.available) {
    return {
      hasFinancialSummary: false,
      financialScore: 0,
      financialScoreMax: 5,
      financialScoreMin: -5,
      financialScoreLabel: "財務未取得",
      financialComment: "財務サマリーを取得できなかったため、株価・テクニカル情報中心の判定です。",
      warning: "財務サマリーを取得できませんでした。株価・テクニカル情報のみ表示しています。"
    };
  }
  return {
    hasFinancialSummary: true,
    isProfitable: Number(financialSummary.profit) > 0,
    hasOperatingProfit: Number(financialSummary.operatingProfit) > 0,
    hasPositiveEps: Number(financialSummary.earningsPerShare) > 0,
    hasPositiveOperatingCashFlow: Number(financialSummary.cashFlowsFromOperatingActivities) > 0,
    hasDividend: Number(financialSummary.dividendPerShareAnnual) > 0,
    hasForecast: [
      financialSummary.forecastNetSales,
      financialSummary.forecastOperatingProfit,
      financialSummary.forecastProfit,
      financialSummary.forecastEarningsPerShare
    ].some((value) => value !== null && value !== undefined && value !== ""),
    financialScore: scoreResult.score,
    financialScoreMax: 5,
    financialScoreMin: -5,
    financialScoreLabel: scoreResult.label,
    financialComment: scoreResult.comment,
    warning: "財務サマリーは取得済みですが、通常スコアへの本格反映はまだ行っていません。"
  };
}

function calculateFinancialSignalScore(financialSummary) {
  if (!financialSummary?.available) {
    return {
      score: 0,
      label: "財務未取得",
      comment: "財務サマリーを取得できなかったため、株価・テクニカル情報中心の判定です。"
    };
  }

  let score = 0;
  if (isPositiveFinancialValue(financialSummary.operatingProfit)) score += 1;
  if (isNegativeFinancialValue(financialSummary.operatingProfit)) score -= 2;
  if (isPositiveFinancialValue(financialSummary.profit)) score += 1;
  if (isNegativeFinancialValue(financialSummary.profit)) score -= 2;
  if (isPositiveFinancialValue(financialSummary.earningsPerShare)) score += 1;
  if (isNegativeFinancialValue(financialSummary.earningsPerShare)) score -= 1;
  if (isPositiveFinancialValue(financialSummary.cashFlowsFromOperatingActivities)) score += 1;
  if (isNegativeFinancialValue(financialSummary.cashFlowsFromOperatingActivities)) score -= 1;
  if (isPositiveFinancialValue(financialSummary.dividendPerShareAnnual)) score += 1;

  const bounded = Math.max(-5, Math.min(5, score));
  const label = bounded >= 4
    ? "財務はおおむね良好"
    : bounded > 0
      ? "財務はやや良好"
      : bounded < 0
        ? "財務に注意"
        : "財務は中立";
  const comment = bounded > 0
    ? "営業利益・純利益・EPSなどがプラスで、財務面は参考材料として悪くありません。ただし通常スコアへの反映は限定的です。"
    : bounded < 0
      ? "主要財務項目の一部に弱さがあり、財務面は注意材料です。ただし通常スコアへの反映は限定的です。"
      : "財務サマリーは取得済みですが、評価対象項目は中立です。";

  return { score: bounded, label, comment };
}

function isPositiveFinancialValue(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0;
}

function isNegativeFinancialValue(value) {
  const number = Number(value);
  return Number.isFinite(number) && number < 0;
}

function mergeFinancialSummaryIntoStockData(stockData, financialResult) {
  if (financialResult?.ok && financialResult.latestDisclosure) {
    const financialSummary = {
      ...mapFinancialSummaryToStockFinancialData(financialResult.latestDisclosure),
      cacheHit: Boolean(financialResult.cacheHit),
      didNetworkRequest: Boolean(financialResult.didNetworkRequest),
      rowCount: financialResult.rowCount ?? 0,
      cacheStored: Boolean(financialResult.cacheStored),
      cacheKey: financialResult.cacheKey,
      cacheSavedAt: financialResult.cacheSavedAt,
      cacheExpiresAt: financialResult.cacheExpiresAt
    };
    return {
      ...stockData,
      financialSummary,
      financialSignals: buildFinancialSignals(financialSummary),
      financialSummaryUnavailable: false,
      importantDisclosures: [
        "J-Quants日足データと財務サマリーを表示しています。通常スコアへの財務反映は未実装です"
      ]
    };
  }

  const financialSummary = {
    available: false,
    source: "J_QUANTS_FINS_SUMMARY",
    unavailableReason: financialResult?.mode === "rate_limited" ? "rate_limited" : "fetch_failed",
    safeError: financialResult?.safeError || financialResult?.message || "Financial summary unavailable",
    message: financialResult?.mode === "rate_limited"
      ? "ローカルレート制御により財務取得を後回しにしました。"
      : financialResult?.message,
    didNetworkRequest: Boolean(financialResult?.didNetworkRequest),
    cacheHit: Boolean(financialResult?.cacheHit),
    statusCode: financialResult?.statusCode,
    retryAfterMs: financialResult?.retryAfterMs,
    rateLimitReason: financialResult?.rateLimitReason,
    rateLimitWaited: Boolean(financialResult?.rateLimitWaited),
    rateLimitWaitedMs: financialResult?.rateLimitWaitedMs || 0
  };
  return {
    ...stockData,
    financialSummary,
    financialSignals: buildFinancialSignals(financialSummary),
    financialSummaryUnavailable: true,
    financialSummaryError: financialSummary.safeError
  };
}

function addStructuredSummaryToStockData(stockData, config = getInternalEnv()) {
  try {
    const stockWithTheme = addThemeSummaryToStockData(stockData, config);
    const indicators = calculateIndicators(stockWithTheme);
    const scoreResult = calculateScore(stockWithTheme, indicators);
    const summary = buildReasonSummary(stockWithTheme, indicators, scoreResult);
    const structuredSummary = buildStructuredSummary(stockWithTheme, scoreResult, {
      indicators,
      summary
    });
    const preTradeCheck = buildPreTradeCheck(stockWithTheme, {
      indicators,
      scoreResult,
      structuredSummary
    });
    const structuredSummaryWithPreTrade = {
      ...structuredSummary,
      preTrade: structuredSummary.preTrade || preTradeCheck.structuredSummaryPreTrade
    };
    return {
      ...stockWithTheme,
      preTradeCheck,
      structuredSummary: structuredSummaryWithPreTrade,
      ...buildAiSummaryFields(addPreTradeWarningToStructuredSummary(structuredSummaryWithPreTrade, preTradeCheck), config)
    };
  } catch (error) {
    const structuredSummary = {
      version: "1.0",
      generatedBy: "RULE_BASED",
      aiReady: false,
      aiGenerated: false,
      disclaimer: "このサマリーは投資助言ではありません。実売買前には必ず公式情報を確認してください。",
      decision: {
        label: "データ不足",
        shortLabel: "データ不足",
        confidence: "low",
        stance: "wait",
        reason: "判断サマリーを生成できませんでした。"
      },
      error: sanitizeJQuantsError(error)
    };
    return {
      ...addThemeSummaryToStockData(stockData, config),
      structuredSummary,
      preTradeCheck: buildPreTradeCheck(stockData),
      ...buildAiSummaryFields(structuredSummary, config)
    };
  }
}

function addThemeSummaryToStockData(stockData, config = getInternalEnv()) {
  if (!config.themeSummaryMockEnabled) {
    return {
      ...stockData,
      themeSummaryStatus: {
        enabled: false,
        source: "LOCAL_MOCK_THEME",
        externalNewsApiUsed: false,
        externalAiUsed: false,
        message: "ニュース・テーマ材料レイヤーは無効です。"
      }
    };
  }
  return {
    ...stockData,
    themeSummary: buildThemeSummary(stockData, { enabled: true })
  };
}

function buildAiSummaryFields(structuredSummary, config = getInternalEnv()) {
  if (!config.aiSummaryMockEnabled) {
    return {
      aiSummaryStatus: {
        enabled: false,
        mode: "disabled",
        aiGenerated: false,
        externalApiUsed: false,
        provider: "none",
        message: "AI要約モックは無効です。"
      }
    };
  }
  return {
    aiSummary: buildAiSummaryMock(structuredSummary, { enabled: true })
  };
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

function withoutRawRows(result) {
  const { rawRows, ...safeResult } = result;
  return safeResult;
}

export function sanitizeRawDailyBarsResponse(raw) {
  const rows = Array.isArray(raw?.data) ? raw.data : Array.isArray(raw) ? raw : [];
  const columns = rows[0] && typeof rows[0] === "object" ? Object.keys(rows[0]) : [];
  return {
    rowCount: rows.length,
    columns,
    sampleRows: rows.slice(0, 3).map(sanitizeSampleRow),
    hasPaginationKey: Boolean(raw?.pagination_key)
  };
}

function safeJQuantsConfig(config) {
  return {
    hasApiKey: Boolean(config.jquantsApiKey),
    useRealStocks: Boolean(config.useRealStocks),
    fallbackToMock: Boolean(config.fallbackToMock),
    realStockFrom: config.realStockFrom,
    realStockTo: config.realStockTo,
    cacheEnabled: Boolean(config.cacheEnabled),
    cacheTtlMs: config.cacheTtlMs,
    minRequestIntervalMs: config.minRequestIntervalMs,
    maxRequestsPerMinute: config.maxRequestsPerMinute,
    useFinancials: Boolean(config.useFinancials),
    financialsFallbackSilent: Boolean(config.financialsFallbackSilent),
    useFinancialScore: Boolean(config.useFinancialScore),
    aiSummary: {
      mockEnabled: Boolean(config.aiSummaryMockEnabled),
      externalApiEnabled: Boolean(config.aiSummaryExternalApiEnabled),
      provider: "none"
    },
    themeSummary: {
      mockEnabled: Boolean(config.themeSummaryMockEnabled),
      externalNewsApiEnabled: Boolean(config.themeSummaryExternalNewsApiEnabled),
      scoreEnabled: Boolean(config.themeSummaryScoreEnabled)
    }
  };
}

function buildJQuantsUrl(config, path) {
  const baseUrl = String(config.jquantsApiBaseUrl || "https://api.jquants.com").replace(/\/+$/, "");
  return `${baseUrl}${path}`;
}

function buildConnectionErrorMessage(statusCode) {
  if (statusCode === 401) return "J-Quants connection check failed. The API key may be invalid.";
  if (statusCode === 403) return "J-Quants responded, but this endpoint may be unavailable for the current plan or API key permissions.";
  return "J-Quants connection check failed. Check API key, plan status, or network status.";
}

function buildSafeHttpError(statusCode, statusText, config) {
  if (statusCode === 401) return "Unauthorized";
  if (statusCode === 403) return "Forbidden: endpoint permission or plan may be insufficient";
  return sanitizeJQuantsError(`${statusCode} ${statusText || ""}`, config);
}

function buildRawSafeHttpError(statusCode, statusText, config) {
  if (statusCode === 400) return "Bad Request: code/date parameters may be invalid.";
  if (statusCode === 401) return "Unauthorized: API key may be invalid.";
  if (statusCode === 403) return "Forbidden: endpoint permission or plan may be insufficient.";
  if (statusCode === 429) return "Too Many Requests: rate limit may have been exceeded.";
  return sanitizeJQuantsError(`${statusCode} ${statusText || ""}`, config);
}

function buildFinancialSafeHttpError(statusCode, statusText, config) {
  if (statusCode === 400) return "Bad Request: code parameter may be invalid.";
  if (statusCode === 401) return "Unauthorized: API key may be invalid.";
  if (statusCode === 403) return "Forbidden: endpoint permission or plan may be insufficient.";
  if (statusCode === 429) return "Too Many Requests: rate limit may have been exceeded.";
  return sanitizeJQuantsError(`${statusCode} ${statusText || ""}`, config);
}

async function summarizeJsonResponse(response) {
  try {
    const body = await response.json();
    const data = Array.isArray(body?.data) ? body.data : Array.isArray(body) ? body : null;
    return {
      responseShape: data ? "array" : typeof body,
      count: data ? data.length : undefined,
      hasPaginationKey: Boolean(body?.pagination_key)
    };
  } catch {
    return { responseShape: "unreadable_json" };
  }
}

export function sanitizeJQuantsError(error, config = getInternalEnv()) {
  const raw = error instanceof Error ? error.message : String(error || "Unknown error");
  let safe = raw;
  if (config.jquantsApiKey) safe = safe.split(config.jquantsApiKey).join("[redacted]");
  safe = safe.replace(/x-api-key[^\s,;]*/gi, "x-api-key[redacted]");
  safe = safe.replace(/JQUANTS_API_KEY[^\s,;]*/g, "JQUANTS_API_KEY[redacted]");
  return safe.slice(0, 240);
}

function sanitizeSampleRow(row) {
  return Object.fromEntries(
    Object.entries(row || {}).map(([key, value]) => {
      if (value == null || ["string", "number", "boolean"].includes(typeof value)) return [key, value];
      return [key, String(value).slice(0, 120)];
    })
  );
}

function sanitizeFinancialSampleRow(row = {}) {
  const pick = (candidates) => {
    const field = candidates.find((candidate) => row[candidate] !== undefined && row[candidate] !== null && row[candidate] !== "");
    return field ? row[field] : null;
  };
  return {
    disclosedDate: pick(["DisclosedDate", "DiscDate"]),
    disclosedTime: pick(["DisclosedTime", "DiscTime"]),
    localCode: pick(["LocalCode", "Code"]),
    typeOfDocument: pick(["TypeOfDocument", "DocType"]),
    sales: pick(["Sales", "NetSales"]),
    operatingProfit: pick(["OP", "OperatingProfit"]),
    profit: pick(["NP", "Profit"]),
    earningsPerShare: pick(["EPS", "EarningsPerShare"]),
    dividendPerShareAnnual: pick(["DPS", "DividendPerShareAnnual"])
  };
}

function hasFinancialValues(row = {}) {
  const fields = [
    "NetSales", "Sales",
    "OperatingProfit", "OP",
    "OrdinaryProfit", "OdP",
    "Profit", "NP",
    "EarningsPerShare", "EPS",
    "DividendPerShareAnnual", "DPS",
    "TotalAssets", "TA",
    "Equity", "Eq",
    "EquityRatio", "EqR",
    "BookValuePerShare", "BPS",
    "CashFlowsFromOperatingActivities", "CFO",
    "CashFlowsFromInvestingActivities", "CFI",
    "CashFlowsFromFinancingActivities", "CFF",
    "CashAndEquivalents", "Cash",
    "ForecastNetSales", "FDSales",
    "ForecastOperatingProfit", "FDOP",
    "ForecastOrdinaryProfit",
    "ForecastProfit", "FDNP",
    "ForecastEarningsPerShare", "FDEPS",
    "ForecastDividendPerShareAnnual", "FDDPS"
  ];
  return fields.some((field) => toFiniteNumberOrNull(row[field]) !== null);
}

function compareFinancialRows(a, b) {
  const aKey = `${a?.DisclosedDate || a?.DiscDate || ""}T${a?.DisclosedTime || a?.DiscTime || ""}`;
  const bKey = `${b?.DisclosedDate || b?.DiscDate || ""}T${b?.DisclosedTime || b?.DiscTime || ""}`;
  if (aKey === bKey) return 0;
  if (!aKey.trim()) return -1;
  if (!bKey.trim()) return 1;
  return aKey.localeCompare(bKey);
}

function toFiniteNumberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const normalized = typeof value === "string" ? value.replace(/,/g, "") : value;
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
}
