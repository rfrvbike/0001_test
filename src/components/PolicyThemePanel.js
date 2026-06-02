import { escapeHtml } from "./formatters.js";

export function PolicyThemePanel(stock = {}) {
  const themes = stock.policyThemes?.length ? stock.policyThemes : ["該当なし"];
  const isRelated = themes[0] !== "該当なし";
  const relationType = safeString(stock.policyRelationType, "NONE");
  const relationClass = safeClassToken(relationType);
  const description = safeString(stock.policyDescription, "国策テーマ判定は未取得です。");

  return `
    <section class="panel">
      <div class="panel-title">国策テーマ</div>
      <div class="policy-head">
        <span class="policy-related ${isRelated ? "on" : ""}">国策関連 ${isRelated ? "あり" : "なし"}</span>
        <span class="relation ${relationClass}">${escapeHtml(relationType)}</span>
      </div>
      <div class="theme-tags">
        ${themes.map((theme) => `<span>${escapeHtml(theme)}</span>`).join("")}
      </div>
      <div class="summary-box">${escapeHtml(description)}</div>
    </section>
  `;
}

function safeString(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function safeClassToken(value, fallback = "unknown") {
  const token = safeString(value, fallback)
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return token || fallback;
}
