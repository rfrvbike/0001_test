import {
  formatSimulationSummaryPercent,
  summarizeSimulationRecordsByDecision,
  summarizeSimulationRecordsByMonth,
  summarizeSimulationRecordsByStock
} from "../services/simulationRecordsService.js";
import { escapeHtml } from "./formatters.js";

const MODE_LABELS = {
  month: "月別",
  stock: "銘柄別",
  decision: "判断別"
};

export function SimulationSummaryPanel({
  records = [],
  filteredRecords = [],
  summaryMode = "month",
  summaryScope = "filtered"
} = {}) {
  const safeRecords = Array.isArray(records) ? records : [];
  const safeFilteredRecords = Array.isArray(filteredRecords) ? filteredRecords : [];
  const targetRecords = summaryScope === "all" ? safeRecords : safeFilteredRecords;
  const rows = buildRows(targetRecords, summaryMode);
  return `
    <section class="simulation-group-summary">
      <div class="simulation-group-summary-head">
        <div>
          <strong>検証サマリー</strong>
          <p class="simulation-record-note">これは実売買損益ではなく、仮記録の参考差分集計です。</p>
        </div>
        <div class="simulation-group-controls">
          <label>
            表示対象
            <select id="simulationSummaryScope" ${safeRecords.length ? "" : "disabled"}>
              ${option("filtered", "表示中の記録", summaryScope)}
              ${option("all", "全件", summaryScope)}
            </select>
          </label>
          <label>
            集計単位
            <select id="simulationSummaryMode" ${safeRecords.length ? "" : "disabled"}>
              ${option("month", "月別", summaryMode)}
              ${option("stock", "銘柄別", summaryMode)}
              ${option("decision", "判断別", summaryMode)}
            </select>
          </label>
        </div>
      </div>
      ${rows.length ? summaryRows(rows, summaryMode) : emptyMessage(safeRecords.length, summaryScope)}
    </section>
  `;
}

function buildRows(records, mode) {
  if (mode === "stock") return summarizeSimulationRecordsByStock(records);
  if (mode === "decision") return summarizeSimulationRecordsByDecision(records);
  return summarizeSimulationRecordsByMonth(records);
}

function summaryRows(rows, mode) {
  return `
    <div class="simulation-group-summary-list" aria-label="${escapeHtml(MODE_LABELS[mode] || "月別")}検証サマリー">
      ${rows.map(summaryRow).join("")}
    </div>
  `;
}

function summaryRow(row) {
  return `
    <article class="simulation-group-summary-row">
      <div>
        <strong>${escapeHtml(row.label)}</strong>
        ${row.sampleCodes?.length ? `<span>${escapeHtml(row.sampleCodes.join(" / "))}</span>` : ""}
      </div>
      <div class="simulation-summary-grid compact">
        <span>記録数：${row.count}</span>
        <span>プラス：${row.positiveCount}</span>
        <span>マイナス：${row.negativeCount}</span>
        <span>変化なし：${row.flatCount}</span>
        <span>未確認：${row.uncheckedCount}</span>
        <span>平均参考変化率：${formatSimulationSummaryPercent(row.averageChangePercent)}</span>
        <span>最大プラス：${formatSimulationSummaryPercent(row.maxPositiveChangePercent)}</span>
        <span>最大マイナス：${formatSimulationSummaryPercent(row.maxNegativeChangePercent)}</span>
      </div>
    </article>
  `;
}

function emptyMessage(totalCount, scope) {
  if (!totalCount) {
    return `<p class="simulation-record-note">集計できるシミュレーション記録はまだありません。</p>`;
  }
  if (scope === "filtered") {
    return `<p class="simulation-record-note">現在のフィルター条件に一致する記録がありません。全件集計に切り替えることもできます。</p>`;
  }
  return `<p class="simulation-record-note">集計対象の記録がありません。</p>`;
}

function option(value, label, currentValue) {
  const safeValue = escapeHtml(value);
  return `<option value="${safeValue}" ${value === currentValue ? "selected" : ""}>${escapeHtml(label)}</option>`;
}
