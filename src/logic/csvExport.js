import { flattenAnalysisResult } from "./bulkAnalysis.js";

export const EXPORT_COLUMNS = [
  "code",
  "name",
  "dataSource",
  "dataSourceLabel",
  "tradableDataLabel",
  "signal",
  "signalLabel",
  "totalScore",
  "buyScore",
  "overheatRisk",
  "confidence",
  "price",
  "change",
  "changePercent",
  "volume",
  "volumeRatio",
  "rsi",
  "ma25",
  "ma75",
  "deviation25",
  "deviation75",
  "high52w",
  "distanceFrom52wHigh",
  "highYtd",
  "distanceFromYtdHigh",
  "isBeforeEarnings",
  "earningsTrend",
  "hasUpwardRevision",
  "hasDownwardRevision",
  "hasDividendIncrease",
  "hasBuyback",
  "policyThemes",
  "policyRelationType",
  "mainBullReasons",
  "mainBearReasons",
  "mainWarnings",
  "actionPlan",
  "lastUpdated",
  "disclaimer"
];

export function exportAnalysisResultsToCsv(results) {
  const rows = results.map((result) => flattenAnalysisResult(result));
  return [
    EXPORT_COLUMNS.join(","),
    ...rows.map((row) => EXPORT_COLUMNS.map((column) => escapeCsv(row[column])).join(",")),
    [
      "DISCLAIMER",
      escapeCsv("このツールは投資助言ではありません。CSV取込データはユーザー提供データであり、正確性・最新性は保証されません。実売買判断には必ず公式情報を確認してください。")
    ].join(",")
  ].join("\n");
}

export function buildExportFilename(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  const stamp = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
  return `stock_analysis_results_${stamp}.csv`;
}

export function downloadCsv(filename, csvText) {
  const blob = new Blob([`\uFEFF${csvText}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function escapeCsv(value) {
  const text = value === undefined || value === null ? "" : String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}
