export const STOCK_MASTER_CSV_KEY = "stockAnalyzer.stockMasterCsv";
export const STOCK_MASTER_CSV_META_KEY = "stockAnalyzer.stockMasterCsvMeta";
export const STOCK_MASTER_CSV_MAX = 5000;
export const STOCK_MASTER_TEMPLATE_FILENAME = "stock-master-template.csv";

const FORBIDDEN_KEYS = new Set([
  "apiKey",
  "JQUANTS_API_KEY",
  "headers",
  "rawRows",
  "debugInfo",
  "financialSummary",
  "structuredSummary",
  "aiSummary",
  "themeSummary",
  "scoreResult",
  "indicators"
]);

const HEADER_ALIASES = {
  code: ["code", "Code", "コード", "銘柄コード", "localCode", "LocalCode"],
  name: ["name", "Name", "銘柄名", "会社名", "CompanyName", "companyName"],
  market: ["market", "Market", "市場", "市場区分"],
  sector: ["sector", "Sector", "業種", "業種名", "industry", "Industry"]
};

const TEMPLATE_ROWS = [
  ["code", "name", "market", "sector"],
  ["7203", "トヨタ自動車", "プライム", "輸送用機器"],
  ["6758", "ソニーグループ", "プライム", "電気機器"],
  ["8035", "東京エレクトロン", "プライム", "電気機器"],
  ["9984", "ソフトバンクグループ", "プライム", "情報・通信業"],
  ["9434", "ソフトバンク", "プライム", "情報・通信業"],
  ["7011", "三菱重工業", "プライム", "機械"],
  ["5803", "フジクラ", "プライム", "非鉄金属"],
  ["6861", "キーエンス", "プライム", "電気機器"],
  ["6098", "リクルートホールディングス", "プライム", "サービス業"]
];

export async function readCsvFileAsText(file, options = {}) {
  if (!file?.arrayBuffer) {
    return {
      ok: false,
      text: "",
      selectedEncoding: normalizeEncodingOption(options.encoding || options.selectedEncoding || "auto"),
      detectedEncoding: "unknown",
      decodeWarning: "CSVファイルを読み込めませんでした。",
      mojibakeSuspected: false
    };
  }
  const arrayBuffer = await file.arrayBuffer();
  return decodeCsvArrayBuffer(arrayBuffer, options.encoding || options.selectedEncoding || "auto");
}

export function decodeCsvArrayBuffer(arrayBuffer, encoding = "auto") {
  const selectedEncoding = normalizeEncodingOption(encoding);
  if (selectedEncoding === "auto") {
    return decodeCsvArrayBufferAuto(arrayBuffer);
  }

  const decoded = decodeWithEncoding(arrayBuffer, selectedEncoding);
  if (!decoded.ok) {
    return {
      ok: false,
      text: "",
      selectedEncoding,
      detectedEncoding: selectedEncoding,
      decodeWarning: decoded.error,
      mojibakeSuspected: false
    };
  }
  const mojibake = detectMojibake(decoded.text);
  return {
    ok: true,
    text: stripBom(decoded.text),
    selectedEncoding,
    detectedEncoding: selectedEncoding,
    decoderLabel: decoded.decoderLabel,
    decodeWarning: mojibake.mojibakeSuspected ? "文字化けの可能性があります。文字コードをShift_JIS/CP932またはUTF-8に切り替えて再読み込みしてください。" : "",
    mojibakeSuspected: mojibake.mojibakeSuspected,
    mojibake
  };
}

export function detectMojibake(text) {
  const value = String(text || "");
  const replacementCount = (value.match(/\uFFFD/g) || []).length;
  const nullCount = (value.match(/\u0000/g) || []).length;
  const suspiciousFragments = ["繝", "繧", "縺", "譁", "莨", "驫", "蜷", "螂", "蟆", "蛹", "鬆"];
  const suspiciousCount = suspiciousFragments.reduce((count, fragment) => (
    count + (value.match(new RegExp(fragment, "g")) || []).length
  ), 0);
  const score = replacementCount * 4 + nullCount * 4 + suspiciousCount;
  return {
    mojibakeSuspected: score >= 2,
    replacementCount,
    nullCount,
    suspiciousCount,
    score
  };
}

export function guessCsvEncoding(text) {
  return detectMojibake(text).mojibakeSuspected ? "shift-jis" : "utf-8";
}

