import { number, signedPercent, signedYen, yen, escapeHtml } from "./formatters.js";

export function KeyMetricsGrid({ stock, indicators, scoreResult } = {}) {
  if (!stock || !indicators) return "";
  const financialScore = stock.financialSignals?.financialScore;
  const themeCount = Array.isArray(stock.themeSummary?.themes) ? stock.themeSummary.themes.length : 0;
  const items = [
    ["現在値", yen(indicators.currentPrice)],
    ["前日比", `${signedYen(indicators.change)} / ${signedPercent(indicators.changePercent)}`],
    ["出来高", `${number(indicators.volume)}株`],
    ["25日線", yen(indicators.ma25)],
    ["75日線", yen(indicators.ma75)],
    ["RSI", Number.isFinite(Number(indicators.rsi)) ? Number(indicators.rsi).toFixed(0) : "未取得"],
    ["財務スコア", financialScore == null ? "未取得" : `${financialScore > 0 ? "+" : ""}${financialScore}`],
    ["テーマ数", `${themeCount}件`]
  ];

  return `
    <section class="key-metrics-grid">
      ${items.map(([label, value]) => `
        <div class="key-metric">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")}
      ${scoreResult?.warnings?.length ? `<div class="key-metric warning"><span>主な注意</span><strong>${escapeHtml(scoreResult.warnings[0])}</strong></div>` : ""}
    </section>
  `;
}
