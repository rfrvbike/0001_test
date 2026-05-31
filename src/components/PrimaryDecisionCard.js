import { escapeHtml } from "./formatters.js";
import { SignalBadge } from "./SignalBadge.js";

export function PrimaryDecisionCard({ stock, scoreResult, structuredSummary } = {}) {
  if (!stock || !scoreResult) return "";
  const decision = structuredSummary?.decision || {};
  const comment = compactComment(decision.reason || scoreResult.summary || "ルールベースの判定結果です。");
  return `
    <section class="primary-decision-card">
      <div class="decision-main">
        <div class="decision-label">${escapeHtml(decision.label || scoreResult.signal || "判定中")}</div>
        <div class="decision-comment">${escapeHtml(comment)}</div>
        <div class="decision-badges">
          ${SignalBadge(scoreResult.signal)}
          <span class="data-badge danger">${escapeHtml(stock.tradableDataLabel || (stock.isTradableData ? "利用可" : "実売買利用不可"))}</span>
        </div>
      </div>
      <div class="decision-score-grid">
        <div><span>総合スコア</span><strong>${escapeHtml(scoreResult.totalScore)}</strong></div>
        <div><span>買いスコア</span><strong>${escapeHtml(scoreResult.buyScore)}</strong></div>
        <div><span>過熱リスク</span><strong>${escapeHtml(scoreResult.overheatRisk)}</strong></div>
        <div><span>信頼度</span><strong>${escapeHtml(scoreResult.confidence)}%</strong></div>
      </div>
    </section>
  `;
}

function compactComment(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= 110) return text;
  return `${text.slice(0, 109)}…`;
}