export function parseStockMasterCsvText(csvText, options = {}) {
  const errors = [];
  const encodingMeta = buildEncodingMeta(csvText, options);
  if (encodingMeta.mojibakeSuspected) {
    errors.push("文字化けしている可能性があります。必要に応じてCSVをUTF-8で保存し直してください。");
  }

  const rows = parseCsvRows(String(csvText || ""));
  if (!rows.length) {
    return buildImportResult([], ["CSVにヘッダー行がありません。"], 0, 0, encodingMeta);
  }

  const headers = rows[0].map((header) => String(header || "").trim());
  const headerMap = buildHeaderMap(headers);
  if (headerMap.errors.length) {
    return buildImportResult([], headerMap.errors, Math.max(rows.length - 1, 0), 0, encodingMeta);
  }

  const normalizedRows = [];
  rows.slice(1).forEach((cells, index) => {
    const lineNumber = index + 2;
    if (cells.every((cell) => !String(cell || "").trim())) return;
    const row = {};
    Object.entries(headerMap.map).forEach(([field, headerIndex]) => {
      row[field] = cells[headerIndex] ?? "";
    });
    const normalized = normalizeStockMasterRow(row, lineNumber);
    if (normalized.error) {
      errors.push(normalized.error);
      return;
    }
    normalizedRows.push(normalized.row);
  });

  const merged = mergeStockMasterRows(normalizedRows);
  const duplicates = normalizedRows.length - merged.length;
  return {
    ok: merged.length > 0,
    rows: merged.slice(0, STOCK_MASTER_CSV_MAX),
    errors,
    stats: {
      readCount: Math.max(rows.length - 1, 0),
      validCount: normalizedRows.length,
      excludedCount: Math.max(rows.length - 1, 0) - normalizedRows.length,
      duplicateCount: duplicates,
      storedCount: Math.min(merged.length, STOCK_MASTER_CSV_MAX),
      truncatedCount: Math.max(merged.length - STOCK_MASTER_CSV_MAX, 0)
    },
    encoding: encodingMeta,
    selectedEncoding: encodingMeta.selectedEncoding,
    detectedEncoding: encodingMeta.detectedEncoding,
    decodeWarning: encodingMeta.decodeWarning,
    mojibakeSuspected: encodingMeta.mojibakeSuspected
  };
}

export function normalizeStockMasterRow(row, lineNumber = 1) {
  const code = normalizeStockMasterCode(row?.code);
  if (!code) return { row: null, error: `${lineNumber}行目: code が空、または4桁コードとして扱えません。` };
  const name = normalizeText(row?.name || code);
  const sanitized = sanitizeStockMasterRow({
    code,
    name,
    market: normalizeText(row?.market || ""),
    sector: normalizeText(row?.sector || ""),
    source: "CSV_MASTER"
  });
  return { row: sanitized, error: "" };
}

export function normalizeStockMasterCode(code) {
  const text = String(code || "").trim().normalize("NFKC").toUpperCase();
  const match = text.match(/^(\d{4})(?:\.T)?$/);
  return match ? match[1] : null;
}

