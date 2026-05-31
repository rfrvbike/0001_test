import { escapeHtml } from "./formatters.js";

export function StructuredSummaryPanel(structuredSummary) {
  if (!structuredSummary) return "";
  const decision = structuredSummary.decision || {};
  const technical = structuredSummary.technical || {};
  const financial = structuredSummary.financial || {};
  const theme = structuredSummary.theme || {};
  const risks = structuredSummary.risks || {};
  const entryPlan = structuredSummary.entryPlan || {};

  return `
    <section class="panel wide structured-summary-panel">
      <div class="panel-title">判断サマリー</div>
      <div class="structured-headline">
        <span>総合判断：${escapeHtml(decision.label || "データ不足")}</span>
        <p>${escapeHtml(compactText(decision.reason || "判断サマリーを生成できませんでした。", 90))}</p>
      </div>
      <div class="structured-list-grid">
        ${summaryBlock("テクニカル", [
          technical.pricePosition,
          technical.rsiStatus,
          compactText(technical.comment, 70)
        ])}
        ${summaryBlock("財務", [
          financial.available ? financial.label : "財務未取得",
          compactText(financial.comment, 70)
        ])}
        ${summaryBlock("テーマ", [
          theme.available ? safeArray(theme.themes).slice(0, 4).join(" / ") : "テーマ未取得",
          compactText(theme.comment, 70)
        ])}
        ${summaryBlock("注意", [
          compactText(risks.comment, 70),
          ...safeArray(structuredSummary.cautions).slice(0, 2)
        ])}
      </div>
      <div class="policy-note compact-policy">
        <strong>今買う場合の条件</strong>
        <ul>${safeArray(entryPlan.ifBuying).slice(0, 3).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div class="policy-note muted compact-policy">
        外部AI APIには接続していません。このサマリーはAI要約に渡せる構造化データをルールベースで整理したものです。
      </div>
    </section>
  `;
}

function summaryBlock(title, items) {
  const list = safeArray(items).filter(Boolean);
  return `
    <div class="structured-mini-block">
      <h3>${escapeHtml(title)}</h3>
      <ul>${(list.length ? list : ["未取得"]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function compactText(value, maxLength = 80) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text || text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}
