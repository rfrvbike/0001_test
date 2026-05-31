import { getInternalEnv } from "../config/env.js";

const cacheStore = new Map();
const requestTimestamps = [];

export function buildJQuantsCacheKey({ code, from, to, endpoint, mode = "stocks" }) {
  return [
    mode,
    String(code || "").trim(),
    String(from || "").trim(),
    String(to || "").trim(),
    String(endpoint || "").trim()
  ].join(":");
}

export function getCachedJQuantsResult(key, config = getInternalEnv(), now = Date.now()) {
  if (!config.cacheEnabled) return null;
  const entry = cacheStore.get(key);
  if (!entry) return null;
  if (entry.expiresAtMs <= now) {
    cacheStore.delete(key);
    return null;
  }
  return {
    ...cloneJson(entry.value),
    cacheHit: true,
    didNetworkRequest: false,
    cacheKey: key,
    cacheSavedAt: entry.savedAt,
    cacheExpiresAt: entry.expiresAt,
    cacheTtlMs: entry.ttlMs
  };
}

export function setCachedJQuantsResult(key, value, meta = {}, config = getInternalEnv(), now = Date.now()) {
  if (!config.cacheEnabled) {
    return { ok: true, stored: false, reason: "cache_disabled" };
  }
  const ttlMs = Number(meta.ttlMs ?? config.cacheTtlMs);
  const savedAt = new Date(now).toISOString();
  const expiresAtMs = now + ttlMs;
  const expiresAt = new Date(expiresAtMs).toISOString();
  cacheStore.set(key, {
    value: sanitizeForCache(value),
    savedAt,
    expiresAt,
    expiresAtMs,
    ttlMs
  });
  return { ok: true, stored: true, savedAt, expiresAt, ttlMs };
}

export function clearJQuantsCache() {
  const count = cacheStore.size;
  cacheStore.clear();
  return { ok: true, cleared: true, clearedCount: count, message: "J-Quants cache cleared." };
}

export function getJQuantsCacheStats(config = getInternalEnv(), now = Date.now()) {
  pruneRequestTimestamps(config, now);
  const entries = [...cacheStore.entries()].map(([key, entry]) => ({
    key,
    savedAt: entry.savedAt,
    expiresAt: entry.expiresAt,
    isExpired: entry.expiresAtMs <= now,
    ttlMs: entry.ttlMs
  }));
  return {
    ok: true,
    cacheEnabled: Boolean(config.cacheEnabled),
    cacheTtlMs: config.cacheTtlMs,
    entryCount: entries.length,
    entries,
    rateLimit: {
      minRequestIntervalMs: config.minRequestIntervalMs,
      maxRequestsPerMinute: config.maxRequestsPerMinute,
      recentRequestCount: requestTimestamps.length
    }
  };
}

export function canMakeJQuantsRequest(config = getInternalEnv(), now = Date.now()) {
  pruneRequestTimestamps(config, now);
  const latest = requestTimestamps[requestTimestamps.length - 1];
  if (latest != null) {
    const elapsed = now - latest;
    if (elapsed < config.minRequestIntervalMs) {
      return {
        ok: false,
        reason: "min_request_interval",
        retryAfterMs: config.minRequestIntervalMs - elapsed
      };
    }
  }
  if (requestTimestamps.length >= config.maxRequestsPerMinute) {
    const oldest = requestTimestamps[0];
    return {
      ok: false,
      reason: "requests_per_minute",
      retryAfterMs: Math.max(0, 60000 - (now - oldest))
    };
  }
  return { ok: true };
}

export function sleep(ms) {
  const waitMs = Math.max(0, Number(ms) || 0);
  return new Promise((resolve) => setTimeout(resolve, waitMs));
}

export async function waitForJQuantsRateLimitIfNeeded(config = getInternalEnv(), options = {}) {
  const maxWaitMs = Number(options.maxWaitMs ?? 1500);
  const first = canMakeJQuantsRequest(config);
  if (first.ok) return { ok: true, waited: false, waitedMs: 0 };

  const retryAfterMs = Number(first.retryAfterMs);
  if (!Number.isFinite(retryAfterMs) || retryAfterMs > maxWaitMs) {
    return { ...first, waited: false, waitedMs: 0 };
  }

  const waitedMs = retryAfterMs + 50;
  await sleep(waitedMs);
  const second = canMakeJQuantsRequest(config);
  if (second.ok) return { ok: true, waited: true, waitedMs };
  return { ...second, waited: true, waitedMs };
}

export function recordJQuantsRequest(now = Date.now(), config = getInternalEnv()) {
  requestTimestamps.push(now);
  pruneRequestTimestamps(config, now);
  return { ok: true, recordedAt: new Date(now).toISOString(), recentRequestCount: requestTimestamps.length };
}

function pruneRequestTimestamps(config, now) {
  const windowStart = now - 60000;
  while (requestTimestamps.length && requestTimestamps[0] < windowStart) {
    requestTimestamps.shift();
  }
}

function sanitizeForCache(value) {
  const cloned = cloneJson(value);
  removeSecretFields(cloned);
  return cloned;
}

function removeSecretFields(value) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    value.forEach(removeSecretFields);
    return;
  }
  for (const key of Object.keys(value)) {
    if (isSecretKey(key)) {
      delete value[key];
    } else {
      removeSecretFields(value[key]);
    }
  }
}

function isSecretKey(key) {
  return /api[-_]?key|x-api-key|headers|authorization|token|password/i.test(key);
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}
