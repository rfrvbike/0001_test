import {
  checkJQuantsConnection,
  fetchJQuantsFinancialSummary,
  fetchJQuantsMappedStockData,
  fetchJQuantsRawDailyBars,
  getJQuantsStatus,
  getJQuantsStockData,
  getJQuantsStockList
} from "../services/jquantsClient.js";
import {
  clearJQuantsCache,
  getJQuantsCacheStats
} from "../services/jquantsCache.js";
import {
  getStockMasterInfo,
  getStockMasterStatus
} from "../services/stockMasterService.js";

export async function routeStocks(req, url) {
  if (url.pathname === "/api/jquants/status") {
    return { status: 200, body: getJQuantsStatus() };
  }

  if (url.pathname === "/api/jquants/cache/status") {
    return { status: 200, body: getJQuantsCacheStats() };
  }

  if (url.pathname === "/api/jquants/cache/clear") {
    return { status: 200, body: clearJQuantsCache() };
  }

  if (url.pathname === "/api/stocks/master/status") {
    return { status: 200, body: getStockMasterStatus() };
  }

  const masterMatch = url.pathname.match(/^\/api\/stocks\/master\/([^/]+)$/);
  if (masterMatch) {
    const info = getStockMasterInfo(decodeURIComponent(masterMatch[1]));
    return {
      status: 200,
      body: {
        ok: true,
        code: info.code,
        found: Boolean(info.found),
        master: info.master || null,
        message: info.found ? "Stock master info was found." : info.message || "Stock master info was not found."
      }
    };
  }

  if (url.pathname === "/api/jquants/connection-check") {
    const result = await checkJQuantsConnection();
    return { status: result.ok ? 200 : result.status || 400, body: result };
  }

  const finsSummaryMatch = url.pathname.match(/^\/api\/jquants\/fins\/summary\/([^/]+)$/);
  if (finsSummaryMatch) {
    const result = await fetchJQuantsFinancialSummary({
      code: decodeURIComponent(finsSummaryMatch[1])
    }, undefined, {
      forceRefresh: url.searchParams.get("forceRefresh") === "true"
    });
    return { status: result.ok ? 200 : result.statusCode && result.statusCode < 500 ? 400 : 500, body: result };
  }

  const rawMatch = url.pathname.match(/^\/api\/jquants\/raw\/([^/]+)$/);
  if (rawMatch) {
    const result = await fetchJQuantsRawDailyBars({
      code: decodeURIComponent(rawMatch[1]),
      from: url.searchParams.get("from") || undefined,
      to: url.searchParams.get("to") || undefined
    });
    return { status: result.ok ? 200 : result.statusCode && result.statusCode < 500 ? 400 : 500, body: result };
  }

  const mappedMatch = url.pathname.match(/^\/api\/jquants\/mapped\/([^/]+)$/);
  if (mappedMatch) {
    const result = await fetchJQuantsMappedStockData({
      code: decodeURIComponent(mappedMatch[1]),
      from: url.searchParams.get("from") || undefined,
      to: url.searchParams.get("to") || undefined
    }, undefined, {
      forceRefresh: url.searchParams.get("forceRefresh") === "true"
    });
    return { status: result.ok ? 200 : result.statusCode && result.statusCode < 500 ? 400 : 500, body: result };
  }

  if (url.pathname === "/api/stocks") {
    const codes = (url.searchParams.get("codes") || "")
      .split(",")
      .map((code) => code.trim())
      .filter(Boolean);
    const result = getJQuantsStockList(codes);
    return { status: result.ok ? 200 : result.status || 400, body: result };
  }

  const match = url.pathname.match(/^\/api\/stocks\/([^/]+)$/);
  if (match) {
    const result = await getJQuantsStockData(decodeURIComponent(match[1]), undefined, {
      forceRefresh: url.searchParams.get("forceRefresh") === "true"
    });
    if (!result.ok) return { status: result.status || 404, body: result };
    return {
      status: 200,
      body: {
        ok: true,
        didNetworkRequest: result.didNetworkRequest,
        implemented: result.implemented,
        mode: result.mode,
        apiVersion: result.apiVersion,
        fallbackUsed: result.fallbackUsed,
        fallbackReason: result.fallbackReason,
        jquantsErrorSummary: result.jquantsErrorSummary,
        calculationWarnings: result.calculationWarnings,
        debugInfo: result.debugInfo,
        realStockFrom: result.realStockFrom,
        realStockTo: result.realStockTo,
        cacheHit: result.cacheHit,
        cacheStored: result.cacheStored,
        cacheKey: result.cacheKey,
        cacheSavedAt: result.cacheSavedAt,
        cacheExpiresAt: result.cacheExpiresAt,
        cacheTtlMs: result.cacheTtlMs,
        forceRefresh: result.forceRefresh,
        retryAfterMs: result.retryAfterMs,
        rateLimitReason: result.rateLimitReason,
        ...result.data
      }
    };
  }

  return null;
}
