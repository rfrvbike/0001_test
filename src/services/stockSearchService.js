import { LOCAL_STOCK_MASTER } from "../../server/data/localStockMaster.js";

const SOURCE_PRIORITY = {
  FAVORITE: 1,
  RECENT: 2,
  WATCHLIST: 3,
  LOCAL_MASTER: 4,
  CSV_MASTER: 5,
  CSV: 6,
  MOCK: 7,
  UNKNOWN: 9
};

const FORBIDDEN_KEYS = [
  "apiKey",
  "JQUANTS_API_KEY",
  "headers",
  "rawRows",
  "debugInfo",
  "financialSummary",
  "structuredSummary",
  "aiSummary",
  "themeSummary"
];

export function normalizeSearchText(text) {
  const normalized = String(text || "")
    .trim()
    .normalize("NFKC")
    .replace(/\s+/g, "")
    .toLowerCase();
  return toHiragana(normalized);
}

export function isStockCodeQuery(query) {
  return /^\d{4}(?:\.t)?$/i.test(String(query || "").trim().normalize("NFKC"));
}

export function buildSearchIndex({
  localMaster = LOCAL_STOCK_MASTER,
  favorites = [],
  recentStocks = [],
  watchlist = [],
  stockMasterRows = [],
  csvRows = []
} = {}) {
  const candidates = [];

  Object.values(localMaster || {}).forEach((stock) => {
    candidates.push(toCandidate(stock, "LOCAL_MASTER"));
  });

  favorites.forEach((stock) => {
    candidates.push(toCandidate(stock, "FAVORITE"));
  });

  recentStocks.forEach((stock) => {
    candidates.push(toCandidate(stock, "RECENT"));
  });

  watchlist.forEach((stock) => {
    candidates.push(toCandidate(typeof stock === "string" ? { code: stock } : stock, "WATCHLIST"));
  });

  stockMasterRows.forEach((stock) => {
    candidates.push(toCandidate(stock, "CSV_MASTER"));
  });

  csvRows.forEach((stock) => {
    candidates.push(toCandidate(stock, "CSV"));
  });

  return mergeDuplicateCandidates(candidates.filter(Boolean));
}

export function searchStockCandidates(query, sources = {}) {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) return [];

  return rankStockCandidates(buildSearchIndex(sources), query)
    .filter((candidate) => candidate.matchScore > 0)
    .slice(0, 10)
    .map(sanitizeSearchCandidate);
}

export function mergeDuplicateCandidates(candidates) {
  const byCode = new Map();
  candidates.forEach((candidate) => {
    const safe = sanitizeSearchCandidate(candidate);
    if (!safe?.code) return;
    const existing = byCode.get(safe.code);
    if (!existing) {
      byCode.set(safe.code, safe);
      return;
    }
    const sources = mergeSources(existing.sources, safe.sources);
    byCode.set(safe.code, {
      ...existing,
      name: preferText(existing.name, safe.name),
      market: preferText(existing.market, safe.market),
      sector: preferText(existing.sector, safe.sector),
      source: sources.join(" / "),
      sources,
      isFavorite: sources.includes("FAVORITE"),
      isRecent: sources.includes("RECENT"),
      isWatchlist: sources.includes("WATCHLIST"),
      isCsvMaster: sources.includes("CSV_MASTER"),
      isCsv: sources.includes("CSV")
    });
  });
  return [...byCode.values()];
}

export function rankStockCandidates(candidates, query) {
  const normalizedQuery = normalizeSearchText(query);
  const codeQuery = normalizeStockCode(query);
  return candidates
    .map((candidate) => {
      const name = normalizeSearchText(candidate.name);
      const aliases = buildAliasTexts(candidate);
      const sourceRank = Math.min(...candidate.sources.map((source) => SOURCE_PRIORITY[source] || 9));
      let matchScore = 0;
      if (codeQuery && candidate.code === codeQuery) matchScore = 100;
      else if (name === normalizedQuery) matchScore = 90;
      else if (name.startsWith(normalizedQuery)) matchScore = 80;
      else if (name.includes(normalizedQuery)) matchScore = 70;
      else if (aliases.some((alias) => alias === normalizedQuery)) matchScore = 65;
      else if (aliases.some((alias) => alias.startsWith(normalizedQuery))) matchScore = 60;
      else if (aliases.some((alias) => alias.includes(normalizedQuery))) matchScore = 50;

      return { ...candidate, matchScore, sourceRank };
    })
    .sort((a, b) => b.matchScore - a.matchScore || a.sourceRank - b.sourceRank || a.code.localeCompare(b.code));
}

export function sanitizeSearchCandidate(candidate) {
  if (!candidate || typeof candidate !== "object") return null;
  const code = normalizeStockCode(candidate.code);
  if (!code) return null;
  const sources = mergeSources(
    [],
    Array.isArray(candidate.sources)
      ? candidate.sources.filter(Boolean)
      : [candidate.source || "UNKNOWN"].filter(Boolean)
  );
  const safe = {
    code,
    name: String(candidate.name || code).trim(),
    market: String(candidate.market || "").trim(),
    sector: String(candidate.sector || "").trim(),
    source: sources.join(" / "),
    sources,
    isFavorite: sources.includes("FAVORITE"),
    isRecent: sources.includes("RECENT"),
    isWatchlist: sources.includes("WATCHLIST"),
    isCsvMaster: sources.includes("CSV_MASTER"),
    isCsv: sources.includes("CSV")
  };
  FORBIDDEN_KEYS.forEach((key) => delete safe[key]);
  return safe;
}

function toCandidate(stock, source) {
  const code = normalizeStockCode(stock?.code || stock?.LocalCode || stock?.Code);
  if (!code) return null;
  return sanitizeSearchCandidate({
    code,
    name: stock?.name || stock?.Name || stock?.companyName || code,
    market: stock?.market || "",
    sector: stock?.sector || "",
    sources: [source]
  });
}

function normalizeStockCode(code) {
  const normalized = String(code || "").trim().normalize("NFKC").toUpperCase().replace(/\.T$/, "");
  return /^\d{4}$/.test(normalized) ? normalized : null;
}

function mergeSources(left = [], right = []) {
  return [...new Set([...left, ...right])]
    .filter(Boolean)
    .sort((a, b) => (SOURCE_PRIORITY[a] || 9) - (SOURCE_PRIORITY[b] || 9));
}

function preferText(left, right) {
  const leftText = String(left || "").trim();
  const rightText = String(right || "").trim();
  if (!leftText || /^\d{4}$/.test(leftText)) return rightText || leftText;
  return leftText;
}

function buildAliasTexts(candidate) {
  const name = normalizeSearchText(candidate.name);
  const aliases = new Set([name]);
  ["グループ", "ホールディングス", "株式会社", "HD"].forEach((word) => {
    aliases.add(name.replace(normalizeSearchText(word), ""));
  });
  return [...aliases].filter(Boolean);
}

function toHiragana(text) {
  return String(text || "").replace(/[\u30a1-\u30f6]/g, (char) => {
    return String.fromCharCode(char.charCodeAt(0) - 0x60);
  });
}
