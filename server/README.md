# Stock Analyzer Backend

Local backend scaffold for the Japanese stock analyzer dashboard.

J-Quants V2 uses an API key issued from the J-Quants dashboard. The key is intended to be sent by the backend with the `x-api-key` header in a future step. This repository does not put the API key in browser JavaScript, localStorage, or API responses.

## Current Behavior

- `JQUANTS_ENABLED=false` is the default.
- When `JQUANTS_ENABLED=false`, mock mode is active and no external request is made.
- When `JQUANTS_ENABLED=true`, the backend checks whether `JQUANTS_API_KEY` is configured.
- When the API key exists, mode becomes `api_key_ready`.
- `JQUANTS_USE_REAL_STOCKS=true` allows `/api/stocks/:code` to fetch J-Quants daily bars.
- `JQUANTS_USE_FINANCIALS=true` additionally merges a lightweight financial summary into `/api/stocks/:code`.
- Financial summaries are display-only in this step and are not strongly reflected in scoring.
- `/api/jquants/connection-check`, raw/mapped checks, real-stock mode, and financial summary endpoints can call J-Quants only when enabled and configured.
- The connection check calls only a lightweight V2 normal API endpoint and does not fetch stock analysis data.
- API responses never include the API key value.
- `server/.env` is ignored by Git.
- `server/.env.example` contains only empty sample values.
- The frontend calls only this local backend, not J-Quants directly.
- Free plans and paid plans may differ in available data and rate limits.
- This tool is not investment advice and connection success does not mean the data is tradable or suitable for live decisions.

## Environment

Copy `server/.env.example` to `server/.env` only on your local machine when you are ready to configure credentials.

```text
JQUANTS_ENABLED=false
JQUANTS_API_VERSION=v2
JQUANTS_API_KEY=
JQUANTS_API_BASE_URL=https://api.jquants.com
JQUANTS_USE_REAL_STOCKS=false
JQUANTS_REAL_STOCK_FROM=2025-09-01
JQUANTS_REAL_STOCK_TO=2026-01-31
JQUANTS_FALLBACK_TO_MOCK=true
JQUANTS_CACHE_ENABLED=true
JQUANTS_CACHE_TTL_MS=300000
JQUANTS_MIN_REQUEST_INTERVAL_MS=1000
JQUANTS_MAX_REQUESTS_PER_MINUTE=20
JQUANTS_USE_FINANCIALS=false
JQUANTS_FINANCIALS_FALLBACK_SILENT=true
JQUANTS_USE_FINANCIAL_SCORE=true
SERVER_HOST=127.0.0.1
SERVER_PORT=8787
EXTERNAL_API_TIMEOUT_MS=10000

# Legacy V1 token auth. Do not use for new V2 accounts.
# JQUANTS_EMAIL=
# JQUANTS_PASSWORD=
# JQUANTS_REFRESH_TOKEN=
# JQUANTS_USE_REFRESH_TOKEN=false
```

Do not commit `server/.env`.

## Start

```powershell
cd C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test
node server/index.js
```

or:

```powershell
npm run start:server
```

## Test

Normally, run the stock analyzer test from the repository root:

```powershell
npm test
```

If `npm` is not available on `PATH`, run the same test script directly with Node:

```powershell
node tests/stock-analyzer.test.js
```

In environments such as Codex where a dedicated Node executable path is available,
use that executable to run the same JavaScript test file:

```powershell
<path-to-node.exe> tests/stock-analyzer.test.js
```

This test suite uses mock/stubbed responses for external data paths and must not
connect to the real J-Quants API.

## URLs

```text
http://127.0.0.1:8787/api/health
http://127.0.0.1:8787/api/jquants/status
http://127.0.0.1:8787/api/jquants/connection-check
http://127.0.0.1:8787/api/jquants/raw/7203?from=2026-01-01&to=2026-01-31
http://127.0.0.1:8787/api/jquants/mapped/7203?from=2026-01-01&to=2026-01-31
http://127.0.0.1:8787/api/stocks/7203
http://127.0.0.1:8787/api/stocks?codes=7203,6758,8035
```

## Status Modes

- `mock`: J-Quants disabled, mock data only, no external request.
- `config_error`: J-Quants enabled but `JQUANTS_API_KEY` is missing.
- `api_key_ready`: API key exists. Real stock and financial fetches are controlled separately by `JQUANTS_USE_REAL_STOCKS` and `JQUANTS_USE_FINANCIALS`.
- `real_stock_ok`: `/api/stocks/:code` returned mapped J-Quants daily bars.
- `fins_summary_ok`: J-Quants financial summary was fetched and sanitized.
- `connection_ok`: `/api/jquants/connection-check` reached J-Quants successfully.
- `connection_error`: `/api/jquants/connection-check` made the request but J-Quants or the network returned an error.

