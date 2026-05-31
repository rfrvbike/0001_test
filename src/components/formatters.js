export const yen = (value) => `${Number(value).toLocaleString("ja-JP")}円`;
export const number = (value) => Number(value).toLocaleString("ja-JP");
export const percent = (value, digits = 1) => `${Number(value).toFixed(digits)}%`;
export const signedPercent = (value) => `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
export const signedYen = (value) => `${value >= 0 ? "+" : ""}${Number(value).toLocaleString("ja-JP")}円`;

export function formatLargeYen(value) {
  const numberValue = Number(value);
  if (value === null || value === undefined || value === "" || !Number.isFinite(numberValue)) return "未取得";
  const abs = Math.abs(numberValue);
  if (abs >= 1_000_000_000_000) return `${(numberValue / 1_000_000_000_000).toFixed(1)}兆円`;
  if (abs >= 100_000_000) return `${(numberValue / 100_000_000).toFixed(1)}億円`;
  if (abs >= 10_000) return `${(numberValue / 10_000).toFixed(1)}万円`;
  return `${numberValue.toLocaleString("ja-JP")}円`;
}

export function formatPerShareYen(value) {
  const numberValue = Number(value);
  if (value === null || value === undefined || value === "" || !Number.isFinite(numberValue)) return "未取得";
  return `${numberValue.toLocaleString("ja-JP", { maximumFractionDigits: 2 })}円`;
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
