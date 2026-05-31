export function buildReasonSummary(stock, indicators, scoreResult) {
  const buyReasons = [
    indicators.aboveMa25 && indicators.aboveMa75 && "25日線、75日線を上回っており上昇トレンド",
    indicators.ma25AboveMa75 && "25日線が75日線を上回り中期トレンドが良好",
    indicators.volumeSpike && "出来高が20日平均を上回り注目度が高い",
    stock.recentHighBreakout && "直近高値を突破している",
    stock.hasUpwardRevision && "上方修正が確認されている",
    stock.hasDividendIncrease && "増配が好材料",
    stock.hasBuyback && "自社株買いが需給面の支え",
    stock.policyThemes?.length > 0 && `国策テーマ（${stock.policyThemes.join("、")}）に関連`
  ].filter(Boolean);

  const weakReasons = [
    !indicators.aboveMa25 && "株価が25日線を下回っている",
    !indicators.aboveMa75 && "株価が75日線を下回っている",
    stock.hasDownwardRevision && "下方修正があり業績リスクが大きい",
    stock.earningsTrend === "DECLINING" && "減益決算で利益モメンタムが弱い",
    stock.exhaustionConcern && "材料出尽くし懸念がある"
  ].filter(Boolean);

  const cautions = [
    indicators.nearHigh52w && "52週高値に近く高値掴みリスクがある",
    indicators.overheatRsi && "RSIが75以上で短期過熱",
    indicators.overMa25 && "25日線から上がりすぎている",
    indicators.isBeforeEarnings && "決算前のため急変動に注意",
    stock.candlePattern === "VOLUME_SPIKE_UPPER_WICK" && "出来高急増後の上ヒゲがあり利確売りに注意",
    stock.isMock && "この判定はモックデータに基づくテスト結果です",
    stock.dataSource === "CSV" && "CSVデータはユーザー提供データであり、正確性・最新性は保証されません",
    isJQuantsRealStock(stock) && "J-Quants日足データ由来ですが、財務・決算・TDnetは未接続です"
  ].filter(Boolean);

  const financialReason = buildFinancialReason(stock, scoreResult, indicators);
  if (financialReason.buyReason) buyReasons.push(financialReason.buyReason);
  if (financialReason.weakReason) weakReasons.push(financialReason.weakReason);
  financialReason.cautions.forEach((caution) => cautions.push(caution));

  const actionPolicy = buildActionPolicy(scoreResult.signal, scoreResult.overheatRisk, stock);
  const skipReason = buildSkipReason(scoreResult.signal, weakReasons, cautions, stock);

  return {
    buyReasons: fillDefault(buyReasons, "明確な買い材料は限定的"),
    weakReasons: fillDefault(weakReasons, defaultWeakReason(stock)),
    cautions: fillDefault(cautions, "過熱シグナルは限定的"),
    actionPolicy,
    skipReason,
    dataNotice: buildDataNotice(stock)
  };
}

function buildActionPolicy(signal, risk, stock) {
  const mockPrefix = stock.isMock ? "モックデータ上のテスト判定です。実売買には使わないでください。 " : "";
  const csvPrefix = stock.dataSource === "CSV" ? "CSV取込データ上の判定です。公式情報で必ず確認してください。 " : "";
  const jquantsPrefix = isJQuantsRealStock(stock) ? "J-Quants日足データを使ったテクニカル中心の参考判定です。財務・決算・TDnetは未接続です。 " : "";
  const prefix = mockPrefix || csvPrefix || jquantsPrefix;
  if (signal === "買い候補") return `${prefix}トレンドと材料は良好。過熱が強まるまでは買い候補として監視。`;
  if (signal === "分割買い候補") return `${prefix}一括ではなく、少額から分割して入る方針が無難。`;
  if (signal === "高値掴み注意") return risk === "HIGH"
    ? `${prefix}今すぐ全力買いは避け、押し目または過熱解消を待つ方針。`
    : `${prefix}買う場合は分割にとどめ、高値更新後の反落に備える。`;
  if (signal === "押し目待ち") return `${prefix}材料は確認しつつ、25日線付近への押し目を待ちたい局面。`;
  if (signal === "損切り警戒") return `${prefix}保有中なら損切りラインを明確にし、新規買いは避けたい局面。`;
  return `${prefix}新規買いは急がず、材料とテクニカルの改善を待つ。`;
}

