import { percent, signedPercent, yen, escapeHtml } from "./formatters.js";

export function BulkAnalysisTable(results) {
  if (!results.length) {
    return `<div class="summary-box">条件に一致する分析結果はありません。</div>`;
  }
  return `
    <div class="bulk-table-wrap">
      <table class="bulk-table">
        <thead>
          <tr>
            <th>code</th><th>name</th><th>データ</th><th>実売買</th><th>判定</th>
            <th>総合</th><th>買い</th><th>過熱</th><th>信頼度</th><th>現在値</th>
            <th>前日比</th><th>出来高倍率</th><th>RSI</th><th>25日乖離</th><th>75日乖離</th>
            <th>52週高値差</th><th>年初来高値差</th><th>決算前</th><th>上方</th><th>下方</th>
            <th>増配</th><th>自社株買い</th><th>国策テーマ</th><th>主な注意点</th><th>推奨方針</th>
          </tr>
        </thead>
        <tbody>
          ${results.map(row).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function row(result) {
  const { stock, indicators, scoreResult, summary } = result;
  const signalClass = signalTone(scoreResult.signal);
  const themes = stock.policyThemes?.join("・") || "-";
  return `
    <tr class="${signalClass}" data-bulk-code="${escapeHtml(stock.code)}">
      <td>${escapeHtml(stock.code)}</td>
      <td>${escapeHtml(stock.name)}</td>
      <td><span class="mini-source">${escapeHtml(stock.dataSourceLabel)}</span></td>
      <td>${escapeHtml(stock.tradableDataLabel || "実売買不可")}</td>
      <td><strong>${escapeHtml(scoreResult.signal)}</strong></td>
      <td>${scoreResult.totalScore}</td>
      <td>${scoreResult.buyScore}</td>
      <td><span class="risk-cell ${scoreResult.overheatRisk.toLowerCase()}">${scoreResult.overheatRisk}</span></td>
      <td>${scoreResult.confidence}%</td>
      <td>${yen(indicators.currentPrice)}</td>
      <td>${signedPercent(indicators.changePercent)}</td>
      <td>${indicators.volumeRatio.toFixed(2)}倍</td>
      <td>${indicators.rsi.toFixed(0)}</td>
      <td>${percent(indicators.ma25Deviation)}</td>
      <td>${percent(indicators.ma75Deviation)}</td>
      <td>${percent(indicators.high52wDrawdown)}</td>
      <td>${percent(indicators.ytdHighDrawdown)}</td>
      <td>${indicators.isBeforeEarnings ? "はい" : "いいえ"}</td>
      <td>${stock.hasUpwardRevision ? "あり" : "なし"}</td>
      <td>${stock.hasDownwardRevision ? "あり" : "なし"}</td>
      <td>${stock.hasDividendIncrease ? "あり" : "なし"}</td>
      <td>${stock.hasBuyback ? "あり" : "なし"}</td>
      <td>${escapeHtml(themes)}</td>
      <td>${escapeHtml(summary.cautions.slice(0, 2).join(" / "))}</td>
      <td>${escapeHtml(summary.actionPolicy)}</td>
    </tr>
  `;
}

function signalTone(signal) {
  if (signal === "買い候補" || signal === "分割買い候補") return "row-good";
  if (signal === "高値掴み注意" || signal === "損切り警戒") return "row-danger";
  if (signal === "押し目待ち") return "row-wait";
  return "row-neutral";
}
