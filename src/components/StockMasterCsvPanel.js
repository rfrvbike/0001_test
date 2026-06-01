import { escapeHtml } from "./formatters.js";

export function StockMasterCsvPanel({
  rows = [],
  meta = null,
  result = null,
  dryRunResult = null,
  message = "",
  error = ""
} = {}) {
  const count = Array.isArray(rows) ? rows.length : 0;
  const stats = result?.stats || {};
  const encoding = result?.encoding || meta || {};
  const source = meta?.source || "CSV_IMPORT";
  const currentSource = meta?.lastSyncSource || source;
  const lastSyncCount = Number(meta?.lastSyncCount ?? count);
  const lastSyncAt = meta?.lastSyncAt || meta?.importedAt || "";
  const mojibakeWarning = Boolean(encoding.mojibakeSuspected);
  return `
    <section class="csv-panel stock-master-csv-panel">
      <div class="panel-title">銘柄マスターCSV</div>
      <p class="csv-help">
        会社名検索用のCSVです。分析用CSVとは別管理で、株価やスコアには使いません。
        対応形式: code, name, market, sector
      </p>
      <p class="csv-help">UTF-8 / Shift_JIS（CP932）に対応します。迷う場合は「自動判定」を選んでください。</p>
      <div class="csv-actions encoding-actions">
        <label class="mini-field">
          <span>文字コード</span>
          <select id="stockMasterCsvEncoding">
            <option value="auto">自動判定</option>
            <option value="utf-8">UTF-8</option>
            <option value="shift-jis">Shift_JIS / CP932</option>
          </select>
        </label>
        <button id="downloadStockMasterTemplateBtn" type="button">テンプレートCSVをダウンロード</button>
      </div>
      <div class="csv-actions">
        <label class="file-button"><input id="stockMasterCsvFile" type="file" accept=".csv,text/csv" />CSVを選択</label>
        <button id="fetchJquantsMasterMockBtn" type="button">J-Quants銘柄マスター取得（Mock）</button>
        <button id="dryRunJquantsMasterBtn" type="button">J-Quants取得 Dry-run</button>
        <button id="clearStockMasterCsvBtn" ${count ? "" : "disabled"}>保存済み銘柄マスターを削除</button>
      </div>
      <div class="storage-grid compact-storage-grid">
        <div><span>Current Source</span><strong>${escapeHtml(currentSource)}</strong></div>
        <div><span>Last Sync Count</span><strong>${lastSyncCount}莉ｶ</strong></div>
        <div><span>保存済み</span><strong>${count}件</strong></div>
        <div><span>取得元</span><strong>${escapeHtml(source)}</strong></div>
        <div><span>銘柄数</span><strong>${count}件</strong></div>
        <div><span>用途</span><strong>会社名検索候補</strong></div>
        <div><span>選択文字コード</span><strong>${escapeHtml(displayEncoding(encoding.selectedEncoding))}</strong></div>
        <div><span>判定文字コード</span><strong>${escapeHtml(displayEncoding(encoding.detectedEncoding))}</strong></div>
        <div><span>文字化け疑い</span><strong>${mojibakeWarning ? "あり" : "なし"}</strong></div>
      </div>
      ${meta?.importedAt ? `<div class="csv-help">最終保存: ${escapeHtml(formatMetaDate(meta.importedAt))}</div>` : ""}
      ${lastSyncAt ? `<div class="csv-help">Last Sync: ${escapeHtml(formatMetaDate(lastSyncAt))}</div>` : ""}
      ${message ? `<div class="storage-message">${escapeHtml(message)}</div>` : ""}
      ${dryRunResult ? dryRunBlock(dryRunResult) : ""}
      ${encoding.decodeWarning ? `<div class="csv-warning">${escapeHtml(encoding.decodeWarning)}</div>` : ""}
      ${mojibakeWarning ? `<div class="csv-warning">文字化けの可能性があります。文字コードを切り替えるか、テンプレートCSVをUTF-8で利用してください。</div>` : ""}
      ${error ? `<div class="csv-errors"><strong>銘柄マスターCSVエラー</strong><p>${escapeHtml(error)}</p></div>` : ""}
      ${result ? importResult(result) : ""}
      ${count ? `
        <div class="csv-help">検索候補にCSV_MASTERとして追加されます。保存内容はcode/name/market/sector/source/importedAtのみです。</div>
        <div class="stock-master-preview">
          ${rows.slice(0, 8).map(previewRow).join("")}
          ${count > 8 ? `<div class="suggestion-more">ほか ${count - 8}件</div>` : ""}
        </div>
      ` : `<div class="csv-help">保存済み銘柄マスターCSVはありません。</div>`}
    </section>
  `;
}

function importResult(result) {
  const stats = result.stats || {};
  const errors = Array.isArray(result.errors) ? result.errors : [];
  return `
    <div class="storage-grid compact-storage-grid">
      <div><span>読み込み</span><strong>${stats.readCount ?? 0}件</strong></div>
      <div><span>有効</span><strong>${stats.validCount ?? 0}件</strong></div>
      <div><span>除外</span><strong>${stats.excludedCount ?? 0}件</strong></div>
      <div><span>重複統合</span><strong>${stats.duplicateCount ?? 0}件</strong></div>
      <div><span>保存済み</span><strong>${stats.storedCount ?? 0}件</strong></div>
    </div>
    ${errors.length ? `<div class="csv-errors">${errors.slice(0, 8).map((error) => `<p>${escapeHtml(error)}</p>`).join("")}</div>` : ""}
  `;
}

function dryRunBlock(result) {
  const rows = Array.isArray(result.sampleRows) ? result.sampleRows : [];
  return `
    <div class="dry-run-result">
      <div class="panel-title">J-Quants取得 Dry-run結果</div>
      <div class="storage-grid compact-storage-grid">
        <div><span>取得件数</span><strong>${Number(result.fetchedCount || 0)}件</strong></div>
        <div><span>CSV件数</span><strong>${Number(result.csvCount || 0)}件</strong></div>
        <div><span>取得元</span><strong>${escapeHtml(result.source || "JQUANTS_MOCK")}</strong></div>
        <div><span>実API接続</span><strong>なし</strong></div>
      </div>
      <div class="stock-master-preview">
        ${rows.map(previewRow).join("")}
      </div>
    </div>
  `;
}

function previewRow(row) {
  const meta = [row.market, row.sector].filter(Boolean).join(" / ");
  return `
    <div class="csv-stock-row">
      <span>${escapeHtml(row.code)} ${escapeHtml(row.name)}</span>
      <span>${meta ? escapeHtml(meta) : "市場・業種未取得"}</span>
      <span><span class="mini-source csv-master">${escapeHtml(row.source || "CSV_MASTER")}</span></span>
    </div>
  `;
}

function displayEncoding(value) {
  const text = String(value || "");
  if (text === "utf-8") return "UTF-8";
  if (text === "shift-jis") return "Shift_JIS / CP932";
  if (text === "auto") return "自動判定";
  if (text === "text" || text === "unknown") return "未判定";
  return text || "未判定";
}

function formatMetaDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ja-JP");
}
