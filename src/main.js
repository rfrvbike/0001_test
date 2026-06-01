const root = document.getElementById("app");

if (root) {
  root.innerHTML = `
    <main class="app-shell app-booting">
      <section class="notice-card">
        <strong>株分析ダッシュボードを読み込み中です</strong>
      </section>
    </main>
  `;
}

try {
  if (!root) {
    throw new Error("Mount target #app was not found.");
  }
  const { mountStockAnalyzer } = await import("./components/StockAnalyzer.js?v=theme-summary-20260531");
  mountStockAnalyzer(root);
  root.dataset.appMounted = "true";
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error("[stock-analyzer] mount failed", error);
  if (root) {
    root.dataset.appMounted = "false";
    root.innerHTML = `
      <main class="app-shell">
        <section class="notice-card danger">
          <strong>画面の初期化に失敗しました</strong>
          <p>ブラウザを再読み込みしてください。解消しない場合はConsole errorを確認してください。</p>
          <p class="mono-text">${escapeHtml(message)}</p>
        </section>
      </main>
    `;
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}
