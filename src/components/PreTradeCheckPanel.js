import { escapeHtml } from "./formatters.js";

export function PreTradeCheckPanel(preTradeCheck, options = {}) {
  if (!preTradeCheck) return "";
  const checkedIds = new Set(options.checkedItemIds || []);
  const checklist = Array.isArray(preTradeCheck.checklist) ? preTradeCheck.checklist : [];
  const compact = Boolean(options.compact);
  const statusClass = statusToClass(preTradeCheck.riskLevel || preTradeCheck.overallStatus);
  const checklistHtml = checklist.map((item) => checklistItem(item, checkedIds, options.code)).join("");
  return `
    <section class="panel pretrade-panel ${compact ? "compact-pretrade" : ""}">
      <div class="panel-title">実売買前チェック</div>
      <div class="pretrade-status ${statusClass}">
        <span>ステータス</span>
        <strong>${escapeHtml(preTradeCheck.overallStatus || "確認不足あり")}</strong>
      </div>
      <p class="pretrade-summary">${escapeHtml(preTradeCheck.summary || "実売買前に公式情報を確認してください。")}</p>
      <div class="pretrade-mini-grid">
        ${checkBlock("株価データ", preTradeCheck.dataSource)}
        ${checkBlock("データ鮮度", preTradeCheck.freshness)}
        ${checkBlock("財務", preTradeCheck.financial)}
        ${checkBlock("ニュース/TDnet", preTradeCheck.newsAndDisclosure)}
        ${checkBlock("リスク", preTradeCheck.risk)}
      </div>
      <div class="pretrade-note">
        この欄は売買判断ではなく、実売買前に確認すべき項目のチェックリストです。
      </div>
      <details class="pretrade-details">
        <summary>詳細チェックを開く</summary>
        <div class="pretrade-checklist">${checklistHtml}</div>
        ${warnings(preTradeCheck.warnings)}
      </details>
    </section>
  `;
}

function checkBlock(label, check) {
  if (!check) return "";
  return `
    <div class="pretrade-check-block ${statusToClass(check.status)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(statusLabel(check.status))}</strong>
      <small>${escapeHtml(check.message || check.label || "")}</small>
    </div>
  `;
}

function checklistItem(item, checkedIds, code) {
  const checked = checkedIds.has(item.id) ? "checked" : "";
  return `
    <label class="pretrade-check-item">
      <input
        type="checkbox"
        data-pretrade-check="${escapeHtml(item.id)}"
        data-pretrade-code="${escapeHtml(code || "")}"
        ${checked}
      />
      <span>${escapeHtml(item.label)}</span>
      ${item.required ? `<small>必須確認</small>` : ""}
    </label>
  `;
}

function warnings(items) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return "";
  return `
    <div class="pretrade-warnings">
      ${list.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}
    </div>
  `;
}

function statusLabel(status) {
  if (status === "ok") return "確認済み";
  if (status === "danger") return "実売買不可";
  if (status === "not_connected") return "未接続";
  if (status === "warning") return "要確認";
  return "参考情報";
}

function statusToClass(status) {
  const text = String(status || "").toLowerCase();
  if (text.includes("danger") || text.includes("不可") || text.includes("mock")) return "danger";
  if (text.includes("ok") || text.includes("low")) return "ok";
  return "warning";
}
