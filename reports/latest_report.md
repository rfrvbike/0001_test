# Codex 作業レポート

## 実施した作業

- 実GUIの生成フローで、GUI設定値が provider routing に届くかを dry-run / mock で確認した。
- 実APIは呼ばず、`unittest.mock` で OpenAI / Gemini クライアントを差し替えて確認した。
- GUIの「今すぐ生成」開始時に、現在のGUI値を `.env` へ保存してから subprocess を起動するよう実アプリ側を補強した。
- LLM routing ログに `account_type` を追加した。

## 調査内容

- GUI本体: `01_context01_myself/tools/settings_manager.py`
  - `ACCOUNTS` で `new_account_daily/main.py`、`yokaze_daily/main.py`、`ai_pickup/recommend_today_post.py` を subprocess 起動する構造。
  - 生成プロセスは各アカウントの `.env` を読むため、GUIで選択した値を実行前に保存する必要がある。
- provider routing:
  - `shared/llm/factory.py` が `TEXT_LLM_PROVIDER` / `IMAGE_PROMPT_LLM_PROVIDER` / `QUALITY_CHECK_LLM_PROVIDER` を role 別に読む。
  - `yokaze_daily`、`ai_pickup`、`new_account_daily` の本文生成は `client_for_role("text", account_type=...)` 経由。
  - `shared/draft_pipeline/generate_draft.py` の画像プロンプト・品質チェックは `client_for_role("image_prompt" / "quality_check", account_type=...)` 経由。

## 修正内容

- `tools/settings_manager.py`
  - `run_generation()` の subprocess 起動前に `save_env(show_message=False)` を実行。
  - GUIで選んだ provider / model が保存済み `.env` と一致した状態で生成フローへ入るようにした。
- `shared/llm/factory.py`
  - `client_for_role(role, account_type="...")` を受け取れるようにした。
  - `[LLM_ROUTE]` / `[LLM_CALL]` に `account_type`、`provider`、`model`、`function`、`role`、`request_label` を出力。
  - provider mismatch エラーにも `account_type` を含めるようにした。
- `yokaze_daily/main.py`
  - 本文生成・画像プロンプト生成の routing に `account_type="yokaze_daily"` を付与。
- `new_account_daily/main.py`
  - 本文生成の routing に `account_type="new_account_daily"` を付与。
- `ai_pickup/score_and_draft.py`
  - 本文生成の routing に `account_type="ai_pickup"` を付与。
- `shared/draft_pipeline/generate_draft.py`
  - text / image_prompt / quality_check の各 client 生成へ `account_type` を伝搬。
- `tests/test_provider_routing_runtime.py`
  - GUI `.env` 保存、GUI生成前保存、OpenAI/Gemini分岐、画像プロンプトprovider分離、品質チェックprovider分離、3アカウントの `account_type` ログをモックで検証。

## 変更ファイル

実アプリ本体側（Git管理外）:

- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tools\settings_manager.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\factory.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\yokaze_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\new_account_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\score_and_draft.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\draft_pipeline\generate_draft.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py`

共有用リポジトリ側:

- `reports/latest_report.md`
- `reports/codex_report_20260515_0056.md`

## テスト結果

- 実API呼び出し: なし。
- 構文確認:
  - `python -m compileall shared\llm tools\settings_manager.py yokaze_daily\main.py new_account_daily\main.py ai_pickup\score_and_draft.py ai_pickup\recommend_today_post.py ai_pickup\x_research_analyze.py shared\draft_pipeline\generate_draft.py tests\test_provider_routing_runtime.py`
  - 結果: OK
- モックテスト:
  - `python -m unittest discover -s tests -v`
  - 結果: 11 tests OK
- 確認できたこと:
  - GUI保存相当の `.env` 更新で `TEXT_LLM_PROVIDER=openai` が保持される。
  - GUI生成フローは subprocess 起動前に `save_env(show_message=False)` を実行する。
  - `TEXT_LLM_PROVIDER=openai` のとき本文生成は `OpenAIClient.generate_text` 側へ分岐する。
  - `TEXT_LLM_PROVIDER=gemini` のとき本文生成は `GeminiClient.generate_text` 側へ分岐する。
  - 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を使う。
  - 品質チェックは `QUALITY_CHECK_LLM_PROVIDER` を使う。
  - ログに `provider` / `model` / `function` / `account_type` が出る。
  - `yokaze_daily` / `ai_pickup` / `new_account_daily` で account-aware routing を確認。
  - 対象ランタイム内の `call_gemini_text(` / `call_gemini(` / `requests.post(` 直呼び残件なし。

## 発見した問題

- `01_context01_myself` は Git リポジトリではないため、実アプリのコード変更そのものを GitHub に push できない。
- `0001_test` は docs / reports 共有用の Git リポジトリであり、今回 push できるのはレポートのみ。

## 未解決事項

- 実アプリ本体 `01_context01_myself` を Git 管理する必要がある。
- GitHub上で実コード差分をレビューできる状態にはまだなっていない。
- 実APIによる最終疎通確認はユーザー許可後に限定して行う。

## 次にやるべきこと

- `01_context01_myself` を GitHub 管理対象にする。
- 実コード差分を commit / push できる状態にする。
- ユーザー許可後、必要最小限の実API疎通確認を行う。

## ChatGPTへ相談したいこと

- 実アプリ本体を `0001_test` に統合するか、別リポジトリとして管理するか。
- 未設定時 default provider を `gemini` のままにするか、GUI default に合わせて `openai` にするか。
