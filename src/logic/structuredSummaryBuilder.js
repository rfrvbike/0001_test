import { calculateIndicators } from "./indicators.js";
import { buildReasonSummary } from "./summaryBuilder.js";

const DECISION_LABELS = new Set([
  "買い候補",
  "押し目待ち",
  "様子見",
  "見送り",
  "高値掴み注意",
  "売られすぎ反発候補",
  "データ不足"
]);

export function buildStructuredSummary(stockData, scoreResult, options = {}) {
  try {
    const indicators = options.indicators || calculateIndicators(stockData, options.today || new Date());
    const reasonSummary = options.summary || buildReasonSummary(stockData, indicators, scoreResult);
    const structuredSummary = {
      version: "1.0",
      generatedBy: "RULE_BASED",
      aiReady: true,
      aiGenerated: false,
      disclaimer: "このサマリーは投資助言ではありません。実売買前には必ず公式情報を確認してください。",
      decision: buildDecisionLabel(stockData, scoreResult, indicators),
      stock: buildStockSummary(stockData),
      technical: buildTechnicalSummary(stockData, scoreResult, indicators),
      financial: buildFinancialSummaryForDecision(stockData),
      theme: buildThemeSummaryForDecision(stockData),
      risks: buildRiskSummary(stockData, scoreResult, indicators),
      positives: buildPositives(stockData, scoreResult, indicators, reasonSummary),
      cautions: buildCautions(stockData, scoreResult, indicators, reasonSummary),
      entryPlan: buildEntryPlan(stockData, scoreResult, indicators),
      aiPromptPayload: null
    };
    structuredSummary.aiPromptPayload = buildAiPromptPayload(stockData, scoreResult, structuredSummary);
    return structuredSummary;
  } catch (error) {
    return {
      version: "1.0",
      generatedBy: "RULE_BASED",
      aiReady: false,
      aiGenerated: false,
      disclaimer: "このサマリーは投資助言ではありません。実売買前には必ず公式情報を確認してください。",
      decision: {
        label: "データ不足",
        shortLabel: "データ不足",
        confidence: "low",
        stance: "wait",
        reason: "判断サマリーを生成できませんでした。"
      },
      error: sanitizeError(error)
    };
  }
}

export function buildTechnicalSummary(stockData, scoreResult, indicators = calculateIndicators(stockData)) {
  const trend = indicators.aboveMa25 && indicators.aboveMa75
    ? "上昇傾向"
    : !indicators.aboveMa25 && !indicators.aboveMa75
      ? "弱含み"
      : "中立";
  const rsiStatus = indicators.rsi >= 75
    ? "過熱"
    : indicators.rsi >= 65
      ? "やや過熱"
      : indicators.rsi <= 30
        ? "売られすぎ"
        : "中立";
  const volumeStatus = indicators.volumeRatio >= 1.5
    ? "出来高増加"
    : indicators.volumeRatio > 0
      ? "通常"
      : "未取得";

  return {
    trend,
    pricePosition: buildPricePosition(indicators),
    rsiStatus,
    rsi: safeNumber(indicators.rsi),
    ma25: safeNumber(indicators.ma25),
    ma75: safeNumber(indicators.ma75),
    price: safeNumber(indicators.currentPrice),
    volumeStatus,
    volumeRatio: roundOrNull(indicators.volumeRatio, 2),
    comment: buildTechnicalComment(trend, rsiStatus, scoreResult)
  };
}

export function buildFinancialSummaryForDecision(stockData) {
  const summary = stockData?.financialSummary;
  const signals = stockData?.financialSignals;
  if (!summary?.available) {
    return {
      available: false,
      score: 0,
      scoreMax: 5,
      label: "財務未取得",
      comment: signals?.financialComment || "財務サマリーは未取得です。株価・テクニカル情報中心の参考判定です。"
    };
  }

  return {
    available: true,
    score: safeNumber(signals?.financialScore ?? stockData?.financialScore ?? 0),
    scoreMax: 5,
    label: signals?.financialScoreLabel || "財務参考評価",
    netSales: nullableNumber(summary.netSales),
    operatingProfit: nullableNumber(summary.operatingProfit),
    profit: nullableNumber(summary.profit),
    eps: nullableNumber(summary.earningsPerShare),
    dividendPerShareAnnual: nullableNumber(summary.dividendPerShareAnnual),
    operatingCashFlow: nullableNumber(summary.cashFlowsFromOperatingActivities),
    comment: signals?.financialComment || "財務サマリーは取得済みですが、決算詳細・TDnetは未接続です。"
  };
}

export function buildThemeSummaryForDecision(stockData) {
  const themeSummary = stockData?.themeSummary;
  if (!themeSummary?.available) {
    return {
      available: false,
      themes: [],
      comment: themeSummary?.comment || "テーマ材料は未取得です。",
      risks: [],
      externalNewsApiUsed: false,
      externalAiUsed: false
    };
  }
  return {
    available: true,
    themes: safeArray(themeSummary.themes),
    comment: themeSummary.comment || "テーマ材料があります。",
    risks: safeArray(themeSummary.risks),
    source: themeSummary.source || "LOCAL_MOCK_THEME",
    externalNewsApiUsed: false,
    externalAiUsed: false
  };
}

