import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const serverDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_ENV_PATH = path.join(serverDir, ".env");

const DEFAULTS = {
  JQUANTS_ENABLED: "false",
  JQUANTS_API_VERSION: "v2",
  JQUANTS_API_KEY: "",
  JQUANTS_API_BASE_URL: "https://api.jquants.com",
  JQUANTS_USE_REAL_STOCKS: "false",
  JQUANTS_REAL_STOCK_FROM: "2025-09-01",
  JQUANTS_REAL_STOCK_TO: "2026-01-31",
  JQUANTS_FALLBACK_TO_MOCK: "true",
  JQUANTS_CACHE_ENABLED: "true",
  JQUANTS_CACHE_TTL_MS: "300000",
  JQUANTS_MIN_REQUEST_INTERVAL_MS: "1000",
  JQUANTS_MAX_REQUESTS_PER_MINUTE: "20",
  JQUANTS_USE_FINANCIALS: "false",
  JQUANTS_FINANCIALS_FALLBACK_SILENT: "true",
  JQUANTS_USE_FINANCIAL_SCORE: "true",
  AI_SUMMARY_MOCK_ENABLED: "true",
  AI_SUMMARY_EXTERNAL_API_ENABLED: "false",
  THEME_SUMMARY_MOCK_ENABLED: "true",
  THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED: "false",
  THEME_SUMMARY_SCORE_ENABLED: "false",
  SERVER_HOST: "127.0.0.1",
  SERVER_PORT: "8787",
  EXTERNAL_API_TIMEOUT_MS: "10000"
};

export function loadEnv(options = {}) {
  const envFilePath = options.envFilePath ?? DEFAULT_ENV_PATH;
  const sourceEnv = options.processEnv ?? process.env;
  const fileEnv = readEnvFile(envFilePath);
  const merged = { ...DEFAULTS, ...fileEnv, ...sourceEnv };

  return {
    jquantsEnabled: toBoolean(merged.JQUANTS_ENABLED),
    apiVersion: String(merged.JQUANTS_API_VERSION || DEFAULTS.JQUANTS_API_VERSION),
    jquantsApiKey: String(merged.JQUANTS_API_KEY || ""),
    jquantsApiBaseUrl: String(merged.JQUANTS_API_BASE_URL || DEFAULTS.JQUANTS_API_BASE_URL),
    useRealStocks: toBoolean(merged.JQUANTS_USE_REAL_STOCKS),
    realStockFrom: String(merged.JQUANTS_REAL_STOCK_FROM || DEFAULTS.JQUANTS_REAL_STOCK_FROM),
    realStockTo: String(merged.JQUANTS_REAL_STOCK_TO || DEFAULTS.JQUANTS_REAL_STOCK_TO),
    fallbackToMock: toBoolean(merged.JQUANTS_FALLBACK_TO_MOCK),
    cacheEnabled: toBoolean(merged.JQUANTS_CACHE_ENABLED),
    cacheTtlMs: toNumber(merged.JQUANTS_CACHE_TTL_MS, Number(DEFAULTS.JQUANTS_CACHE_TTL_MS)),
    minRequestIntervalMs: toNumber(merged.JQUANTS_MIN_REQUEST_INTERVAL_MS, Number(DEFAULTS.JQUANTS_MIN_REQUEST_INTERVAL_MS)),
    maxRequestsPerMinute: toNumber(merged.JQUANTS_MAX_REQUESTS_PER_MINUTE, Number(DEFAULTS.JQUANTS_MAX_REQUESTS_PER_MINUTE)),
    useFinancials: toBoolean(merged.JQUANTS_USE_FINANCIALS),
    financialsFallbackSilent: toBoolean(merged.JQUANTS_FINANCIALS_FALLBACK_SILENT),
    useFinancialScore: toBoolean(merged.JQUANTS_USE_FINANCIAL_SCORE),
    aiSummaryMockEnabled: toBoolean(merged.AI_SUMMARY_MOCK_ENABLED),
    aiSummaryExternalApiEnabled: toBoolean(merged.AI_SUMMARY_EXTERNAL_API_ENABLED),
    themeSummaryMockEnabled: toBoolean(merged.THEME_SUMMARY_MOCK_ENABLED),
    themeSummaryExternalNewsApiEnabled: toBoolean(merged.THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED),
    themeSummaryScoreEnabled: toBoolean(merged.THEME_SUMMARY_SCORE_ENABLED),
    serverHost: String(merged.SERVER_HOST || DEFAULTS.SERVER_HOST),
    serverPort: toNumber(merged.SERVER_PORT, Number(DEFAULTS.SERVER_PORT)),
    externalApiTimeoutMs: toNumber(merged.EXTERNAL_API_TIMEOUT_MS, Number(DEFAULTS.EXTERNAL_API_TIMEOUT_MS)),
    envFileLoaded: Boolean(envFilePath && fs.existsSync(envFilePath))
  };
}

export function getEnv(options = {}) {
  return toSafeEnv(loadEnv(options));
}

export function getInternalEnv(options = {}) {
  return loadEnv(options);
}

export function getSafeEnvStatus(options = {}) {
  return getEnv(options);
}

export const env = {
  get host() {
    return loadEnv().serverHost;
  },
  get port() {
    return loadEnv().serverPort;
  },
  get jquantsEnabled() {
    return loadEnv().jquantsEnabled;
  }
};

function readEnvFile(envFilePath) {
  if (!envFilePath || !fs.existsSync(envFilePath)) return {};
  const text = fs.readFileSync(envFilePath, "utf8");
  return Object.fromEntries(
    text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"))
      .map((line) => {
        const index = line.indexOf("=");
        if (index === -1) return [line, ""];
        const key = line.slice(0, index).trim();
        const value = line.slice(index + 1).trim().replace(/^["']|["']$/g, "");
        return [key, value];
      })
  );
}

function toSafeEnv(config) {
  return {
    jquantsEnabled: config.jquantsEnabled,
    apiVersion: config.apiVersion,
    hasApiKey: Boolean(config.jquantsApiKey),
    useRealStocks: config.useRealStocks,
    fallbackToMock: config.fallbackToMock,
    realStockFrom: config.realStockFrom,
    realStockTo: config.realStockTo,
    cacheEnabled: config.cacheEnabled,
    cacheTtlMs: config.cacheTtlMs,
    minRequestIntervalMs: config.minRequestIntervalMs,
    maxRequestsPerMinute: config.maxRequestsPerMinute,
    useFinancials: config.useFinancials,
    financialsFallbackSilent: config.financialsFallbackSilent,
    useFinancialScore: config.useFinancialScore,
    aiSummary: {
      mockEnabled: config.aiSummaryMockEnabled,
      externalApiEnabled: config.aiSummaryExternalApiEnabled,
      provider: "none"
    },
    themeSummary: {
      mockEnabled: config.themeSummaryMockEnabled,
      externalNewsApiEnabled: config.themeSummaryExternalNewsApiEnabled,
      scoreEnabled: config.themeSummaryScoreEnabled
    },
    serverHost: config.serverHost,
    serverPort: config.serverPort,
    externalApiTimeoutMs: config.externalApiTimeoutMs,
    envFileLoaded: config.envFileLoaded
  };
}

function toBoolean(value) {
  return String(value).trim().toLowerCase() === "true";
}

function toNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}
