import { escapeHtml } from "./formatters.js";

export function CompactStatusBar(status = {}) {
  const items = [
    ["接続状態", status.ok ? "OK" : status.checked ? "エラー" : "未確認"],
    ["J-Quants", status.jquantsEnabled ? "有効" : "無効"],
    ["実データ", status.useRealStocks ? "ON" : "OFF"],
    ["財務", status.useFinancials ? "ON" : "OFF"],
    ["AI", "モック"],
    ["テーマ", "モック"]
  ];

  return `
    <section class="compact-status-bar">
      ${items.map(([label, value]) => `
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")}
    </section>
  `;
}