`/api/jquants/status` and `/api/health` keep `didNetworkRequest: false`. `/api/stocks/:code` returns `didNetworkRequest: true` only when real-stock mode or financial integration makes an actual backend J-Quants request.

## Connection Check

`/api/jquants/connection-check` uses:

```text
GET https://api.jquants.com/v2/markets/calendar
```

The API key is sent only from the backend using the `x-api-key` header. The response is summarized and the body is not passed through to the frontend. This endpoint is for connectivity only:

- It does not fetch stock prices for analysis.
- It does not fetch financial statements.
- It does not change `/api/stocks/:code`; that endpoint still returns mock data.
- It never returns request headers or the API key.
- If J-Quants returns 403, the backend reports that communication reached J-Quants but the endpoint may be unavailable for the current plan or permissions.

## Raw Daily Bars Check

`/api/jquants/raw/:code` fetches one issue from the J-Quants V2 daily OHLC endpoint for structure checking only.

```text
GET https://api.jquants.com/v2/equities/bars/daily?code=7203&from=2026-01-01&to=2026-01-31
```

Example:

```text
http://127.0.0.1:8787/api/jquants/raw/7203?from=2026-01-01&to=2026-01-31
```

This endpoint:

- Uses the API key only inside the backend with the `x-api-key` header.
- Does not pass through the full J-Quants response.
- Returns only `rowCount`, `columns`, and up to 3 `sampleRows`.
- Does not feed data into scoring, watchlists, CSV analysis, or `/api/stocks/:code`.
- Is not investment advice and must not be used as tradable data.

Common error hints:

- `400`: code/date parameters may be invalid.
- `401`: API key may be invalid.
- `403`: endpoint permission or plan may be insufficient.
- `429`: rate limit may have been exceeded.

## Mapped Daily Bars Check

`/api/jquants/mapped/:code` fetches the same raw daily OHLC data, then maps it into the dashboard's internal `stockData` shape for structure checking only.

Example:

```text
http://127.0.0.1:8787/api/jquants/mapped/7203?from=2026-01-01&to=2026-01-31
```

This endpoint:

- Is still a structure-check endpoint. `/api/stocks/:code` can use the same mapper only when the real stock switch is enabled.
- Does not feed data into scoring, watchlists, CSV analysis, or bulk analysis.
- Returns `stockData` with `dataSource: J_QUANTS_MAPPED`.
- Keeps `isTradableData: false` and `tradableDataLabel: J-Quants実データ確認用`.
- Calculates `price`, `previousClose`, `change`, `changePercent`, and `volume` when enough rows exist.
- Calculates `averageVolume20d`, `ma25`, `ma75`, and `rsi` only when enough data exists.
- Returns `null` and `calculationWarnings` when the requested period is too short.
- Does not pass through the full raw response.

## `/api/stocks/:code` Real Stock Switch

`JQUANTS_USE_REAL_STOCKS=false` is the default. In this mode, `/api/stocks/:code` keeps returning `J_QUANTS_MOCK` with `didNetworkRequest: false`.

When all of the following are true, `/api/stocks/:code` tries to fetch one symbol from J-Quants and map it into `stockData`:

- `JQUANTS_ENABLED=true`
- `JQUANTS_API_KEY` is present
- `JQUANTS_USE_REAL_STOCKS=true`

Date range:

- `JQUANTS_REAL_STOCK_FROM=2025-09-01`
- `JQUANTS_REAL_STOCK_TO=2026-01-31`

Fallback:

- `JQUANTS_FALLBACK_TO_MOCK=true` returns mock data if J-Quants fetch fails.
- Fallback responses include `fallbackUsed`, `fallbackReason`, and a safe `jquantsErrorSummary`.
- `JQUANTS_FALLBACK_TO_MOCK=false` returns an error instead of mock fallback.

The real stock response still uses `isTradableData: false` and `tradableDataLabel: J-Quants実データ・要確認`. Financial data, earnings, TDnet, and policy themes are still not connected. Bulk analysis does not perform multi-symbol J-Quants fetching in this step.

Example:

```text
http://127.0.0.1:8787/api/stocks/7203
```

## Local Stock Master

The backend has a small local stock master for common symbols. It fills `name`, `market`, and `sector` after J-Quants daily bars are mapped into `stockData`.

Currently included examples:

- `7203`: トヨタ自動車 / プライム / 輸送用機器
- `6758`: ソニーグループ / プライム / 電気機器
- `8035`: 東京エレクトロン / プライム / 電気機器
- `9984`: ソフトバンクグループ / プライム / 情報・通信業
- `6861`: キーエンス / プライム / 電気機器
- `6098`: リクルートホールディングス / プライム / サービス業

Endpoints:

```text
http://127.0.0.1:8787/api/stocks/master/7203
http://127.0.0.1:8787/api/stocks/master/status
```

Notes:

- `/api/stocks/:code` caches stock data after local master enrichment, so cache hits keep `name`, `market`, `sector`, and `stockMasterSource`.
- CSV names remain user-provided data. If CSV input already includes a name, it should not be overwritten by the local master.
- J-Quants listed-info / stock-master fetching is intentionally not implemented in this step because it can become a large request. The placeholder returns `didNetworkRequest:false`.
- Financials, earnings, TDnet, and AI summaries remain unconnected.
- This dashboard is not investment advice.

## J-Quants Cache And Rate Control

J-Quants real stock fetches use an in-memory backend cache. The cache is process-local and disappears when `node server/index.js` is restarted.

Environment variables:

```text
JQUANTS_CACHE_ENABLED=true
JQUANTS_CACHE_TTL_MS=300000
JQUANTS_MIN_REQUEST_INTERVAL_MS=1000
JQUANTS_MAX_REQUESTS_PER_MINUTE=20
```

Behavior:

- Same `code`, `from`, `to`, endpoint, and mode returns the cached result while it is valid.
- First fetch: `didNetworkRequest:true`, `cacheHit:false`, `cacheStored:true`.
- Cache hit: `didNetworkRequest:false`, `cacheHit:true`.
- `forceRefresh=true` skips the cache but still obeys rate control.
- Rate-limited requests return a safe error or mock fallback depending on `JQUANTS_FALLBACK_TO_MOCK`.
- API keys, request headers, full raw responses, and raw rows are not returned by cache APIs.

Examples:

```text
http://127.0.0.1:8787/api/stocks/7203
http://127.0.0.1:8787/api/stocks/7203?forceRefresh=true
http://127.0.0.1:8787/api/jquants/cache/status
http://127.0.0.1:8787/api/jquants/cache/clear
```

`/api/jquants/cache/status` returns only safe metadata such as cache keys, saved times, expiry times, and rate-limit counters. It does not return `stockData`, raw J-Quants data, API keys, or headers.

Bulk analysis still does not perform multi-symbol J-Quants fetching. It continues to use CSV, saved CSV, or mock data to avoid unexpected traffic and free-plan rate-limit issues.

Free plans may have data delay, date-range limits, endpoint limits, and rate limits. This dashboard is not investment advice, and J-Quants daily-bar data alone should not be used as a final trading decision.

## Financial Summary Check

`/api/jquants/fins/summary/:code` fetches one symbol from the J-Quants V2 financial summary endpoint for structure checking only.

Endpoint used by the backend:

```text
GET https://api.jquants.com/v2/fins/summary?code=7203
```

Examples:

```text
http://127.0.0.1:8787/api/jquants/fins/summary/7203
http://127.0.0.1:8787/api/jquants/fins/summary/7203?forceRefresh=true
```

This endpoint:

- Uses the API key only inside the backend with the `x-api-key` header.
- Returns a sanitized summary only.
- Returns `rowCount`, `columnsCount`, `importantColumns`, up to 3 lightweight `sampleRows`, and `latestDisclosure`.
- Does not return the full J-Quants response, request headers, API keys, or raw rows.
- Uses the same memory cache and local rate control as daily-bar fetches.
- Supports `forceRefresh=true`, which skips the cache but still obeys rate control.
- Is not integrated into `/api/stocks/:code`, scoring, watchlists, or bulk analysis yet.
- If the newest disclosure row is a correction or notice without financial values, the endpoint selects the newest row that has financial values.

`latestDisclosure` extracts common fields when present:

- `DisclosedDate` / `DiscDate`
- `DisclosedTime` / `DiscTime`
- `LocalCode` / `Code`
- `TypeOfDocument` / `DocType`
- `NetSales` / `Sales`
- `OperatingProfit` / `OP`
- `OrdinaryProfit` / `OdP`
- `Profit` / `NP`
- `EarningsPerShare` / `EPS`
- `DividendPerShareAnnual` / `DPS`
- `TotalAssets` / `TA`
- `Equity` / `Eq`
- `EquityRatio` / `EqR`
- `BookValuePerShare` / `BPS`
- `CashFlowsFromOperatingActivities` / `CFO`
- `CashFlowsFromInvestingActivities` / `CFI`
- `CashFlowsFromFinancingActivities` / `CFF`
- `CashAndEquivalents` / `Cash`
- forecast fields such as `FDSales`, `FDOP`, `FDNP`, `FDEPS`, and `FDDPS`

