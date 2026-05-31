import { escapeHtml } from "./formatters.js";

export function ThemeSummaryPanel(themeSummary) {
  if (!themeSummary) return "";
  if (themeSummary.status?.enabled === false) {
    return `
      <section class="panel wide">
        <div class="panel-title">ニュース・テーマ材料</div>
        <div class="policy-note muted">${escapeHtml(themeSummary.status.message || "ニュース・テーマ材料レイヤーは無効です。")}</div>
      </section>
    `;
  }

  const themes = Array.isArray(themeSummary.themes) ? themeSummary.themes : [];
  return `
    <section class="panel wide">
      <div class="panel-title">ニュース・テーマ材料</div>
      <div class="meta-grid">
        <div><span>データ種別</span><strong>${escapeHtml(themeSummary.source || "LOCAL_MOCK_THEME")}</strong></div>
        <div><span>外部ニュースAPI</span><strong>${themeSummary.externalNewsApiUsed ? "使用" : "未接続"}</strong></div>
        <div><span>外部AI</span><strong>${themeSummary.externalAiUsed ? "使用" : "未接続"}</strong></div>
        <div><span>スコア反映</span><strong>${themeSummary.themeScoreApplied ? "あり" : "なし"}</strong></div>
      </div>
      <div class="tag-row">
        ${(themes.length ? themes : ["テーマ未登録"]).map((theme) => `<span class="tag">${escapeHtml(theme)}</span>`).join("")}
      </div>
      <div class="summary-box">${escapeHtml(themeSummary.comment || "この銘柄に対応するローカルテーマ材料はまだ登録されていません。")}</div>
      <div class="policy-note">
        <strong>注意</strong>
        <ul>${safeArray(themeSummary.risks).map((risk) => `<li>${escapeHtml(risk)}</li>`).join("")}</ul>
      </div>
    </section>
  `;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}
