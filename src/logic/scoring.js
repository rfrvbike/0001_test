export function calculateScore(stock, indicators) {
  const entries = [];
  let score = 0;

  const add = (label, value) => {
    if (!value) return;
    entries.push({ label, value });
    score += value;
  };

  add("株価が25日線より上", indicators.aboveMa25 ? 10 : 0);
  add("25日線が75日線より上", indicators.ma25AboveMa75 ? 10 : 0);
  add("出来高が20日平均の1.5倍以上", indicators.volumeSpike ? 10 : 0);
  add("直近高値を突破", stock.recentHighBreakout ? 15 : 0);
  add("上方修正あり", stock.hasUpwardRevision ?? stock.disclosure?.upwardRevision ? 20 : 0);
  add("増配あり", stock.hasDividendIncrease ?? stock.disclosure?.dividendIncrease ? 10 : 0);
  add("自社株買いあり", stock.hasBuyback ?? stock.disclosure?.buyback ? 10 : 0);
  add("国策テーマ関連あり", isPolicyRelated(stock) ? 10 : 0);
  add("RSIが50〜70", indicators.rsi >= 50 && indicators.rsi <= 70 ? 5 : 0);
  add("決算通過済みで内容良好", stock.postEarningsGood ?? stock.disclosure?.postEarningsGood ? 10 : 0);

  add("RSIが75以上", indicators.overheatRsi ? -15 : 0);
  add("25日線乖離率が+10%以上", indicators.overMa25 ? -15 : 0);
  add("52週高値まで3%以内", indicators.nearHigh52w ? -10 : 0);
  add("決算発表直前", indicators.isBeforeEarnings ? -10 : 0);
  add("出来高急増後に上ヒゲ", hasUpperWickAfterVolumeSpike(stock) ? -15 : 0);
  add("下方修正あり", stock.hasDownwardRevision ?? stock.disclosure?.downwardRevision ? -30 : 0);
  add("株価が25日線を下回る", !indicators.aboveMa25 ? -20 : 0);
  add("株価が75日線を下回る", !indicators.aboveMa75 ? -30 : 0);
  add("減益決算", getEarningsTrend(stock) === "DECLINING" ? -15 : 0);
  add("材料出尽くし懸念", stock.exhaustionConcern ?? stock.disclosure?.exhaustionConcern ? -10 : 0);

  const financialEvaluation = calculateFinancialScore(stock);
  if (financialEvaluation.shouldDisplay) {
    entries.push({
      label: "財務参考評価",
      value: financialEvaluation.appliedScore,
      note: financialEvaluation.label
    });
    score += financialEvaluation.appliedScore;
  }

  const boundedScore = Math.max(-100, Math.min(100, score));
  const buyScore = Math.max(0, Math.min(100, Math.round((boundedScore + 100) / 2)));
  const warnings = buildWarnings(stock, indicators);
  const signal = judgeSignal(boundedScore, warnings);
  const overheatRisk = judgeOverheatRisk(warnings, indicators);
  const confidence = Math.max(35, Math.min(95, 72 + Math.abs(boundedScore) * 0.18 - warnings.length * 4));

  return {
    totalScore: boundedScore,
    buyScore,
    confidence: Math.round(confidence),
    entries,
    warnings,
    signal,
    overheatRisk,
    financialScore: financialEvaluation.score,
    appliedFinancialScore: financialEvaluation.appliedScore,
    financialScoreEnabled: financialEvaluation.enabled,
    financialScoreLabel: financialEvaluation.label,
    financialComment: financialEvaluation.comment
  };
}

