import { escapeHtml } from "./formatters.js";

export function DisclosurePanel(stock, indicators) {
  const trendLabel = { GROWING: "増益", DECLINING: "減益", STABLE: "横ばい", TURNAROUND: "回復" }[stock.earningsTrend] || "横ばい";
  const summary = stock.importantDisclosures?.length
    ? stock.importantDisclosures.join(" / ")
    : "重要開示サンプルはありません";
  return `
    <section class="panel">
      <div class="panel-title">材料・開示</div>
      <div class="metric-grid compact">
        ${metric("直近決算日", stock.latestEarningsDate)}
        ${metric("次回決算予定日", stock.nextEarningsDate)}
        ${metric("決算前かどうか", indicators.isBeforeEarnings ? "はい" : "いいえ", indicators.isBeforeEarnings ? "negative" : "positive")}
        ${metric("業績方向", trendLabel, stock.earningsTrend === "GROWING" ? "positive" : stock.earningsTrend === "DECLINING" ? "negative" : "")}
        ${metric("上方修正", stock.hasUpwardRevision ? "あり" : "なし", stock.hasUpwardRevision ? "positive" : "")}
        ${metric("下方修正", stock.hasDownwardRevision ? "あり" : "なし", stock.hasDownwardRevision ? "negative" : "")}
        ${metric("増配", stock.hasDividendIncrease ? "あり" : "なし", stock.hasDividendIncrease ? "positive" : "")}
        ${metric("自社株買い", stock.hasBuyback ? "あり" : "なし", stock.hasBuyback ? "positive" : "")}
      </div>
      <div class="summary-box">${escapeHtml(summary)}</div>
    </section>
  `;
}

function metric(label, value, tone = "") {
  return `<div class="metric"><span>${label}</span><strong class="${tone}">${escapeHtml(value)}</strong></div>`;
}