function buildSkipReason(signal, weakReasons, cautions, stock) {
  if (stock.isMock) return "現在は実市場データではないため、実売買判断としては必ず見送り扱いにしてください。";
  if (stock.dataSource === "CSV") return "CSVデータの正確性・最新性は保証されないため、実売買前に公式情報で確認してください。";
  if (isJQuantsRealStock(stock)) return "J-Quants日足データは取得済みですが、財務・決算・TDnetは未接続のため、実売買前に公式情報で確認してください。";
  if (signal === "買い候補" || signal === "分割買い候補") {
    return cautions.length ? "高値圏や決算前リスクが強まる場合は見送り。" : "明確な悪材料が出た場合は見送り。";
  }
  return [...weakReasons, ...cautions].slice(0, 3).join("。") || "優位性がまだ十分ではない。";
}

function fillDefault(items, fallback) {
  return items.length ? items : [fallback];
}

function defaultWeakReason(stock) {
  if (isJQuantsRealStock(stock)) return "日足テクニカル上では大きな弱気材料は限定的です。ただし財務・決算・TDnetは未接続です";
  if (stock.dataSource === "CSV") return "CSV上では大きな弱気材料は限定的です。公式情報で確認してください";
  return "大きな弱気材料はモック上では目立たない";
}

function buildDataNotice(stock) {
  if (stock.isMock) return "この判定はモックデータに基づくテスト結果です。実際の投資判断には使えません。";
  if (stock.dataSource === "CSV") return "CSVデータはユーザー提供データです。正確性・最新性は保証されません。実売買判断には必ず公式情報を確認してください。";
  if (isJQuantsRealStock(stock)) return "J-Quants日足データから変換した実データです。財務・決算・開示・TDnetは未接続です。無料プランではデータ遅延や取得範囲制限があります。";
  return "実データ接続後も最終判断は自己責任です。";
}

function isJQuantsRealStock(stock) {
  return stock?.dataSource === "J_QUANTS_MAPPED" || stock?.dataSource === "J_QUANTS_REAL";
}

function buildFinancialReason(stock, scoreResult, indicators) {
  const signals = stock?.financialSignals;
  const summary = stock?.financialSummary;
  const cautions = [];

  if (!signals && !summary) {
    return { buyReason: null, weakReason: null, cautions };
  }

  if (!signals?.hasFinancialSummary || summary?.available === false) {
    cautions.push("財務サマリーは未取得です。株価・テクニカル中心の参考判定として見てください。");
    return { buyReason: null, weakReason: null, cautions };
  }

  const score = Number(signals.financialScore ?? scoreResult.financialScore ?? 0);
  const comment = signals.financialComment || scoreResult.financialComment;
  const buyReason = score > 0
    ? comment || "営業利益・純利益・EPSなどがプラスで、財務面は参考材料として悪くありません。"
    : null;
  const weakReason = score < 0
    ? comment || "主要財務項目の一部に弱さがあり、財務面は注意材料です。"
    : null;

  cautions.push("財務サマリーは取得済みですが、決算詳細・TDnet開示は未接続です。最終判断には公式資料確認が必要です。");
  if ((indicators?.overheatRsi || scoreResult?.overheatRisk === "HIGH") && score > 0) {
    cautions.push("財務面は悪くありませんが、RSIや高値圏リスクがある場合は企業内容と買いタイミングを分けて判断してください。");
  }

  return { buyReason, weakReason, cautions };
}
