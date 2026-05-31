const FORBIDDEN_PATTERNS = [
  /JQUANTS_API_KEY/i,
  /x-api-key/i,
  /rawRows/i,
  /headers/i,
  /\.env/i,
  /localStorage/i
];

export function buildAiSummaryMock(structuredSummary, options = {}) {
  if (options.enabled === false) {
    return {
      available: false,
      enabled: false,
      mode: "disabled",
      aiGenerated: false,
      externalApiUsed: false,
      provider: "none",
      message: "AI要約モックは無効です。"
    };
  }

  const safeSummary = sanitizeAiSummaryInput(structuredSummary);
  let shortComment = buildShortAiLikeComment(safeSummary);
  if (safeSummary?.theme?.available && !shortComment.includes("テーマ")) {
    shortComment += ` テーマ材料としては、${safeSummary.theme.comment || safeArray(safeSummary.theme.themes).join("・")}。`;
  }
  const bullets = buildAiSummaryBullets(safeSummary);
  const warnings = buildAiSummaryWarnings(safeSummary);

  return {
    available: true,
    mode: "rule_based_mock",
    aiGenerated: false,
    externalApiUsed: false,
    provider: "none",
    title: "AI要約プレビュー（モック）",
    shortComment,
    bullets,
    warnings,
    source: {
      structuredSummaryVersion: safeSummary?.version || "1.0",
      generatedBy: safeSummary?.generatedBy || "RULE_BASED"
    }
  };
}

export function buildShortAiLikeComment(structuredSummary) {
  const decisionLabel = structuredSummary?.decision?.label || "データ不足";
  const stockName = structuredSummary?.stock?.name || structuredSummary?.stock?.code || "この銘柄";
  const technicalComment = structuredSummary?.technical?.comment || "テクニカル情報は限定的です。";
  const financialComment = structuredSummary?.financial?.comment || "財務情報は未取得です。";
  const themeComment = structuredSummary?.theme?.available ? structuredSummary.theme.comment : "";
  const riskComment = structuredSummary?.risks?.comment || "リスク確認が必要です。";
  const themeSentence = themeComment ? `テーマ面では、${themeComment}` : "";

  if (decisionLabel === "買い候補") {
    return `${stockName}は、テクニカルと財務の両面では悪くない状態です。${technicalComment}${financialComment}${themeSentence}ただし、これは買いを断定するものではなく、実際の判断では最新の決算資料や開示情報も確認してください。`;
  }
  if (decisionLabel === "押し目待ち") {
    return `${stockName}は、基調や財務面では参考材料があります。${financialComment}${themeSentence}一方で、短期的にはやや高値圏や過熱感があり、今すぐ飛びつくより押し目を待ってから判断する方が安全です。実売買前には決算資料やTDnet開示を確認してください。`;
  }
  if (decisionLabel === "高値掴み注意") {
    return `${stockName}は、企業内容に参考材料があっても、株価の位置はやや高く見える局面です。${themeSentence}${riskComment}買いタイミングは慎重に見たいところで、押し目や過熱感の落ち着きを確認してから判断してください。`;
  }
  if (decisionLabel === "様子見") {
    return `${stockName}は、現時点では判断材料がやや中立です。${technicalComment}${financialComment}無理に動かず、出来高や移動平均線、公式開示の変化を確認する姿勢が無難です。`;
  }
  if (decisionLabel === "見送り") {
    return `${stockName}は、現時点では慎重に見たい材料が残っています。${technicalComment}${riskComment}新規判断では、弱材料が解消するか、公式情報で改善が確認できるまで待つ選択肢があります。`;
  }
  if (decisionLabel === "売られすぎ反発候補") {
    return `${stockName}は、短期的には売られすぎからの反発余地が意識される可能性があります。ただし、下落理由が解消したとは限らないため、反発狙いでもリスク確認が必要です。投資助言ではなく、公式情報確認を前提にした参考コメントです。`;
  }
  return `${stockName}は、現時点では判断材料が不足しています。${themeSentence}価格・テクニカル・財務・開示情報を追加で確認し、実売買判断には公式情報を必ず確認してください。`;
}

export function buildAiSummaryBullets(structuredSummary) {
  const positives = safeArray(structuredSummary?.positives).slice(0, 2);
  const cautions = safeArray(structuredSummary?.cautions).slice(0, 2);
  const technical = structuredSummary?.technical?.trend ? `株価は${structuredSummary.technical.trend}です。` : null;
  const financial = structuredSummary?.financial?.available
    ? structuredSummary.financial.label || "財務面は取得済みです。"
    : "財務情報は未取得または限定的です。";
  const theme = structuredSummary?.theme?.available
    ? `テーマ材料：${safeArray(structuredSummary.theme.themes).slice(0, 4).join("・")}`
    : null;

  return unique([
    technical,
    financial,
    theme,
    ...positives,
    ...cautions,
    "実売買前には公式情報を確認してください。"
  ].filter(Boolean)).slice(0, 6);
}

export function buildAiSummaryWarnings(structuredSummary) {
  const warnings = [
    "この要約はAI APIではなく、ルールベースのモック生成です。",
    "投資助言ではありません。",
    "実売買前には必ず公式情報を確認してください。"
  ];
  if (structuredSummary?.risks?.highGrabRisk === "high") warnings.push("高値掴みリスクがある場合、財務が良くても買いタイミングは慎重に見てください。");
  if (structuredSummary?.theme?.available) {
    warnings.push("テーマ材料は外部ニュースAPIではなくローカルモックまたは手動入力です。");
    warnings.push("最新ニュースは別途確認してください。");
    warnings.push("思惑買いだけで売買判断しないでください。");
  }
  if (structuredSummary?.stock?.dataSource === "CSV") warnings.push("CSVデータはユーザー提供データであり、正確性・最新性は保証されません。");
  if (String(structuredSummary?.stock?.dataSource || "").includes("MOCK")) warnings.push("モックデータは実売買判断には使えません。");
  return unique(warnings);
}

export function sanitizeAiSummaryInput(structuredSummary) {
  const copy = JSON.parse(JSON.stringify(structuredSummary || {}));
  delete copy.aiPromptPayload?.data?.rawRows;
  delete copy.rawRows;
  delete copy.headers;
  delete copy.requestHeaders;
  delete copy.localStorage;
  const text = JSON.stringify(copy);
  if (FORBIDDEN_PATTERNS.some((pattern) => pattern.test(text))) {
    return JSON.parse(
      text
        .replace(/JQUANTS_API_KEY/gi, "[redacted]")
        .replace(/x-api-key/gi, "[redacted]")
        .replace(/rawRows/gi, "[redacted]")
        .replace(/headers/gi, "[redacted]")
        .replace(/\.env/gi, "[redacted]")
        .replace(/localStorage/gi, "[redacted]")
    );
  }
  return copy;
}

function safeArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}
