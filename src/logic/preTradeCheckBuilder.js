import { calculateIndicators } from "./indicators.js";

const FORBIDDEN_KEYS = [
  "apiKey",
  "JQUANTS_API_KEY",
  "x-api-key",
  "headers",
  "rawRows",
  "debugInfo",
  ".env"
];

export function buildPreTradeCheck(stockData, options = {}) {
  try {
    const indicators = options.indicators || calculateIndicators(stockData);
    const scoreResult = options.scoreResult || {};
    const dataSource = buildDataSourceCheck(stockData);
    const freshness = buildDataFreshnessCheck(stockData);
    const financial = buildFinancialCheck(stockData);
    const newsAndDisclosure = buildNewsAndDisclosureCheck(stockData);
    const risk = buildRiskCheck(stockData, { indicators, scoreResult });
    const checklist = buildPreTradeChecklist(stockData);
    const checks = { dataSource, freshness, financial, newsAndDisclosure, risk };
    const warning = buildPreTradeWarningLevel(checks);
    const overallStatus = buildOverallStatus(stockData, checks);
    const preTradeCheck = {
      available: true,
      generatedBy: "RULE_BASED",
      tradeAdvice: false,
      overallStatus,
      riskLevel: warning.riskLevel,
      summary: buildPreTradeSummary(stockData, checks, overallStatus),
      dataSource,
      freshness,
      financial,
      newsAndDisclosure,
      risk,
      checklist,
      warnings: [
        "このアプリは投資助言ではありません。",
        "実売買前には証券会社アプリ、会社IR、TDnet、最新ニュースを必ず確認してください。",
        "買い・売りを断定せず、確認不足や参考情報を見える化するためのチェックです。"
      ],
      structuredSummaryPreTrade: {
        overallStatus,
        requiredConfirmations: [
          "証券会社アプリ",
          "会社IR",
          "TDnet",
          "最新ニュース",
          "売買条件",
          "損切り条件"
        ],
        tradeAdvice: false
      }
    };
    return sanitizePreTradeCheck(preTradeCheck);
  } catch (error) {
    return {
      available: false,
      generatedBy: "RULE_BASED",
      tradeAdvice: false,
      overallStatus: "データ不足",
      riskLevel: "warning",
      summary: "実売買前チェックを生成できませんでした。",
      error: sanitizeText(error?.message || "unknown error"),
      checklist: buildPreTradeChecklist(stockData),
      warnings: ["このアプリは投資助言ではありません。実売買前には公式情報を確認してください。"]
    };
  }
}

export function buildDataFreshnessCheck(stockData) {
  const latestDate = stockData?.lastUpdated || stockData?.date || "";
  if (stockData?.isMock) {
    return {
      status: "danger",
      latestDate,
      message: "モックデータのため、実売買判断には使用できません。"
    };
  }
  if (stockData?.dataSource === "CSV") {
    return {
      status: "warning",
      latestDate,
      message: "CSVデータはユーザー提供データです。正確性・最新性は保証されません。"
    };
  }
  if (isJQuantsReal(stockData)) {
    return {
      status: "warning",
      latestDate,
      message: "J-Quants日足データを使用しています。無料プランでは遅延や取得範囲制限がある可能性があります。"
    };
  }
  return {
    status: latestDate ? "ok" : "warning",
    latestDate,
    message: latestDate ? "データ日付を確認できます。" : "データ日付を確認できません。"
  };
}

export function buildDataSourceCheck(stockData) {
  if (stockData?.isMock || String(stockData?.dataSource || "").includes("MOCK")) {
    return {
      status: "danger",
      label: "モックデータ",
      dataSource: stockData?.dataSource || "MOCK",
      isMock: true,
      isCsv: false,
      didNetworkRequest: Boolean(stockData?.didNetworkRequest),
      cacheHit: Boolean(stockData?.cacheHit),
      message: "モックデータのため、実売買判断には使用できません。"
    };
  }
  if (stockData?.dataSource === "CSV") {
    return {
      status: "warning",
      label: "CSVデータ",
      dataSource: "CSV",
      isMock: false,
      isCsv: true,
      didNetworkRequest: false,
      cacheHit: false,
      message: "CSVデータは公式情報ではありません。実売買前に必ず公式情報を確認してください。"
    };
  }
  if (isJQuantsReal(stockData)) {
    return {
      status: "ok",
      label: "J-Quants実データ",
      dataSource: stockData.dataSource,
      isMock: false,
      isCsv: false,
      didNetworkRequest: Boolean(stockData.didNetworkRequest),
      cacheHit: Boolean(stockData.cacheHit),
      message: "株価データはJ-Quants実データです。ただし、実売買前には証券会社アプリで現在値と出来高を確認してください。"
    };
  }
  return {
    status: "warning",
    label: stockData?.dataSourceLabel || stockData?.dataSource || "データ種別未確認",
    dataSource: stockData?.dataSource || "",
    isMock: Boolean(stockData?.isMock),
    isCsv: false,
    didNetworkRequest: Boolean(stockData?.didNetworkRequest),
    cacheHit: Boolean(stockData?.cacheHit),
    message: "データソースを確認してください。"
  };
}

