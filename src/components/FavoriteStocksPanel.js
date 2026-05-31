import { escapeHtml } from "./formatters.js";

export function FavoriteStocksPanel({
  favorites = [],
  currentCode = "",
  currentIsFavorite = false
} = {}) {
  const list = Array.isArray(favorites) ? favorites : [];
  return `
    <section class="favorite-panel">
      <div class="favorite-head">
        <div>
          <div class="panel-title">お気に入り銘柄</div>
          <p>よく見る銘柄をこのブラウザだけに保存します。</p>
        </div>
        <button id="favoriteCurrentBtn" class="favorite-add ${currentIsFavorite ? "saved" : ""}">
          ${currentIsFavorite ? "★ お気に入り済み" : "☆ お気に入り追加"}
        </button>
      </div>
      ${list.length ? `
        <div class="favorite-list">
          ${list.slice(0, 50).map((favorite) => favoriteButton(favorite, currentCode)).join("")}
        </div>
      ` : `
        <div class="favorite-empty">
          お気に入り銘柄はまだありません。分析結果から「お気に入り追加」を押すとここに表示されます。
        </div>
      `}
    </section>
  `;
}

function favoriteButton(favorite, currentCode) {
  const active = favorite.code === currentCode ? "active" : "";
  const label = `${favorite.code} ${favorite.name || "銘柄名未取得"}`;
  const meta = [favorite.market, favorite.sector].filter(Boolean).join(" / ");
  return `
    <div class="favorite-chip ${active}">
      <button type="button" data-favorite-analyze="${escapeHtml(favorite.code)}">
        <span>★ ${escapeHtml(label)}</span>
        ${meta ? `<small>${escapeHtml(meta)}</small>` : ""}
      </button>
      <button type="button" class="favorite-remove" data-favorite-remove="${escapeHtml(favorite.code)}" title="お気に入りから削除">×</button>
    </div>
  `;
}
