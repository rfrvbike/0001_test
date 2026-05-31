import { escapeHtml } from "./formatters.js";

export function PolicyThemePanel(stock) {
  const themes = stock.policyThemes?.length ? stock.policyThemes : ["該当なし"];
  const isRelated = themes[0] !== "該当なし";
  return `
    <section class="panel">
      <div class="panel-title">国策テーマ</div>
      <div class="policy-head">
        <span class="policy-related ${isRelated ? "on" : ""}">国策関連 ${isRelated ? "あり" : "なし"}</span>
        <span class="relation ${stock.policyRelationType.toLowerCase()}">${stock.policyRelationType}</span>
      </div>
      <div class="theme-tags">
        ${themes.map((theme) => `<span>${escapeHtml(theme)}</span>`).join("")}
      </div>
      <div class="summary-box">${escapeHtml(stock.policyDescription)}</div>
    </section>
  `;
}
