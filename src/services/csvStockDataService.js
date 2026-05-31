const REQUIRED_HEADERS = [
  "code",
  "name",
  "price",
  "previousClose",
  "volume",
  "ma25",
  "ma75",
  "rsi",
  "high52w",
  "highYtd"
];

const NUMERIC_FIELDS = [
  "price",
  "previousClose",
  "volume",
  "averageVolume20d",
  "ma25",
  "ma75",
  "rsi",
  "high52w",
  "highYtd"
];

const BOOLEAN_FIELDS = [
  "hasUpwardRevision",
  "hasDownwardRevision",
  "hasDividendIncrease",
  "hasBuyback",
  "isBeforeEarnings"
];

let csvStocks = [];

export function parseStockCsv(csvText) {
  const errors = [];
  if (/[\uFFFD\u0000]/.test(csvText)) {
    errors.push("文字コードの問題で文字化けしている可能性があります");
  }

  const rows = parseCsvRows(csvText);
  if (!rows.length) return { stocks: [], errors: ["CSVにヘッダー行がありません"] };

  const headers = rows[0].map((header) => header.trim());
  const missingHeaders = REQUIRED_HEADERS.filter((header) => !headers.includes(header));
  if (missingHeaders.length) {
    return {
      stocks: [],
      errors: missingHeaders.map((header) => `ヘッダーに ${header} がありません`)
    };
  }

  const stocks = [];
  rows.slice(1).forEach((cells, index) => {
    const lineNumber = index + 2;
    if (cells.every((cell) => !String(cell).trim())) {
      errors.push(`${lineNumber}行目：空行です`);
      return;
    }

    const row = Object.fromEntries(headers.map((header, i) => [header, cells[i] ?? ""]));
    const normalized = normalizeCsvStockData(row, lineNumber);
    if (normalized.errors.length) {
      errors.push(...normalized.errors);
      return;
    }

    const validationErrors = validateCsvStockData(normalized.stock, lineNumber);
    if (validationErrors.length) {
      errors.push(...validationErrors);
      return;
    }
    stocks.push(normalized.stock);
  });

  return { stocks, errors };
}

export function normalizeCsvStockData(row, lineNumber = 1) {
  const errors = [];
  const normalized = {};

  for (const [key, value] of Object.entries(row)) {
    const trimmed = String(value ?? "").trim();
    if (NUMERIC_FIELDS.includes(key)) {
      if (trimmed === "") {
        normalized[key] = "";
      } else if (!Number.isFinite(Number(trimmed))) {
        errors.push(`${lineNumber}行目：${key} が数値ではありません`);
      } else {
        normalized[key] = Number(trimmed);
      }
    } else if (BOOLEAN_FIELDS.includes(key)) {
      if (trimmed === "") {
        normalized[key] = false;
      } else if (/^(true|false)$/i.test(trimmed)) {
        normalized[key] = trimmed.toLowerCase() === "true";
      } else {
        errors.push(`${lineNumber}行目：${key} は true / false で入力してください`);
      }
    } else {
      normalized[key] = trimmed;
    }
  }

  const stock = applyCsvSourceMeta({
    code: normalized.code,
    name: normalized.name,
    market: normalized.market || "CSV取込",
    lastUpdated: normalized.lastUpdated || "CSV取込データ",
    price: normalized.price,
    previousClose: normalized.previousClose,
    change: Number.isFinite(normalized.price - normalized.previousClose) ? normalized.price - normalized.previousClose : 0,
    changePercent: normalized.previousClose > 0 ? ((normalized.price - normalized.previousClose) / normalized.previousClose) * 100 : 0,
    volume: normalized.volume,
    averageVolume20d: normalized.averageVolume20d || 0,
    ma25: normalized.ma25,
    ma75: normalized.ma75,
    rsi: normalized.rsi,
    high52w: normalized.high52w,
    highYtd: normalized.highYtd,
    latestEarningsDate: normalized.latestEarningsDate || "",
    nextEarningsDate: normalized.nextEarningsDate || "",
    earningsTrend: normalized.earningsTrend || "STABLE",
    hasUpwardRevision: Boolean(normalized.hasUpwardRevision),
    hasDownwardRevision: Boolean(normalized.hasDownwardRevision),
    hasDividendIncrease: Boolean(normalized.hasDividendIncrease),
    hasBuyback: Boolean(normalized.hasBuyback),
    importantDisclosures: splitList(normalized.importantDisclosures),
    policyThemes: splitList(normalized.policyThemes),
    policyRelationType: normalized.policyRelationType || "NONE",
    policyDescription: normalized.policyDescription || "CSV取込データです。正確性・最新性は保証されません。",
    candlePattern: normalized.candlePattern || "NORMAL",
    isBeforeEarnings: Boolean(normalized.isBeforeEarnings),
    recentHighBreakout: false,
    postEarningsGood: normalized.earningsTrend === "GROWING" && Boolean(normalized.hasUpwardRevision),
    exhaustionConcern: normalized.candlePattern === "VOLUME_SPIKE_UPPER_WICK"
  });

  return { stock, errors };
}

export function applyCsvSourceMeta(stock, extra = {}) {
  return {
    ...stock,
    ...extra,
    dataSource: "CSV",
    dataSourceLabel: "CSV取込",
    isMock: false,
    isTradableData: false,
    tradableDataLabel: "要確認"
  };
}

export function validateCsvStockData(stock, lineNumber = 1) {
  const errors = [];
  REQUIRED_HEADERS.forEach((field) => {
    const value = stock[field];
    if (value === "" || value === undefined || value === null) {
      errors.push(`${lineNumber}行目：${field} が空です`);
    }
  });
  return errors;
}

export function setCsvStockData(stocks) {
  csvStocks = Array.isArray(stocks) ? stocks.map((stock) => structuredClone(applyCsvSourceMeta(stock))) : [];
  return listCsvStocks();
}

export function getCsvStockData(query) {
  const normalized = String(query ?? "").trim().toLowerCase();
  const found = csvStocks.find((stock) => {
    return stock.code.toLowerCase() === normalized
      || stock.name.toLowerCase() === normalized
      || stock.name.toLowerCase().includes(normalized);
  });
  if (!found) throw new Error(`CSV取込データに ${query} は見つかりません`);
  return structuredClone(found);
}

export function listCsvStocks() {
  return csvStocks.map((stock) => structuredClone(stock));
}

function splitList(value) {
  if (!value) return [];
  return String(value)
    .split(/[・,、;|]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}
