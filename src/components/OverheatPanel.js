export function OverheatPanel(stock, indicators, scoreResult) {
  const verdict = buildOverheatVerdict(indicators, scoreResult);
  return `
    <section class="panel">
      <div class="panel-title">高値掴み危険度</div>
      <div class="risk-checks">
        ${check("高値圏", indicators.nearHigh52w)}
        ${check("25日線から上がりすぎ", indicators.overMa25)}
        ${check("RSI過熱", indicators.overheatRsi)}
        ${check("出来高急増", indicators.volumeSpike)}
        ${check("決算前リスク", indicators.isBeforeEarnings)}
      </div>
      <div class="verdict ${scoreResult.overheatRisk.toLowerCase()}">${verdict}</div>
      ${stock.isMock ? `<div class="summary-box">この危険度判定もモックデータに基づくテスト表示です。</div>` : ""}
      ${stock.dataSource === "CSV" ? `<div class="summary-box">この危険度判定はCSV取込データに基づきます。公式情報で確認してください。</div>` : ""}
      ${isJQuantsRealStock(stock) ? `<div class="summary-box">この危険度判定はJ-Quants日足データのテクニカル指標に基づく参考表示です。財務・決算・TDnetは未接続です。</div>` : ""}
    </section>
  `;
}

function check(label, active) {
  return `<div class="risk-check ${active ? "active" : ""}"><span>${label}</span><strong>${active ? "はい" : "いいえ"}</strong></div>`;
}

function buildOverheatVerdict(indicators, scoreResult) {
  if (scoreResult.overheatRisk === "HIGH") return "今すぐ買いは危険";
  if (scoreResult.overheatRisk === "MEDIUM" && scoreResult.totalScore >= 50) return "分割なら可";
  if (scoreResult.overheatRisk === "MEDIUM") return "押し目待ち推奨";
  return "まだ過熱感は小さい";
}

function isJQuantsRealStock(stock) {
  return stock?.dataSource === "J_QUANTS_MAPPED" || stock?.dataSource === "J_QUANTS_REAL";
}
