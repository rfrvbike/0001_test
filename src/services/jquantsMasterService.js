import {
  mergeStockMasterRows,
  normalizeStockMasterCode
} from "./stockMasterCsvService.js";

export const JQUANTS_MASTER_MOCK_SOURCE = "JQUANTS_MOCK";

const MOCK_MASTER_ROWS = [
  { code: "7203", name: "トヨタ自動車", market: "プライム", sector: "輸送用機器" },
  { code: "6758", name: "ソニーグループ", market: "プライム", sector: "電気機器" },
  { code: "8035", name: "東京エレクトロン", market: "プライム", sector: "電気機器" },
  { code: "9984", name: "ソフトバンクグループ", market: "プライム", sector: "情報・通信業" },
  { code: "9434", name: "ソフトバンク", market: "プライム", sector: "情報・通信業" },
  { code: "7011", name: "三菱重工業", market: "プライム", sector: "機械" },
  { code: "5803", name: "フジクラ", market: "プライム", sector: "非鉄金属" },
  { code: "6861", name: "キーエンス", market: "プライム", sector: "電気機器" },
  { code: "6098", name: "リクルートHD", market: "プライム", sector: "サービス業" }
];

export async function fetchMasterMock() {
  return {
    ok: true,
    source: JQUANTS_MASTER_MOCK_SOURCE,
    didNetworkRequest: false,
    rows: MOCK_MASTER_ROWS.map((row) => ({ ...row }))
  };
}

export function normalizeMasterData(rows = []) {
  const normalizedRows = (Array.isArray(rows) ? rows : [])
    .map((row) => {
      const code = normalizeStockMasterCode(row?.code || row?.Code || row?.LocalCode);
      if (!code) return null;
      return {
        code,
        name: normalizeText(row?.name || row?.Name || row?.CompanyName || row?.companyName || code),
        market: normalizeText(row?.market || row?.Market || ""),
        sector: normalizeText(row?.sector || row?.Sector || row?.Industry || row?.industry || ""),
        source: JQUANTS_MASTER_MOCK_SOURCE
      };
    })
    .filter(Boolean);
  return mergeStockMasterRows(normalizedRows).map((row) => ({
    ...row,
    source: JQUANTS_MASTER_MOCK_SOURCE
  }));
}

export function buildCsvFromMasterData(rows = []) {
  const normalizedRows = normalizeMasterData(rows);
  const header = ["code", "name", "market", "sector"];
  const body = normalizedRows.map((row) => (
    header.map((field) => escapeCsvCell(row[field])).join(",")
  ));
  return {
    source: JQUANTS_MASTER_MOCK_SOURCE,
    count: normalizedRows.length,
    csvText: `\uFEFF${[header.join(","), ...body].join("\n")}\n`,
    rows: normalizedRows
  };
}

export async function buildMasterMockDryRun() {
  const fetched = await fetchMasterMock();
  const rows = normalizeMasterData(fetched.rows);
  const csv = buildCsvFromMasterData(rows);
  return {
    ok: true,
    source: JQUANTS_MASTER_MOCK_SOURCE,
    didNetworkRequest: false,
    fetchedCount: fetched.rows.length,
    normalizedCount: rows.length,
    csvCount: csv.count,
    sampleRows: rows.slice(0, 5),
    csvText: csv.csvText
  };
}

function normalizeText(value) {
  return String(value || "").trim();
}

function escapeCsvCell(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}
