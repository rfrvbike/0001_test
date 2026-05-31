import { escapeHtml, formatLargeYen, formatPerShareYen } from "./formatters.js?v=financial-score-20260529";

export function FinancialSummaryPanel(stock) {
  const summary = stock.financialSummary;
  const status = stock.financialSummaryStatus;
  const signals = stock.financialSignals;
  if (!summary && status?.enabled === false) {
    return `
      <section class="panel">
        <div class="panel-title">財務サマリー</div>
        <div class="summary-box">現在は財務サマリー統合OFFです。</div>
      </section>
    `;
  }

  if (!summary) {
    return `
      <section class="panel">
        <div class="panel-title">財務サマリー</div>
        <div class="summary-box">財務サマリーは未取得です。</div>
      </section>
    `;
  }

  if (!summary.available) {
    return `
      <section class="panel">
        <div class="panel-title">財務サマリー</div>
        <div class="summary-box">
          取得できませんでした。株価・テクニカル情報のみ表示しています。<br />
          理由：${escapeHtml(summary.safeError || stock.financialSummaryError || summary.unavailableReason || "不明")}
        </div>
      </section>
    `;
  }

  return `
    <section class="panel">
      <div class="panel-title">財務サマリー</div>
      <div class="metric-grid compact">
        ${metric("データ種別", "J-Quants財務サマリー")}
        ${metric("最新開示日", `${summary.disclosedDate || "未取得"} ${summary.disclosedTime || ""}`.trim())}
        ${metric("書類種別", summary.typeOfDocument || "未取得")}
        ${metric("売上高", formatLargeYen(summary.netSales))}
        ${metric("営業利益", formatLargeYen(summary.operatingProfit))}
        ${metric("純利益", formatLargeYen(summary.profit))}
        ${metric("EPS", formatPerShareYen(summary.earningsPerShare))}
        ${metric("年間配当", formatPerShareYen(summary.dividendPerShareAnnual))}
        ${metric("自己資本比率", summary.equityRatio == null ? "未取得" : `${summary.equityRatio}%`)}
        ${metric("営業CF", formatLargeYen(summary.cashFlowsFromOperatingActivities))}
        ${metric("財務データ取得", summary.cacheHit ? "キャッシュ利用" : summary.didNetworkRequest ? "J-Quants実通信" : "バックエンド取得")}
      </div>
      ${financialEvaluationBox(signals, stock)}
      <div class="summary-box">
        財務サマリーは表示のみで、通常スコアにはまだ本格反映していません。実売買前には公式資料を確認してください。
      </div>
    </section>
  `;
}

function metric(label, value, tone = "") {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong class="${tone}">${escapeHtml(value)}</strong></div>`;
}

function financialEvaluationBox(signals, stock) {
  if (!signals) return "";
  const score = Number(signals.financialScore || 0);
  const scoreText = `${score > 0 ? "+" : ""}${score} / +5`;
  const reflected = stock.useFinancialScore === false ? "表示のみ（総合スコアへ未反映）" : "総合スコアへ弱く反映";
  const tone = score > 0 ? "positive" : score < 0 ? "negative" : "";
  return `
    <div class="summary-box">
      <strong>財務参考評価</strong><br />
      財務スコア：<span class="${tone}">${escapeHtml(scoreText)}</span><br />
      評価：${escapeHtml(signals.financialScoreLabel || "財務評価なし")}<br />
      反映：${escapeHtml(reflected)}<br />
      コメント：${escapeHtml(signals.financialComment || signals.warning || "財務情報は参考表示です。")}
    </div>
  `;
}