export function getStoredStockMaster(storage = getStorage()) {
  if (!storage) return [];
  try {
    const raw = storage.getItem(STOCK_MASTER_CSV_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return mergeStockMasterRows(parsed.map((row) => sanitizeStockMasterRow(row)).filter(Boolean))
      .slice(0, STOCK_MASTER_CSV_MAX);
  } catch {
    return [];
  }
}

export function getStoredStockMasterMeta(storage = getStorage()) {
  if (!storage) return null;
  try {
    const raw = storage.getItem(STOCK_MASTER_CSV_META_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return sanitizeStockMasterCsvMeta(parsed);
  } catch {
    return null;
  }
}

export function saveStoredStockMaster(rows, storage = getStorage(), meta = {}) {
  if (!storage) return { ok: false, error: "localStorage is unavailable.", rows: [] };
  try {
    const importedAt = new Date().toISOString();
    const sanitized = mergeStockMasterRows(Array.isArray(rows) ? rows : [])
      .slice(0, STOCK_MASTER_CSV_MAX)
      .map((row) => sanitizeStockMasterRow({ ...row, importedAt }))
      .filter(Boolean);
    storage.setItem(STOCK_MASTER_CSV_KEY, JSON.stringify(sanitized));
    const safeMeta = sanitizeStockMasterCsvMeta({
      ...meta,
      importedAt,
      count: sanitized.length
    });
    storage.setItem(STOCK_MASTER_CSV_META_KEY, JSON.stringify(safeMeta));
    return { ok: true, rows: sanitized, count: sanitized.length, meta: safeMeta };
  } catch (error) {
    return {
      ok: false,
      error: "銘柄マスターCSVが大きすぎるため保存できませんでした。件数を減らしてください。",
      detail: error.message,
      rows: []
    };
  }
}

export function clearStoredStockMaster(storage = getStorage()) {
  if (!storage) return { ok: false, error: "localStorage is unavailable." };
  try {
    storage.removeItem(STOCK_MASTER_CSV_KEY);
    storage.removeItem(STOCK_MASTER_CSV_META_KEY);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function buildStockMasterCsvTemplate() {
  return `\uFEFF${TEMPLATE_ROWS.map((row) => row.map(escapeCsvCell).join(",")).join("\n")}\n`;
}

export function downloadStockMasterCsvTemplate(filename = STOCK_MASTER_TEMPLATE_FILENAME) {
  if (typeof document === "undefined" || typeof Blob === "undefined" || !globalThis.URL?.createObjectURL) {
    return { ok: false, error: "CSVテンプレートのダウンロードはブラウザ環境で実行してください。" };
  }
  const blob = new Blob([buildStockMasterCsvTemplate()], { type: "text/csv;charset=utf-8" });
  const url = globalThis.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  globalThis.URL.revokeObjectURL(url);
  return { ok: true, filename };
}

export function mergeStockMasterRows(rows) {
  const byCode = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const safe = sanitizeStockMasterRow(row);
    if (!safe) return;
    byCode.set(safe.code, {
      ...byCode.get(safe.code),
      ...safe
    });
  });
  return [...byCode.values()].sort((a, b) => a.code.localeCompare(b.code));
}

export function sanitizeStockMasterRow(row) {
  if (!row || typeof row !== "object") return null;
  const code = normalizeStockMasterCode(row.code || row.LocalCode || row.Code);
  if (!code) return null;
  const safe = {};
  Object.keys(row).forEach((key) => {
    if (!FORBIDDEN_KEYS.has(key)) safe[key] = row[key];
  });
  return {
    code,
    name: normalizeText(safe.name || safe.Name || safe.companyName || safe.CompanyName || code),
    market: normalizeText(safe.market || safe.Market || ""),
    sector: normalizeText(safe.sector || safe.Sector || safe.industry || safe.Industry || ""),
    source: normalizeStockMasterSource(safe.source || safe.Source || "CSV_MASTER"),
    importedAt: normalizeText(safe.importedAt || "")
  };
}

function normalizeStockMasterSource(source) {
  const value = normalizeText(source || "CSV_MASTER").toUpperCase();
  if (value === "JQUANTS_MOCK") return "JQUANTS_MOCK";
  if (value === "CSV_IMPORT") return "CSV_IMPORT";
  return "CSV_MASTER";
}

function buildHeaderMap(headers) {
  const normalizedHeaders = headers.map((header) => normalizeHeader(header));
  const map = {};
  const errors = [];
  ["code", "name"].forEach((field) => {
    const index = findHeaderIndex(normalizedHeaders, HEADER_ALIASES[field]);
    if (index < 0) errors.push(`ヘッダーに ${field} がありません。`);
    else map[field] = index;
  });
  ["market", "sector"].forEach((field) => {
    const index = findHeaderIndex(normalizedHeaders, HEADER_ALIASES[field]);
    map[field] = index >= 0 ? index : -1;
  });
  return { map, errors };
}

function findHeaderIndex(normalizedHeaders, aliases) {
  const normalizedAliases = aliases.map((alias) => normalizeHeader(alias));
  return normalizedHeaders.findIndex((header) => normalizedAliases.includes(header));
}

function normalizeHeader(header) {
  return String(header || "").trim().normalize("NFKC").replace(/\s+/g, "").toLowerCase();
}

function buildImportResult(rows, errors, readCount, validCount, encodingMeta = buildEncodingMeta("")) {
  return {
    ok: rows.length > 0,
    rows,
    errors,
    stats: {
      readCount,
      validCount,
      excludedCount: Math.max(readCount - validCount, 0),
      duplicateCount: 0,
      storedCount: rows.length,
      truncatedCount: 0
    },
    encoding: encodingMeta,
    selectedEncoding: encodingMeta.selectedEncoding,
    detectedEncoding: encodingMeta.detectedEncoding,
    decodeWarning: encodingMeta.decodeWarning,
    mojibakeSuspected: encodingMeta.mojibakeSuspected
  };
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
      if (row.some((value) => String(value).trim())) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => String(value).trim())) rows.push(row);
  return rows;
}

