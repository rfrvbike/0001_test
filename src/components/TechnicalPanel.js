import { number, percent, signedPercent, signedYen, yen } from "./formatters.js";

export function TechnicalPanel(stock, indicators) {
  return `
    <section class="panel">
      <div class="panel-title">株価・テクニカル指標</div>
      <div class="metric-grid">
        ${metric("現在値", yen(indicators.currentPrice))}
        ${metric("前日比", `${signedYen(indicators.change)} / ${signedPercent(indicators.changePercent)}`, indicators.change >= 0 ? "positive" : "negative")}
        ${metric("出来高", `${number(indicators.volume)}株`)}
        ${metric("出来高倍率", `${indicators.volumeRatio.toFixed(2)}倍`, indicators.volumeRatio >= 1.5 ? "positive" : "")}
        ${metric("25日移動平均線", yen(indicators.ma25))}
        ${metric("75日移動平均線", yen(indicators.ma75))}
        ${metric("25日線乖離率", percent(indicators.ma25Deviation), indicators.ma25Deviation >= 10 ? "negative" : indicators.ma25Deviation > 0 ? "positive" : "")}
        ${metric("75日線乖離率", percent(indicators.ma75Deviation), indicators.ma75Deviation > 0 ? "positive" : "negative")}
        ${metric("RSI", indicators.rsi.toFixed(0), indicators.rsi >= 75 ? "negative" : indicators.rsi >= 50 ? "positive" : "")}
        ${metric("52週高値", yen(indicators.high52w))}
        ${metric("52週高値からの下落率", percent(indicators.high52wDrawdown), indicators.high52wDrawdown <= 3 ? "negative" : "")}
        ${metric("年初来高値からの下落率", percent(indicators.ytdHighDrawdown))}
      </div>
      ${stock.isMock ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線は実市場データではなくサンプルです。</div>` : ""}
      ${stock.dataSource === "CSV" ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線はCSV取込値です。正確性・最新性は保証されません。</div>` : ""}
      ${isJQuantsRealStock(stock) ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線はJ-Quants日足データ由来です。財務・決算・TDnetは未接続です。</div>` : ""}
    </section>
  `;
}

function metric(label, value, tone = "") {
  return `
    <div class="metric">
      <span>${label}</span>
      <strong class="${tone}">${value}</strong>
    </div>
  `;
}

function isJQuantsRealStock(stock) {
  return stock?.dataSource === "J_QUANTS_MAPPED" || stock?.dataSource === "J_QUANTS_REAL";
}
