import { number, percent, signedPercent, signedYen, yen } from "./formatters.js";

export function TechnicalPanel(stock, indicators = {}) {
  const volumeRatio = toFiniteNumber(indicators.volumeRatio);
  const rsi = toFiniteNumber(indicators.rsi);
  const change = toFiniteNumber(indicators.change);
  const ma25Deviation = toFiniteNumber(indicators.ma25Deviation);
  const ma75Deviation = toFiniteNumber(indicators.ma75Deviation);
  const high52wDrawdown = toFiniteNumber(indicators.high52wDrawdown);

  return `
    <section class="panel">
      <div class="panel-title">株価・テクニカル指標</div>
      <div class="metric-grid">
        ${metric("現在値", formatYen(indicators.currentPrice))}
        ${metric("前日比", `${formatSignedYen(indicators.change)} / ${formatSignedPercent(indicators.changePercent)}`, change >= 0 ? "positive" : "negative")}
        ${metric("出来高", `${formatNumber(indicators.volume)}株`)}
        ${metric("出来高倍率", formatFixedOrMissing(volumeRatio, 2, "倍"), volumeRatio >= 1.5 ? "positive" : "")}
        ${metric("25日移動平均", formatYen(indicators.ma25))}
        ${metric("75日移動平均", formatYen(indicators.ma75))}
        ${metric("25日線乖離率", formatPercent(indicators.ma25Deviation), ma25Deviation >= 10 ? "negative" : ma25Deviation > 0 ? "positive" : "")}
        ${metric("75日線乖離率", formatPercent(indicators.ma75Deviation), ma75Deviation > 0 ? "positive" : "negative")}
        ${metric("RSI", formatFixedOrMissing(rsi, 0), rsi >= 75 ? "negative" : rsi >= 50 ? "positive" : "")}
        ${metric("52週高値", formatYen(indicators.high52w))}
        ${metric("52週高値からの下落率", formatPercent(indicators.high52wDrawdown), high52wDrawdown <= 3 ? "negative" : "")}
        ${metric("年初来高値からの下落率", formatPercent(indicators.ytdHighDrawdown))}
      </div>
      ${stock.isMock ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線は実際の市場データではなくサンプルです。</div>` : ""}
      ${stock.dataSource === "CSV" ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線はCSV取込値です。正確性・最新性は保証されません。</div>` : ""}
      ${isJQuantsRealStock(stock) ? `<div class="summary-box">表示中の株価・出来高・RSI・移動平均線はJ-Quants日足データ由来です。財務・決算詳細・TDnetは未接続です。</div>` : ""}
    </section>
  `;
}

function toFiniteNumber(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function formatYen(value) {
  return toFiniteNumber(value) === null ? "未取得" : yen(value);
}

function formatNumber(value) {
  return toFiniteNumber(value) === null ? "未取得" : number(value);
}

function formatPercent(value) {
  return toFiniteNumber(value) === null ? "未取得" : percent(value);
}

function formatSignedYen(value) {
  return toFiniteNumber(value) === null ? "未取得" : signedYen(value);
}

function formatSignedPercent(value) {
  return toFiniteNumber(value) === null ? "未取得" : signedPercent(value);
}

function formatFixedOrMissing(value, digits, suffix = "") {
  if (value === null || value === undefined) return "未取得";
  return `${value.toFixed(digits)}${suffix}`;
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
