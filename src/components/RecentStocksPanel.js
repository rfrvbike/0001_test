import { escapeHtml } from "./formatters.js";

export function RecentStocksPanel({ recentStocks = [], currentCode = "" } = {}) {
  const list = Array.isArray(recentStocks) ? recentStocks.slice(0, 10) : [];
  return `
    <section class="recent-panel">
      <div class="recent-head">
        <div>
          <div class="panel-title">最近見た銘柄</div>
          <p>個別分析した銘柄を、このブラウザだけに軽量保存しています。</p>
        </div>
        <button id="clearRecentStocksBtn" class="recent-clear" ${list.length ? "" : "disabled"}>履歴を削除</button>
      </div>
      ${list.length ? `
        <div class="recent-list">
          ${list.map((stock) => recentButton(stock, currentCode)).join("")}
        </div>
      ` : `
        <div class="recent-empty">最近見た銘柄はまだありません。分析するとここに表示されます。</div>
      `}
    </section>
  `;
}

function recentButton(stock, currentCode) {
  const active = stock.code === currentCode ? "active" : "";
  const label = `${stock.code} ${stock.name || "銘柄名未取得"}`;
  const meta = [stock.market, stock.sector].filter(Boolean).join(" / ");
  return `
    <div class="recent-chip ${active}">
      <button type="button" data-recent-analyze="${escapeHtml(stock.code)}">
        <span>${escapeHtml(label)}</span>
        ${meta ? `<small>${escapeHtml(meta)}</small>` : ""}
      </button>
      <button type="button" class="recent-remove" data-recent-remove="${escapeHtml(stock.code)}" title="履歴から削除">×</button>
    </div>
  `;
}