export function calculateFinancialScore(stock) {
  const summary = stock?.financialSummary;
  const hasFinancialContext = Boolean(summary || stock?.financialSignals || stock?.financialSummaryStatus);
  const enabled = stock?.useFinancialScore !== false;

  if (!summary?.available) {
    return {
      score: 0,
      appliedScore: 0,
      enabled,
      shouldDisplay: hasFinancialContext,
      label: "財務未取得",
      comment: "財務サマリーを取得できなかったため、株価・テクニカル情報中心の判定です。"
    };
  }

  let score = 0;
  if (isPositiveNumber(summary.operatingProfit)) score += 1;
  if (isNegativeNumber(summary.operatingProfit)) score -= 2;
  if (isPositiveNumber(summary.profit)) score += 1;
  if (isNegativeNumber(summary.profit)) score -= 2;
  if (isPositiveNumber(summary.earningsPerShare)) score += 1;
  if (isNegativeNumber(summary.earningsPerShare)) score -= 1;
  if (isPositiveNumber(summary.cashFlowsFromOperatingActivities)) score += 1;
  if (isNegativeNumber(summary.cashFlowsFromOperatingActivities)) score -= 1;
  if (isPositiveNumber(summary.dividendPerShareAnnual)) score += 1;

  const bounded = Math.max(-5, Math.min(5, score));
  const label = bounded >= 4
    ? "財務はおおむね良好"
    : bounded > 0
      ? "財務はやや良好"
      : bounded < 0
        ? "財務に注意"
        : "財務は中立";

  return {
    score: bounded,
    appliedScore: enabled ? bounded : 0,
    enabled,
    shouldDisplay: true,
    label,
    comment: buildFinancialScoreComment(summary, bounded)
  };
}

export function judgeSignal(score, warnings = []) {
  const hasPriorityWarning = warnings.length > 0;
  if (score <= -40) return "損切り警戒";
  if (score < 0) return "見送り";
  if (hasPriorityWarning && score >= 50) return "高値掴み注意";
  if (hasPriorityWarning && score >= 30) return "押し目待ち";
  if (score >= 70) return "買い候補";
  if (score >= 50) return "分割買い候補";
  if (score >= 30) return "押し目待ち";
  return "様子見";
}

function buildWarnings(stock, indicators) {
  return [
    indicators.overheatRsi && "RSI 75以上",
    indicators.overMa25 && "25日線乖離率 +10%以上",
    indicators.nearHigh52w && "52週高値まで3%以内",
    indicators.isBeforeEarnings && "決算発表直前",
    hasUpperWickAfterVolumeSpike(stock) && "出来高急増後の上ヒゲ"
  ].filter(Boolean);
}

function judgeOverheatRisk(warnings, indicators) {
  const riskPoints = warnings.length
    + (indicators.volumeSpike ? 1 : 0)
    + (indicators.rsi >= 70 ? 1 : 0);
  if (riskPoints >= 3) return "HIGH";
  if (riskPoints >= 1) return "MEDIUM";
  return "LOW";
}

function isPolicyRelated(stock) {
  if (stock.policyTheme) return stock.policyTheme.isRelated;
  return Array.isArray(stock.policyThemes) && stock.policyThemes.length > 0;
}

function getEarningsTrend(stock) {
  return stock.earningsTrend ?? stock.disclosure?.earningsTrend;
}

function hasUpperWickAfterVolumeSpike(stock) {
  return stock.largeUpperWickAfterVolumeSpike || stock.candlePattern === "VOLUME_SPIKE_UPPER_WICK";
}

function isPositiveNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0;
}

function isNegativeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number < 0;
}

function buildFinancialScoreComment(summary, score) {
  if (score > 0) {
    const points = [
      isPositiveNumber(summary.operatingProfit) && "営業利益",
      isPositiveNumber(summary.profit) && "純利益",
      isPositiveNumber(summary.earningsPerShare) && "EPS",
      isPositiveNumber(summary.cashFlowsFromOperatingActivities) && "営業CF",
      isPositiveNumber(summary.dividendPerShareAnnual) && "配当"
    ].filter(Boolean);
    return `${points.join("・") || "主要財務項目"}がプラスで、財務面は参考材料として悪くありません。ただし通常スコアへの反映は最大±5点に限定しています。`;
  }
  if (score < 0) {
    return "営業利益・純利益・EPS・営業CFの一部に弱さがあり、財務面は注意材料です。ただし通常スコアへの反映は最大±5点に限定しています。";
  }
  return "財務サマリーは取得済みですが、評価対象項目は中立です。決算詳細やTDnet開示は未接続です。";
}