`sampleRows` intentionally includes only disclosure date/time, code, document type, sales, operating profit, profit, EPS, and DPS so browser output stays short. `debugInfo` exposes only safe field hints such as `salesFieldUsed`, `operatingProfitFieldUsed`, and `latestRowSelectedBy`.

Free plans may have endpoint, plan, date-range, or rate restrictions. This endpoint is for API structure confirmation only and must not be treated as investment advice.

## Financial Summary Integration

`JQUANTS_USE_FINANCIALS=false` is the default. When it is `true`, `/api/stocks/:code` can attach a lightweight `financialSummary` object after the daily-bar stock data has been fetched and mapped.

The merged `financialSummary` includes only sanitized values such as:

- disclosed date/time and document type
- net sales, operating profit, ordinary profit, profit
- EPS and annual dividend per share
- total assets, equity, equity ratio, BPS
- CFO, CFI, CFF, cash and equivalents
- forecast sales, operating profit, profit, EPS, and dividend
- `cacheHit`, `didNetworkRequest`, and `rowCount`

If financial fetching fails, `/api/stocks/:code` still returns stock price and technical data. The response includes `financialSummary.available=false`, `financialSummaryUnavailable=true`, and a safe error message. API keys, request headers, raw J-Quants rows, and full financial responses are never returned.

When `/api/stocks/:code` fetches daily bars and financial summary in the same request, the backend checks the local rate limit before the financial request. If the retry wait is short, it waits briefly and then continues; if the wait is too long, stock data is still returned and the financial summary is marked unavailable with a rate-limit message.

The stock cache key separates financial integration ON/OFF:

```text
stocks-financials-off:7203:2025-09-01:2026-01-31:/v2/equities/bars/daily
stocks-financials-on:7203:2025-09-01:2026-01-31:/v2/equities/bars/daily
```

Financial data is shown in the frontend as a reference panel and can be weakly reflected in the normal score when `JQUANTS_USE_FINANCIAL_SCORE=true`.

The financial score is deliberately small:

- Range: `-5` to `+5`
- Positive operating profit, net profit, EPS, operating cash flow, and dividend add small points.
- Negative operating profit, net profit, EPS, or operating cash flow subtract small points.
- Strong overheat warnings such as high RSI or high-grab risk are still prioritized. Good financials do not cancel timing risk.
- When `JQUANTS_USE_FINANCIAL_SCORE=false`, `financialSummary` and `financialSignals` are still returned for display, but the total score is not changed.

Bulk analysis still does not fetch financial summaries for multiple issues.

## Structured Decision Summary

`/api/stocks/:code` also includes `structuredSummary`, a rule-based JSON summary prepared for a future AI commentary step.

This is not AI-generated and does not call OpenAI, Claude, Gemini, or any other external AI API.

The object includes:

- `decision`: rule-based label, stance, confidence, and short reason
- `stock`: code, name, market, sector, data source, and update time
- `technical`: trend, price position, RSI status, moving averages, volume status, and comment
- `financial`: sanitized financial summary and weak financial score context
- `risks`: overheat/high-grab risk, warnings, and risk comment
- `positives`, `cautions`, and `entryPlan`
- `aiPromptPayload`: a safe future AI input payload

`aiPromptPayload` intentionally excludes API keys, request headers, `.env` values, localStorage content, J-Quants raw rows, and large raw responses. It is meant only as a compact input for a future short Japanese explanatory comment. It must still be treated as decision-support context, not investment advice.

Generating `structuredSummary` does not change `totalScore`, `buyScore`, or the rule-based signal. Good financials still do not cancel high RSI, high-grab, or other timing risks.

## AI Summary Mock

`/api/stocks/:code` can also include `aiSummary`, a rule-based mock commentary generated from `structuredSummary`.

This is a preview for a future AI summary feature. It does not call OpenAI, Claude, Gemini, or any other external AI API.

Environment flags:

- `AI_SUMMARY_MOCK_ENABLED=true`: generate `aiSummary` in `rule_based_mock` mode.
- `AI_SUMMARY_EXTERNAL_API_ENABLED=false`: reserved for a future step. In the current implementation, even if this is set to `true`, no external AI API is called.

