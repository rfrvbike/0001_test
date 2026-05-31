import { escapeHtml } from "./formatters.js";

export function ReasonPanel(summary) {
  return `
    <section class="panel wide">
      <div class="panel-title">買い理由・見送り理由</div>
      ${summary.dataNotice ? `<div class="mock-inline-warning">${escapeHtml(summary.dataNotice)}</div>` : ""}
      <div class="reason-grid">
        ${listBlock("買い材料", summary.buyReasons, "positive")}
        ${listBlock("弱気材料", summary.weakReasons, "negative")}
        ${listBlock("注意点", summary.cautions, "warning")}
      </div>
      <div class="policy-note">
        <strong>今買う場合の方針</strong>
        <p>${escapeHtml(summary.actionPolicy)}</p>
      </div>
      <div class="policy-note muted">
        <strong>見送る場合の理由</strong>
        <p>${escapeHtml(summary.skipReason)}</p>
      </div>
    </section>
  `;
}

function listBlock(title, items, tone) {
  return `
    <div class="reason-block ${tone}">
      <h3>${title}</h3>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}
