import { escapeHtml } from "./formatters.js";

export function BulkAnalysisFilters(filters) {
  return `
    <div class="bulk-controls">
      <label>検索
        <input id="bulkSearch" value="${escapeHtml(filters.search || "")}" placeholder="7203 または トヨタ" />
      </label>
      <label>並び替え
        <select id="bulkSort">
          ${option("buyScoreDesc", "買いスコア 高い順", filters.sortKey)}
          ${option("buyScoreAsc", "買いスコア 低い順", filters.sortKey)}
          ${option("totalScoreDesc", "総合スコア 高い順", filters.sortKey)}
          ${option("totalScoreAsc", "総合スコア 低い順", filters.sortKey)}
          ${option("overheatRiskDesc", "過熱リスク 高い順", filters.sortKey)}
          ${option("rsiDesc", "RSI 高い順", filters.sortKey)}
          ${option("rsiAsc", "RSI 低い順", filters.sortKey)}
          ${option("ma25DeviationDesc", "25日線乖離率 高い順", filters.sortKey)}
          ${option("volumeRatioDesc", "出来高倍率 高い順", filters.sortKey)}
          ${option("near52wDesc", "52週高値に近い順", filters.sortKey)}
          ${option("codeAsc", "銘柄コード順", filters.sortKey)}
          ${option("nameAsc", "銘柄名順", filters.sortKey)}
        </select>
      </label>
      <label>判定
        <select id="bulkSignal">
          ${["ALL", "買い候補", "分割買い候補", "押し目待ち", "高値掴み注意", "様子見", "見送り", "利確候補", "損切り警戒"].map((value) => option(value, value === "ALL" ? "すべて" : value, filters.signal)).join("")}
        </select>
      </label>
      <label>過熱
        <select id="bulkRisk">
          ${["ALL", "LOW", "MEDIUM", "HIGH"].map((value) => option(value, value === "ALL" ? "すべて" : value, filters.risk)).join("")}
        </select>
      </label>
      <label>材料
        <select id="bulkMaterial">
          ${option("ALL", "すべて", filters.material)}
          ${option("upwardRevision", "上方修正あり", filters.material)}
          ${option("downwardRevision", "下方修正あり", filters.material)}
          ${option("dividendIncrease", "増配あり", filters.material)}
          ${option("buyback", "自社株買いあり", filters.material)}
          ${option("beforeEarnings", "決算前", filters.material)}
          ${option("policyTheme", "国策テーマあり", filters.material)}
          ${option("csvOnly", "CSV取込のみ", filters.material)}
          ${option("mockOnly", "モックデータのみ", filters.material)}
        </select>
      </label>
    </div>
  `;
}

function option(value, label, current) {
  return `<option value="${value}" ${value === current ? "selected" : ""}>${label}</option>`;
}