export function buildRiskSummary(stockData, scoreResult, indicators = calculateIndicators(stockData)) {
  const warnings = [
    ...safeArray(scoreResult?.warnings),
    indicators.overheatRsi && "RSIが高く短期的に過熱感があります",
    indicators.overMa25 && "25日線から上がりすぎている可能性があります",
    indicators.nearHigh52w && "52週高値に近く高値掴みリスクがあります",
    stockData?.financialSignals?.financialScore > 0 && (indicators.overheatRsi || scoreResult?.overheatRisk === "HIGH") && "財務が良くても買いタイミングは慎重に見る必要があります"
  ].filter(Boolean);

  const highGrabRisk = scoreResult?.overheatRisk === "HIGH" || indicators.nearHigh52w || indicators.overMa25
    ? "high"
    : scoreResult?.overheatRisk === "MEDIUM"
      ? "medium"
      : "low";

  return {
    overheatRisk: String(scoreResult?.overheatRisk || "LOW").toLowerCase(),
    highGrabRisk,
    warnings: unique(warnings),
    comment: highGrabRisk === "high"
      ? "企業内容と買いタイミングは分けて判断してください。短期的には高値掴みに注意が必要です。"
      : "現時点の過熱リスクは限定的ですが、公式情報の確認は必要です。"
  };
}

export function buildDecisionLabel(stockData, scoreResult, indicators = calculateIndicators(stockData)) {
  const financialScore = Number(stockData?.financialSignals?.financialScore ?? scoreResult?.financialScore ?? 0);
  const hasFinancial = Boolean(stockData?.financialSummary?.available);
  const isOverheated = indicators.overheatRsi || indicators.overMa25 || indicators.nearHigh52w || scoreResult?.overheatRisk === "HIGH";

  let label = "様子見";
  if (isMissingCoreData(stockData)) label = "データ不足";
  else if (isOverheated && scoreResult.totalScore >= 30) label = indicators.nearHigh52w || scoreResult?.overheatRisk === "HIGH" ? "高値掴み注意" : "押し目待ち";
  else if (indicators.rsi <= 30 && scoreResult.totalScore >= 0 && financialScore >= 0) label = "売られすぎ反発候補";
  else if (scoreResult.totalScore >= 55 && (!hasFinancial || financialScore >= 0)) label = "買い候補";
  else if (scoreResult.totalScore >= 30) label = "押し目待ち";
  else if (scoreResult.totalScore < 0) label = "見送り";

  if (!DECISION_LABELS.has(label)) label = "様子見";
  return {
    label,
    shortLabel: label,
    confidence: confidenceLabel(scoreResult.confidence),
    stance: decisionStance(label),
    reason: buildDecisionReason(label, stockData, scoreResult, indicators)
  };
}

export function buildAiPromptPayload(stockData, scoreResult, structuredSummary) {
  return {
    purpose: "short_japanese_stock_commentary",
    instruction: "以下の構造化データをもとに、投資助言にならない範囲で、初心者にも分かる短い日本語コメントを作成する。",
    constraints: [
      "買い・売りを断定しない",
      "投資助言ではないと分かる表現にする",
      "財務が良くても高値掴みリスクを無視しない",
      "公式情報確認を促す",
      "APIキー、headers、raw全文、localStorage情報は扱わない"
    ],
    data: {
      code: stockData?.code || "",
      name: stockData?.name || "",
      market: stockData?.market || "",
      sector: stockData?.sector || "",
      decisionLabel: structuredSummary.decision?.label || "データ不足",
      totalScore: safeNumber(scoreResult?.totalScore),
      buyScore: safeNumber(scoreResult?.buyScore),
      technicalSummary: structuredSummary.technical?.comment || "",
      financialSummary: structuredSummary.financial?.comment || "",
      themeSummary: structuredSummary.theme?.comment || "",
      risks: safeArray(structuredSummary.risks?.warnings),
      positives: safeArray(structuredSummary.positives),
      cautions: safeArray(structuredSummary.cautions)
    }
  };
}

function buildStockSummary(stockData) {
  return {
    code: stockData?.code || "",
    name: stockData?.name || "",
    market: stockData?.market || "",
    sector: stockData?.sector || "",
    dataSource: stockData?.dataSource || "",
    lastUpdated: stockData?.lastUpdated || ""
  };
}

function buildPricePosition(indicators) {
  if (indicators.aboveMa25 && indicators.aboveMa75) return "25日線・75日線を上回っています";
  if (!indicators.aboveMa25 && !indicators.aboveMa75) return "25日線・75日線を下回っています";
  if (indicators.aboveMa25) return "25日線は上回りますが、75日線との位置は中立です";
  return "25日線を下回っており、短期的には慎重です";
}