export function buildFinancialCheck(stockData) {
  const summary = stockData?.financialSummary;
  if (summary?.available) {
    return {
      status: "ok",
      available: true,
      disclosedDate: summary.disclosedDate || "",
      disclosedTime: summary.disclosedTime || "",
      documentType: shortenDocumentType(summary.typeOfDocument || ""),
      message: "財務サマリーは取得済みです。ただし、決算詳細資料や補足資料は未確認です。"
    };
  }
  return {
    status: "warning",
    available: false,
    disclosedDate: "",
    disclosedTime: "",
    documentType: "",
    message: "財務サマリーは未取得です。会社IRや決算資料を確認してください。"
  };
}

export function buildNewsAndDisclosureCheck(stockData) {
  return {
    status: "not_connected",
    newsApiConnected: false,
    tdnetConnected: false,
    earningsDetailConnected: false,
    themeSource: stockData?.themeSummary?.source || "LOCAL_MOCK_THEME",
    message: "ニュースAPI、TDnet、決算詳細は未接続です。最新材料は別途確認してください。"
  };
}

export function buildRiskCheck(stockData, options = {}) {
  const indicators = options.indicators || calculateIndicators(stockData);
  const scoreResult = options.scoreResult || {};
  const overheatRisk = scoreResult.overheatRisk || "LOW";
  const highGrabRisk = overheatRisk === "HIGH" || indicators.nearHigh52w || indicators.overMa25
    ? "high"
    : overheatRisk === "MEDIUM"
      ? "medium"
      : "low";
  const rsiStatus = indicators.rsi >= 75
    ? "overheated"
    : indicators.rsi <= 30
      ? "oversold"
      : "neutral";
  return {
    status: highGrabRisk === "high" ? "warning" : "ok",
    overheatRisk: String(overheatRisk).toLowerCase(),
    highGrabRisk,
    rsiStatus,
    themeRisk: stockData?.themeSummary?.available
      ? "テーマ材料はローカル/手動情報です。思惑買いには注意してください。"
      : "テーマ材料は未確認です。",
    message: highGrabRisk === "high"
      ? "財務が良くても、買いタイミングは別途確認が必要です。"
      : "短期リスクは限定的に見えますが、公式情報確認は必要です。"
  };
}

export function buildPreTradeChecklist() {
  return [
    {
      id: "official_price_check",
      label: "証券会社アプリで現在値・出来高を確認した",
      required: true,
      checked: false,
      category: "price"
    },
    {
      id: "ir_check",
      label: "会社IR・決算資料を確認した",
      required: true,
      checked: false,
      category: "financial"
    },
    {
      id: "tdnet_check",
      label: "TDnetなど適時開示を確認した",
      required: true,
      checked: false,
      category: "disclosure"
    },
    {
      id: "news_check",
      label: "最新ニュース・材料を確認した",
      required: true,
      checked: false,
      category: "news"
    },
    {
      id: "entry_plan_check",
      label: "買う場合の条件・見送る条件を決めた",
      required: true,
      checked: false,
      category: "plan"
    },
    {
      id: "loss_rule_check",
      label: "損失許容額・撤退条件を決めた",
      required: true,
      checked: false,
      category: "risk"
    }
  ];
}

export function buildPreTradeWarningLevel(checks) {
  const values = Object.values(checks || {});
  if (values.some((check) => check?.status === "danger")) return { riskLevel: "danger" };
  if (values.some((check) => ["warning", "not_connected"].includes(check?.status))) return { riskLevel: "medium" };
  return { riskLevel: "low" };
}

function buildOverallStatus(stockData, checks) {
  if (stockData?.isMock || String(stockData?.dataSource || "").includes("MOCK")) return "モックのため実売買不可";
  if (stockData?.dataSource === "CSV") return "CSVデータのため公式情報確認必須";
  if (checks?.risk?.highGrabRisk === "high") return "高値掴み注意";
  if (!checks?.financial?.available) return "財務未取得・追加確認必要";
  if (checks?.newsAndDisclosure?.status === "not_connected") return "実データ確認済み・追加確認必要";
  return "確認不足あり";
}

function buildPreTradeSummary(stockData, checks, overallStatus) {
  if (stockData?.isMock || String(stockData?.dataSource || "").includes("MOCK")) {
    return "モックデータのため、実売買判断には使用できません。";
  }
  if (stockData?.dataSource === "CSV") {
    return "CSVデータは公式情報ではありません。正確性・最新性を別途確認してください。";
  }
  return `${checks.dataSource.label}を確認できますが、ニュース、TDnet、決算詳細は未接続です。実売買前には公式情報の確認が必要です。ステータス: ${overallStatus}`;
}

function isJQuantsReal(stockData) {
  return ["J_QUANTS_MAPPED", "J_QUANTS_REAL"].includes(stockData?.dataSource);
}

function shortenDocumentType(type) {
  const text = String(type || "");
  if (!text) return "";
  if (text.includes("3Q")) return "3Q決算短信";
  if (text.includes("2Q")) return "2Q決算短信";
  if (text.includes("1Q")) return "1Q決算短信";
  if (text.includes("FinancialStatements")) return "決算短信";
  return text.length > 32 ? `${text.slice(0, 32)}...` : text;
}

function sanitizePreTradeCheck(value) {
  const text = JSON.stringify(value || {});
  if (FORBIDDEN_KEYS.some((key) => text.includes(key))) {
    return JSON.parse(FORBIDDEN_KEYS.reduce((safeText, key) => safeText.replaceAll(key, "[redacted]"), text));
  }
  return value;
}

function sanitizeText(value) {
  return String(value || "").replace(/JQUANTS_API_KEY|x-api-key|rawRows|headers|\.env/gi, "[redacted]");
}
