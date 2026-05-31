import { escapeHtml } from "./formatters.js";

export function StockSearchSuggestions({
  query = "",
  candidates = [],
  message = "",
  maxVisible = 10
} = {}) {
  const trimmed = String(query || "").trim();
  const list = Array.isArray(candidates) ? candidates.slice(0, maxVisible) : [];
  if (!trimmed) return "";

  return `
    <div class="stock-search-suggestions">
      <div class="suggestions-head">
        <span>会社名候補</span>
        <small>${escapeHtml(message || "候補をクリックすると、その銘柄を分析します。外部検索APIは未接続です。")}</small>
      </div>
      ${list.length ? `
        <div class="suggestion-list">
          ${list.map(candidateButton).join("")}
        </div>
        ${Array.isArray(candidates) && candidates.length > maxVisible
          ? `<div class="suggestion-more">候補が多いため上位${maxVisible}件のみ表示しています。会社名をもう少し絞り込んでください。</div>`
          : ""}
      ` : `
        <div class="suggestion-empty">
          候補が見つかりません。現在はローカル銘柄マスター、お気に入り、監視リスト、CSV内の銘柄だけ検索できます。
        </div>
      `}
    </div>
  `;
}

function candidateButton(candidate) {
  const meta = [candidate.market, candidate.sector].filter(Boolean).join(" / ");
  return `
    <button type="button" class="suggestion-card" data-search-candidate="${escapeHtml(candidate.code)}">
      <span class="suggestion-main">
        <strong>${escapeHtml(candidate.code)} ${escapeHtml(candidate.name || "銘柄名未取得")}</strong>
        ${meta ? `<small>${escapeHtml(meta)}</small>` : ""}
      </span>
      <span class="suggestion-badges">
        ${sourceBadges(candidate).join("")}
      </span>
    </button>
  `;
}

function sourceBadges(candidate) {
  const badges = [];
  if (candidate.isFavorite) badges.push(`<span class="mini-source favorite">お気に入り</span>`);
  if (candidate.isRecent) badges.push(`<span class="mini-source recent">最近見た</span>`);
  if (candidate.isWatchlist) badges.push(`<span class="mini-source watch">監視中</span>`);
  if (candidate.isCsvMaster) badges.push(`<span class="mini-source csv-master">CSV_MASTER</span>`);
  if (candidate.isCsv) badges.push(`<span class="mini-source csv">CSV</span>`);
  (candidate.sources || []).forEach((source) => {
    if (["FAVORITE", "RECENT", "WATCHLIST", "CSV_MASTER", "CSV"].includes(source)) return;
    badges.push(`<span class="mini-source">${escapeHtml(source)}</span>`);
  });
  return badges;
}