function buildTechnicalComment(trend, rsiStatus, scoreResult) {
  if (scoreResult?.overheatRisk === "HIGH") return `株価は${trend}ですが、短期的な過熱感が強く、買いタイミングには注意が必要です。`;
  return `株価は${trend}で、RSIは${rsiStatus}です。テクニカルは参考材料として確認してください。`;
}

function buildPositives(stockData, scoreResult, indicators, reasonSummary) {
  return unique([
    indicators.aboveMa25 && indicators.aboveMa75 && "25日線・75日線を上回る上昇傾向",
    indicators.ma25AboveMa75 && "25日線が75日線を上回る中期トレンド",
    stockData?.financialSummary?.available && Number(stockData?.financialSignals?.financialScore || 0) > 0 && "財務参考評価がプラス",
    stockData?.financialSummary?.available && "営業利益・純利益・EPSなどの財務サマリーを確認済み",
    stockData?.themeSummary?.available && `${safeArray(stockData.themeSummary.themes).slice(0, 3).join("・")}などのテーマ性があります`,
    ...safeArray(reasonSummary?.buyReasons).slice(0, 3)
  ].filter(Boolean));
}

function buildCautions(stockData, scoreResult, indicators, reasonSummary) {
  return unique([
    indicators.nearHigh52w && "短期的には高値圏に近い可能性があります",
    indicators.overheatRsi && "RSIが高く、短期的な過熱に注意が必要です",
    indicators.overMa25 && "25日線からの乖離が大きく、飛びつき買いに注意が必要です",
    stockData?.financialSummary?.available && "決算詳細・TDnetは未接続です",
    stockData?.themeSummary?.available && "テーマ材料は短期的な思惑で上下しやすく、材料出尽くしに注意が必要です",
    stockData?.themeSummary?.available && "外部ニュースAPI未接続のため、最新ニュースは別途確認してください",
    stockData?.dataSource === "CSV" && "CSVデータはユーザー提供データであり、正確性は保証されません",
    stockData?.isMock && "モックデータは実売買判断には使えません",
    "このデータだけで実売買判断しないでください",
    ...safeArray(reasonSummary?.cautions).slice(0, 3)
  ].filter(Boolean));
}

function buildEntryPlan(stockData, scoreResult, indicators) {
  const cautious = indicators.overheatRsi || indicators.nearHigh52w || scoreResult?.overheatRisk !== "LOW";
  return {
    ifBuying: cautious
      ? [
        "今すぐ飛びつくより、25日線付近までの押し目を待つ",
        "出来高が落ち着くか確認する",
        "公式決算資料やTDnet開示を確認する"
      ]
      : [
        "少額から分割で入る",
        "25日線を下回らないか確認する",
        "公式情報で材料の裏付けを確認する"
      ],
    ifWatching: [
      "25日線を大きく割らずに反発するか確認する",
      "RSIが落ち着くまで待つ",
      "次の決算・業績修正を確認する"
    ],
    invalidation: [
      "25日線・75日線を明確に下回る",
      "業績悪化や下方修正が確認される",
      "出来高を伴う急落が発生する"
    ]
  };
}

function buildDecisionReason(label, stockData, scoreResult, indicators) {
  const financialGood = Number(stockData?.financialSignals?.financialScore || 0) > 0;
  if ((label === "押し目待ち" || label === "高値掴み注意") && financialGood) {
    return "財務面は良好ですが、短期的には過熱感や高値圏リスクがあり、今すぐ飛びつくより押し目を待つ局面です。";
  }
  if (label === "買い候補") return "テクニカルが比較的良好で、過熱リスクも限定的です。ただし売買判断には公式情報確認が必要です。";
  if (label === "売られすぎ反発候補") return "RSIが低く、短期的な反発余地はありますが、下落理由の確認が必要です。";
  if (label === "見送り") return "テクニカルまたは材料面の弱さがあり、現時点では慎重に見たい局面です。";
  if (label === "データ不足") return "判断に必要なデータが不足しているため、公式情報や追加データを確認してください。";
  return "現時点では決め手に欠けるため、材料・出来高・移動平均線の変化を確認したい局面です。";
}

function confidenceLabel(confidence) {
  const value = Number(confidence);
  if (!Number.isFinite(value)) return "low";
  if (value >= 80) return "high";
  if (value >= 60) return "medium";
  return "low";
}

function decisionStance(label) {
  if (label === "買い候補" || label === "売られすぎ反発候補") return "watch_to_buy";
  if (label === "押し目待ち" || label === "高値掴み注意") return "watch";
  if (label === "見送り") return "avoid";
  return "wait";
}

function isMissingCoreData(stockData) {
  return !stockData || stockData.price == null || stockData.ma25 == null || stockData.ma75 == null || stockData.rsi == null;
}

function safeArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function safeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function nullableNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  return safeNumber(value);
}

function roundOrNull(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Number(number.toFixed(digits));
}

function sanitizeError(error) {
  return String(error?.message || error || "Unknown error")
    .replace(/x-api-key[^\s,;]*/gi, "x-api-key[redacted]")
    .replace(/JQUANTS_API_KEY[^\s,;]*/g, "JQUANTS_API_KEY[redacted]");
}
