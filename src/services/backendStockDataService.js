const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8787";

export async function getBackendHealth(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(`${baseUrl}/api/health`, "ローカルバックエンドが起動していません。必要に応じて node server/index.js を実行してください。");
}

export async function getBackendJQuantsStatus(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/jquants/status`,
    "J-Quants接続状態を取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendJQuantsConnectionCheck(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/jquants/connection-check`,
    "J-Quants接続確認を実行できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendJQuantsCacheStatus(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/jquants/cache/status`,
    "J-Quantsキャッシュ状態を取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function clearBackendJQuantsCache(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/jquants/cache/clear`,
    "J-Quantsキャッシュを削除できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendStockMaster(code, baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/stocks/master/${encodeURIComponent(code)}`,
    "銘柄マスターを取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendStockMasterStatus(baseUrl = DEFAULT_BACKEND_BASE_URL) {
  return backendJson(
    `${baseUrl}/api/stocks/master/status`,
    "銘柄マスター状態を取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendJQuantsRawStockData(code, from, to, baseUrl = DEFAULT_BACKEND_BASE_URL) {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const query = params.toString() ? `?${params.toString()}` : "";
  return backendJson(
    `${baseUrl}/api/jquants/raw/${encodeURIComponent(code)}${query}`,
    "J-Quants raw確認データを取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendJQuantsMappedStockData(code, from, to, baseUrl = DEFAULT_BACKEND_BASE_URL) {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const query = params.toString() ? `?${params.toString()}` : "";
  return backendJson(
    `${baseUrl}/api/jquants/mapped/${encodeURIComponent(code)}${query}`,
    "J-Quants mapped確認データを取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendJQuantsFinancialSummary(code, optionsOrBaseUrl = DEFAULT_BACKEND_BASE_URL) {
  const options = typeof optionsOrBaseUrl === "string" ? { baseUrl: optionsOrBaseUrl } : optionsOrBaseUrl;
  const baseUrl = options.baseUrl || DEFAULT_BACKEND_BASE_URL;
  const params = new URLSearchParams();
  if (options.forceRefresh) params.set("forceRefresh", "true");
  const query = params.toString() ? `?${params.toString()}` : "";
  return backendJson(
    `${baseUrl}/api/jquants/fins/summary/${encodeURIComponent(code)}${query}`,
    "J-Quants財務サマリーを取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

export async function getBackendStockData(code, optionsOrBaseUrl = DEFAULT_BACKEND_BASE_URL) {
  const options = typeof optionsOrBaseUrl === "string" ? { baseUrl: optionsOrBaseUrl } : optionsOrBaseUrl;
  const baseUrl = options.baseUrl || DEFAULT_BACKEND_BASE_URL;
  const encodedCode = encodeURIComponent(code);
  const params = new URLSearchParams();
  if (options.forceRefresh) params.set("forceRefresh", "true");
  const query = params.toString() ? `?${params.toString()}` : "";
  const result = await backendJson(
    `${baseUrl}/api/stocks/${encodedCode}${query}`,
    "バックエンドの銘柄データを取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
  if (!result.ok) return result;
  return result.data ?? result;
}

export async function getBackendStocks(codes = [], baseUrl = DEFAULT_BACKEND_BASE_URL) {
  const query = codes.length ? `?codes=${encodeURIComponent(codes.join(","))}` : "";
  return backendJson(
    `${baseUrl}/api/stocks${query}`,
    "バックエンドの銘柄一覧を取得できませんでした。ローカルバックエンドの起動状態を確認してください。"
  );
}

async function backendJson(url, offlineMessage) {
  try {
    assertLocalBackendUrl(url);
    const response = await fetch(url, { headers: { accept: "application/json" } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      return {
        ...body,
        ok: false,
        status: response.status,
        error: body.error || `バックエンドAPIがエラーを返しました: ${response.status}`,
        missingFields: body.missingFields || [],
        mode: body.mode || "error",
        didNetworkRequest: Boolean(body.didNetworkRequest),
        didExternalRequest: false
      };
    }
    return { ...body, didExternalRequest: false };
  } catch (error) {
    return {
      ok: false,
      error: offlineMessage,
      detail: error.message,
      didExternalRequest: false
    };
  }
}

function assertLocalBackendUrl(url) {
  const parsed = new URL(url);
  const allowedHosts = new Set(["127.0.0.1", "localhost"]);
  if (!allowedHosts.has(parsed.hostname)) {
    throw new Error("Only local backend URLs are allowed.");
  }
}
