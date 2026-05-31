import { escapeHtml } from "./formatters.js";

export function AiSummaryMockPanel(aiSummary) {
  if (!aiSummary) return "";
  if (aiSummary.enabled === false || aiSummary.available === false) {
    return `
      <section class="panel wide">
        <div class="panel-title">AI要約プレビュー（モック）</div>
        <div class="policy-note muted">
          ${escapeHtml(aiSummary.message || "AI要約モックは無効です。")}
        </div>
      </section>
    `;
  }

  const shortComment = compactComment(aiSummary.shortComment || "要約を生成できませんでした。", 3);
  return `
    <section class="panel wide ai-summary-panel">
      <div class="panel-title">${escapeHtml(aiSummary.title || "AI要約プレビュー（モック）")}</div>
      <div class="mock-ai-badge">外部AI未接続（モック要約）。ルールベース生成です。</div>
      <div class="summary-box ai-summary-main">${escapeHtml(shortComment)}</div>
      <div class="ai-summary-grid">
        ${listBlock("要点", aiSummary.bullets, "bullets", 4)}
        ${listBlock("注意", aiSummary.warnings, "warnings", 3)}
      </div>
    </section>
  `;
}

function listBlock(title, items, type = "", limit = 4) {
  const list = Array.isArray(items) && items.length ? items.slice(0, limit) : ["未取得"];
  return `
    <div class="reason-block ai-summary-block ${escapeHtml(type)}">
      <h3>${escapeHtml(title)}</h3>
      <ul>${list.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function compactComment(value, maxSentences = 3) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  const sentences = text.match(/[^。！？!?]+[。！？!?]?/g) || [text];
  return sentences.slice(0, maxSentences).join("").trim();
}