function normalizeText(value) {
  return String(value || "").trim();
}

function decodeCsvArrayBufferAuto(arrayBuffer) {
  const utf8 = decodeCsvArrayBuffer(arrayBuffer, "utf-8");
  const shift = decodeWithAnyShiftJisLabel(arrayBuffer);
  if (shift.ok) {
    const utf8Score = detectMojibake(utf8.text).score;
    const shiftScore = detectMojibake(shift.text).score;
    if (!utf8.ok || utf8Score > shiftScore + 1) {
      const mojibake = detectMojibake(shift.text);
      return {
        ok: true,
        text: stripBom(shift.text),
        selectedEncoding: "auto",
        detectedEncoding: shift.detectedEncoding,
        decoderLabel: shift.decoderLabel,
        decodeWarning: mojibake.mojibakeSuspected ? "Shift_JIS/CP932として読み込みましたが、文字化けの可能性があります。" : "",
        mojibakeSuspected: mojibake.mojibakeSuspected,
        mojibake
      };
    }
  }
  return {
    ...utf8,
    selectedEncoding: "auto",
    detectedEncoding: utf8.mojibakeSuspected && !shift.ok ? "utf-8" : "utf-8",
    decodeWarning: utf8.mojibakeSuspected
      ? "UTF-8として読み込みましたが、文字化けの可能性があります。Shift_JIS/CP932を選んで再読み込みしてください。"
      : ""
  };
}

function decodeWithAnyShiftJisLabel(arrayBuffer) {
  const labels = ["shift-jis", "shift_jis", "ms932"];
  for (const label of labels) {
    try {
      const decoder = new TextDecoder(label, { fatal: false });
      return {
        ok: true,
        text: decoder.decode(arrayBuffer),
        decoderLabel: label,
        detectedEncoding: "shift-jis"
      };
    } catch {
      // Try the next browser/Node-supported label.
    }
  }
  return {
    ok: false,
    error: "このブラウザではShift_JIS/CP932のデコードに対応していません。UTF-8のCSVテンプレートを利用してください。"
  };
}

function decodeWithEncoding(arrayBuffer, encoding) {
  const normalized = normalizeEncodingOption(encoding);
  if (normalized === "shift-jis") return decodeWithAnyShiftJisLabel(arrayBuffer);
  try {
    const decoder = new TextDecoder(normalized, { fatal: false });
    return {
      ok: true,
      text: decoder.decode(arrayBuffer),
      decoderLabel: normalized
    };
  } catch (error) {
    return {
      ok: false,
      error: `${encoding} のデコードに対応していません。${error.message || ""}`.trim()
    };
  }
}

function normalizeEncodingOption(encoding) {
  const value = String(encoding || "auto").trim().toLowerCase();
  if (["text", "unknown"].includes(value)) return value;
  if (["sjis", "shift_jis", "shift-jis", "shiftjis", "cp932", "ms932"].includes(value)) return "shift-jis";
  if (["utf8", "utf-8"].includes(value)) return "utf-8";
  return "auto";
}

function stripBom(text) {
  return String(text || "").replace(/^\uFEFF/, "");
}

function buildEncodingMeta(csvText, options = {}) {
  const detection = detectMojibake(csvText);
  const selectedEncoding = normalizeEncodingOption(options.selectedEncoding || options.encoding || "text");
  const detectedEncoding = normalizeEncodingOption(options.detectedEncoding || options.decoderLabel || selectedEncoding);
  return {
    selectedEncoding,
    detectedEncoding,
    decodeWarning: normalizeText(options.decodeWarning || (detection.mojibakeSuspected ? "文字化けの可能性があります。" : "")),
    mojibakeSuspected: Boolean(options.mojibakeSuspected ?? detection.mojibakeSuspected)
  };
}

function sanitizeStockMasterCsvMeta(meta = {}) {
  return {
    importedAt: normalizeText(meta.importedAt || meta.savedAt || ""),
    count: Number.isFinite(Number(meta.count)) ? Number(meta.count) : 0,
    source: normalizeText(meta.source || "CSV_IMPORT"),
    selectedEncoding: normalizeEncodingOption(meta.selectedEncoding || meta.encoding || "auto"),
    detectedEncoding: normalizeEncodingOption(meta.detectedEncoding || "unknown"),
    decodeWarning: normalizeText(meta.decodeWarning || ""),
    mojibakeSuspected: Boolean(meta.mojibakeSuspected)
  };
}

function escapeCsvCell(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function getStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}
