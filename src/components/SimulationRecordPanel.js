import { escapeHtml, signedPercent, yen } from "./formatters.js";

const STATUS_LABELS = {
  watching: "確認中",
  review_later: "後で確認",
  simulated_entry: "仮記録",
  closed: "検証済み",
  archived: "アーカイブ"
};

export function SimulationRecordPanel({
  analysis = null,
  records = [],
  filteredRecords = null,
  filters = {},
  summary = null,
  decisionLabels = [],
  message = "",
  error = "",
  variant = "list"
} = {}) {
  const safeRecords = Array.isArray(records) ? records : [];
  const safeFilteredRecords = Array.isArray(filteredRecords) ? filteredRecords : safeRecords;
  const canAdd = Boolean(analysis?.stock || analysis?.code || analysis?.name);

  return `
    <section class="simulation-record-panel ${variant === "add" ? "compact" : ""}">
      <div class="simulation-record-head">
        <div>
          <div class="panel-title">シミュレーション記録</div>
          <p class="simulation-record-note">実売買ではありません。注文は行わず、分析時点の判断を検証用に保存します。</p>
        </div>
        <span class="data-badge danger">実売買なし</span>
      </div>
      ${message ? `<div class="storage-message">${escapeHtml(message)}</div>` : ""}
      ${error ? `<div class="csv-errors"><p>${escapeHtml(error)}</p></div>` : ""}
      ${variant === "add" ? addRecordForm(canAdd) : recordList(safeRecords, safeFilteredRecords, filters, summary, decisionLabels)}
    </section>
  `;
}

function addRecordForm(canAdd) {
  return `
    <div class="simulation-record-form">
      <label for="simulationMemoInput">記録メモ</label>
      <textarea id="simulationMemoInput" class="simulation-record-textarea" rows="3" placeholder="例：RSIが高いため押し目を待つ。決算資料を確認する。"></textarea>
      <div class="simulation-record-actions">
        <button id="addSimulationRecordBtn" ${canAdd ? "" : "disabled"}>シミュレーション記録に追加</button>
      </div>
      <p class="simulation-record-warning">保存するのは軽量な検証メモだけです。APIキー、rawデータ、詳細レスポンスは保存しません。</p>
    </div>
  `;
}

function recordList(records, filteredRecords, filters, summary, decisionLabels) {
  const safeSummary = summary || buildEmptySummary(filteredRecords);
  return `
    <div class="simulation-record-list-panel">
      <div class="simulation-record-list-head">
        <span>表示件数：${filteredRecords.length} / 全体：${records.length}件</span>
        <div class="simulation-record-actions">
          <button id="exportSimulationRecordsCsvBtn" ${records.length ? "" : "disabled"}>全件CSV出力</button>
          <button id="exportFilteredSimulationRecordsCsvBtn" ${filteredRecords.length ? "" : "disabled"}>表示中のみCSV出力</button>
          <button id="clearSimulationRecordsBtn" ${records.length ? "" : "disabled"}>記録を全削除</button>
        </div>
      </div>
      ${filterControls(filters, decisionLabels, records.length)}
      ${summaryCard(safeSummary, filteredRecords.length, records.length)}
      ${records.length
        ? (filteredRecords.length
          ? `<div class="simulation-record-list">${filteredRecords.map(recordRow).join("")}</div>`
          : `<p class="simulation-record-note">条件に一致するシミュレーション記録はありません。</p>`)
        : `<p class="simulation-record-note">まだシミュレーション記録はありません。個別分析後に「シミュレーション記録に追加」から残せます。</p>`}
    </div>
  `;
}

function filterControls(filters = {}, decisionLabels = [], recordCount = 0) {
  const datePreset = filters.datePreset || "all";
  const diffStatus = filters.diffStatus || "all";
  const decisionLabel = filters.decisionLabel || "all";
  const safeLabels = Array.isArray(decisionLabels) ? decisionLabels : [];
  return `
    <div class="simulation-filter-panel">
      <div class="simulation-filter-grid">
        <label>
          期間
          <select id="simulationDatePreset" ${recordCount ? "" : "disabled"}>
            ${option("all", "すべて", datePreset)}
            ${option("today", "今日", datePreset)}
            ${option("7d", "過去7日", datePreset)}
            ${option("30d", "過去30日", datePreset)}
            ${option("custom", "日付指定", datePreset)}
          </select>
        </label>
        <label>
          開始日
          <input id="simulationDateFrom" type="date" value="${escapeHtml(filters.dateFrom || "")}" ${recordCount ? "" : "disabled"}>
        </label>
        <label>
          終了日
          <input id="simulationDateTo" type="date" value="${escapeHtml(filters.dateTo || "")}" ${recordCount ? "" : "disabled"}>
        </label>
        <label>
          銘柄検索
          <input id="simulationKeyword" type="search" placeholder="7203 / トヨタ / ソニー" value="${escapeHtml(filters.keyword || "")}" ${recordCount ? "" : "disabled"}>
        </label>
        <label>
          判断
          <select id="simulationDecisionLabel" ${recordCount ? "" : "disabled"}>
            ${option("all", "すべて", decisionLabel)}
            ${safeLabels.map((label) => option(label, label, decisionLabel)).join("")}
          </select>
        </label>
        <label>
          参考差分
          <select id="simulationDiffStatus" ${recordCount ? "" : "disabled"}>
            ${option("all", "すべて", diffStatus)}
            ${option("positive", "プラス", diffStatus)}
            ${option("negative", "マイナス", diffStatus)}
            ${option("neutral", "変化なし", diffStatus)}
            ${option("unknown", "未確認", diffStatus)}
          </select>
        </label>
      </div>
      <div class="simulation-record-actions compact-actions">
        <button id="resetSimulationFiltersBtn" ${recordCount ? "" : "disabled"}>フィルターリセット</button>
      </div>
    </div>
  `;
}

