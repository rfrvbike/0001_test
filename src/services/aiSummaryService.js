import { buildReasonSummary } from "../logic/summaryBuilder.js";

export function buildRuleBasedSummary(stockData, indicators, scoringResult) {
  return buildReasonSummary(stockData, indicators, scoringResult);
}

export async function buildAiSummary() {
  return {
    implemented: false,
    didNetworkRequest: false,
    text: "AI要約は未実装です。将来利用する場合も、OpenAI / Claude APIはブラウザから直接呼ばずバックエンド経由にします。"
  };
}

export async function buildOptionalAiSummary() {
  return buildAiSummary();
}
