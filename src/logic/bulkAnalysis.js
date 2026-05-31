import { calculateIndicators } from "./indicators.js";
import { calculateScore } from "./scoring.js";
import { buildReasonSummary } from "./summaryBuilder.js";

const RISK_ORDER = { HIGH: 3, MEDIUM: 2, LOW: 1 };

export function analyzeStockList(stocks) {
  return stocks.map((stock) => {
    const indicators = calculateIndicators(stock);
    const scoreResult = calculateScore(stock, indicators);
    const summary = buildReasonSummary(stock, indicators, scoreResult);
    return { stock, indicators, scoreResult, summary };
  });
}

export function buildBulkAnalysisSummary(results) {
  const countSignal = (signal) => results.filter((result) => result.scoreResult.signal === signal).length;
  return {
    total: results.length,
    buy: countSignal("買い候補"),
    splitBuy: countSignal("分割買い候補"),
    pullback: countSignal("押し目待ち"),
    overheatWarning: countSignal("高値掴み注意"),
    watch: countSignal("様子見"),
    skip: countSignal("見送り"),
    takeProfit: countSignal("利確候補"),
    lossCut: countSignal("損切り警戒"),
    highRisk: results.filter((result) => result.scoreResult.overheatRisk === "HIGH").length,
    upwardRevision: results.filter((result) => result.stock.hasUpwardRevision).length,
    downwardRevision: results.filter((result) => result.stock.hasDownwardRevision).length,
    policyTheme: results.filter((result) => result.stock.policyThemes?.length > 0).length,
    csv: results.filter((result) => result.stock.dataSource === "CSV").length,
    mock: results.filter((result) => result.stock.dataSource === "MOCK").length
  };
}

export function sortBulkAnalysisResults(results, sortKey = "buyScoreDesc") {
  const sorted = [...results];
  const value = (result, key) => {
    const { stock, indicators, scoreResult } = result;
    const values = {
      totalScoreDesc: scoreResult.totalScore,
      totalScoreAsc: -scoreResult.totalScore,
      buyScoreDesc: scoreResult.buyScore,
      buyScoreAsc: -scoreResult.buyScore,
      overheatRiskDesc: RISK_ORDER[scoreResult.overheatRisk] ?? 0,
      rsiDesc: indicators.rsi,
      rsiAsc: -indicators.rsi,
      ma25DeviationDesc: indicators.ma25Deviation,
      volumeRatioDesc: indicators.volumeRatio,
      near52wDesc: -indicators.high52wDrawdown,
      codeAsc: stock.code,
      nameAsc: stock.name
    };
    return values[key];
  };

  sorted.sort((a, b) => {
    const av = value(a, sortKey);
    const bv = value(b, sortKey);
    if (typeof av === "string") return av.localeCompare(String(bv), "ja");
    return bv - av;
  });
  return sorted;
}

export function filterBulkAnalysisResults(results, filters = {}) {
  const search = String(filters.search ?? "").trim().toLowerCase();
  return results.filter((result) => {
    const { stock, scoreResult } = result;
    if (search && !stock.code.toLowerCase().includes(search) && !stock.name.toLowerCase().includes(search)) return false;
    if (filters.signal && filters.signal !== "ALL" && scoreResult.signal !== filters.signal) return false;
    if (filters.risk && filters.risk !== "ALL" && scoreResult.overheatRisk !== filters.risk) return false;
    if (filters.material && filters.material !== "ALL" && !matchesMaterial(result, filters.material)) return false;
    return true;
  });
}

export function flattenAnalysisResult(result) {
  const { stock, indicators, scoreResult, summary } = result;
  return {
    code: stock.code,
    name: stock.name,
    dataSource: stock.dataSource,
    dataSourceLabel: stock.dataSourceLabel,
    tradableDataLabel: stock.tradableDataLabel || (stock.isTradableData ? "可" : "実売買不可"),
    signal: scoreResult.signal,
    signalLabel: scoreResult.signal,
    totalScore: scoreResult.totalScore,
    buyScore: scoreResult.buyScore,
    overheatRisk: scoreResult.overheatRisk,
    confidence: scoreResult.confidence,
    price: indicators.currentPrice,
    change: indicators.change,
    changePercent: indicators.changePercent,
    volume: indicators.volume,
    volumeRatio: indicators.volumeRatio,
    rsi: indicators.rsi,
    ma25: indicators.ma25,
    ma75: indicators.ma75,
    deviation25: indicators.ma25Deviation,
    deviation75: indicators.ma75Deviation,
    high52w: indicators.high52w,
    distanceFrom52wHigh: indicators.high52wDrawdown,
    highYtd: indicators.ytdHigh,
    distanceFromYtdHigh: indicators.ytdHighDrawdown,
    isBeforeEarnings: indicators.isBeforeEarnings,
    earningsTrend: stock.earningsTrend,
    hasUpwardRevision: stock.hasUpwardRevision,
    hasDownwardRevision: stock.hasDownwardRevision,
    hasDividendIncrease: stock.hasDividendIncrease,
    hasBuyback: stock.hasBuyback,
    policyThemes: stock.policyThemes?.join("・") || "",
    policyRelationType: stock.policyRelationType,
    mainBullReasons: summary.buyReasons.join(" / "),
    mainBearReasons: summary.weakReasons.join(" / "),
    mainWarnings: summary.cautions.join(" / "),
    actionPlan: summary.actionPolicy,
    lastUpdated: stock.lastUpdated,
    disclaimer: "このツールは投資助言ではありません。CSV取込データはユーザー提供データであり、正確性・最新性は保証されません。実売買判断には公式情報を確認してください。"
  };
}

function matchesMaterial(result, material) {
  const { stock, indicators } = result;
  const checks = {
    upwardRevision: stock.hasUpwardRevision,
    downwardRevision: stock.hasDownwardRevision,
    dividendIncrease: stock.hasDividendIncrease,
    buyback: stock.hasBuyback,
    beforeEarnings: indicators.isBeforeEarnings,
    policyTheme: stock.policyThemes?.length > 0,
    csvOnly: stock.dataSource === "CSV",
    mockOnly: stock.dataSource === "MOCK"
  };
  return Boolean(checks[material]);
}