The response uses:

- `mode: "rule_based_mock"`
- `aiGenerated: false`
- `externalApiUsed: false`
- `provider: "none"`

The mock summary contains a short Japanese comment, bullet points, warnings, and source metadata. It avoids buy/sell certainty such as "必ず買い" or "今すぐ売り", and it explicitly states that the output is not investment advice.

The mock builder uses only sanitized `structuredSummary` fields. It does not include API keys, request headers, `.env` values, localStorage content, J-Quants raw rows, or raw response bodies.

Generating `aiSummary` does not change `totalScore`, `buyScore`, `structuredSummary`, or the rule-based signal. Bulk analysis still does not call J-Quants or external AI APIs for many symbols.

## News And Theme Mock Layer

`/api/stocks/:code` can include `themeSummary`, a local mock or manual-input layer for news-like market themes.

This feature is intentionally offline. It does not call external news APIs and does not call OpenAI, Claude, Gemini, or any other AI API. It is a safe preparation layer for future handling of topics such as SpaceX listing speculation, space, semiconductor, AI, defense, FX-sensitive themes, earnings expectations, and short-term theme overheating.

Environment flags:

- `THEME_SUMMARY_MOCK_ENABLED=true`: return local mock theme material when available.
- `THEME_SUMMARY_EXTERNAL_NEWS_API_ENABLED=false`: reserved for a future step. In the current implementation, even if this is set to `true`, no external news API is called.
- `THEME_SUMMARY_SCORE_ENABLED=false`: theme material is displayed and included in summaries, but it does not change `totalScore` by default.

The response uses:

- `source: "LOCAL_MOCK_THEME"` or `"MANUAL_AND_LOCAL_MOCK_THEME"`
- `externalNewsApiUsed: false`
- `externalAiUsed: false`
- `themeScoreApplied: false`

Examples in the local mock layer include:

- `7203`: automobile, yen weakness benefit, EV, hybrid, global economy, earnings expectation
- `8035`: semiconductor, AI investment, generative AI, capex, US tech-stock linkage
- `9984`: AI, semiconductor investment, Arm, Nasdaq linkage, investment-company risk
- `SPACE_THEME_SAMPLE`: SpaceX listing speculation, space, satellite communications, defense space, speculation buying, short-term overheating

The frontend shows a "News / Theme Material" panel and can temporarily apply manually entered comma-separated themes to the current analysis. Manual theme input is not sent to any external service.

`structuredSummary.theme`, `structuredSummary.positives`, `structuredSummary.cautions`, and the rule-based `aiSummary` mock can reference theme material. Theme material is always treated as reference information only. It must not be used to make a deterministic buy/sell decision, and latest official information and news should be checked before any real trading decision.

## Pre-Trade Check

`/api/stocks/:code` can include `preTradeCheck`, a rule-based checklist for items the user should confirm before any real trade.

This feature is not a buy/sell recommendation and does not change `totalScore`, `buyScore`, `judgeSignal`, J-Quants fetch behavior, financial fetch behavior, theme generation, or structured-summary scoring logic.

The check summarizes:

- data source: J-Quants real data, CSV, or mock
- freshness: last update/date status and possible free-plan delay
- financials: whether J-Quants financial summary is available
- news/disclosures: news API, TDnet, and earnings-detail status
- risk: overheat, high-grab, RSI, and theme-speculation cautions
- checklist: securities app price/volume check, company IR, TDnet, latest news, entry plan, and loss rule

`preTradeCheck.tradeAdvice` is always `false`. Wording intentionally uses "要確認", "確認不足あり", "参考情報", and similar neutral labels instead of buy/sell instructions.

The frontend can store only checklist state in localStorage under:

- `stockAnalyzer.preTradeChecklist`

Allowed stored fields are `code`, checked item ids, and `updatedAt`. API keys, raw rows, full financial summaries, full structured summaries, AI summaries, debug info, headers, and `.env` values are not stored.

`structuredSummary.preTrade` can include a compact overview, and `aiSummary.warnings` can remind the user to check a securities app, company IR, TDnet, and latest news before trading. No external AI, news, TDnet, securities-company, or order API is added.

## Next Step

The next implementation stage can map financial summaries into a safe internal financial-data object only when:

- `JQUANTS_ENABLED=true`
- `JQUANTS_API_KEY` is present
- the API key remains backend-only
- frontend still calls only this local backend
- cache and rate-limit behavior are visible to the user before any bulk real-data fetch is added
- financial summary fields have been verified for the current plan and symbol range