function summaryCard(summary, filteredCount, totalCount) {
  return `
    <div class="simulation-summary-card">
      <div>
        <strong>シミュレーション記録 集計</strong>
        <span>表示 ${filteredCount} / 全体 ${totalCount}件</span>
      </div>
      <div class="simulation-summary-grid">
        <span>プラス：${summary.positiveCount}件</span>
        <span>マイナス：${summary.negativeCount}件</span>
        <span>変化なし：${summary.neutralCount}件</span>
        <span>未確認：${summary.unknownCount}件</span>
        <span>平均参考変化率：${formatPercentOrUnknown(summary.averageChangePercent)}</span>
        <span>最大プラス：${formatPercentOrUnknown(summary.maxPositiveChangePercent)}</span>
        <span>最大マイナス：${formatPercentOrUnknown(summary.maxNegativeChangePercent)}</span>
      </div>
      <p class="simulation-record-warning">これは実売買損益ではなく、仮記録の検証用集計です。</p>
    </div>
  `;
}

function recordRow(record) {
  const id = escapeHtml(record.id);
  const diff = buildDisplayDiff(record);
  return `
    <article class="simulation-record-row">
      <div class="simulation-record-summary">
        <div>
          <strong>${escapeHtml(record.code)} ${escapeHtml(record.name)}</strong>
          <div class="simulation-record-meta">
            <span>${escapeHtml(formatDateTime(record.recordedAt))}</span>
            <span>${escapeHtml(record.dataSource || "-")}</span>
            <span>${escapeHtml(record.decisionLabel || "判断なし")}</span>
            <span>記録時 ${record.price === null ? "未確認" : escapeHtml(yen(record.price))}</span>
            ${record.changePercent === null ? "" : `<span>${escapeHtml(signedPercent(record.changePercent))}</span>`}
          </div>
        </div>
        <div class="simulation-score-pill">
          <span>総合 ${formatScore(record.totalScore)}</span>
          <span>買い ${formatScore(record.buyScore)}</span>
        </div>
      </div>
      <div class="simulation-record-edit">
        <label>
          状態
          <select data-simulation-status="${id}">
            ${Object.entries(STATUS_LABELS).map(([value, label]) => `<option value="${value}" ${record.status === value ? "selected" : ""}>${label}</option>`).join("")}
          </select>
        </label>
        <label>
          メモ
          <textarea class="simulation-record-textarea" rows="2" data-simulation-memo="${id}">${escapeHtml(record.memo || "")}</textarea>
        </label>
        <label>
          検証メモ
          <textarea class="simulation-record-textarea" rows="2" data-simulation-result-memo="${id}">${escapeHtml(record.resultMemo || "")}</textarea>
        </label>
      </div>
      <div class="simulation-price-check ${diff.className}">
        <span>最終確認価格：${record.lastCheckedPrice === null || record.lastCheckedPrice === undefined ? "未確認" : escapeHtml(yen(record.lastCheckedPrice))}</span>
        <span>参考差分：${escapeHtml(diff.label)}</span>
        <span>最終確認：${record.lastCheckedAt ? escapeHtml(formatDateTime(record.lastCheckedAt)) : "未確認"}</span>
        <span>データ：${escapeHtml(record.lastCheckedDataSource || "-")}</span>
      </div>
      <p class="simulation-record-warning">これは実売買損益ではなく、仮記録の検証用の参考差分です。注文は行われません。</p>
      <div class="simulation-record-actions">
        <button data-simulation-analyze="${escapeHtml(record.code)}">再分析</button>
        <button data-simulation-check="${id}" data-simulation-check-code="${escapeHtml(record.code)}">現在価格を確認</button>
        <button data-simulation-update="${id}">メモ更新</button>
        <button data-simulation-remove="${id}">削除</button>
      </div>
    </article>
  `;
}

function buildDisplayDiff(record) {
  const change = Number(record.lastCheckedChange);
  const percent = Number(record.lastCheckedChangePercent);
  if (!Number.isFinite(change) || !Number.isFinite(percent)) {
    return { label: "未計算", className: "neutral" };
  }
  const sign = change > 0 ? "+" : "";
  const className = change > 0 ? "positive" : change < 0 ? "negative" : "neutral";
  return {
    label: `${sign}${change.toLocaleString("ja-JP")}円（${sign}${percent.toFixed(2)}%）`,
    className
  };
}

function option(value, label, currentValue) {
  const safeValue = escapeHtml(value);
  return `<option value="${safeValue}" ${value === currentValue ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function buildEmptySummary(records = []) {
  return {
    totalRecords: Array.isArray(records) ? records.length : 0,
    positiveCount: 0,
    negativeCount: 0,
    neutralCount: 0,
    unknownCount: Array.isArray(records) ? records.length : 0,
    averageChangePercent: null,
    maxPositiveChangePercent: null,
    maxNegativeChangePercent: null
  };
}

function formatPercentOrUnknown(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "未計算";
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function formatScore(value) {
  return value === null || value === undefined ? "-" : String(value);
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}
