# Codex 作業レポート

## 実施した作業

- 実アプリ本体候補 `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself` に対して、本文生成の Gemini 直呼びを provider routing へ統一した。
- 実APIは呼ばず、`unittest.mock` によるモックテストのみ実行した。
- `0001_test` 側に今回の作業結果を記録した。

## 調査内容

- `yokaze_daily/main.py` の本文生成、preview生成、画像プロンプト生成で `call_gemini_text(...)` が直接呼ばれていた。
- `ai_pickup/score_and_draft.py`、`ai_pickup/recommend_today_post.py`、`ai_pickup/x_research_analyze.py` でも Gemini 固定の `call_gemini(...)` 経由が残っていた。
- `new_account_daily/main.py` も Gemini 固定関数を持っていた。
- `tools/settings_manager.py` には `TEXT_LLM_PROVIDER` / `IMAGE_PROMPT_LLM_PROVIDER` / `QUALITY_CHECK_LLM_PROVIDER` / `OPENAI_MODEL=gpt-5.4` の GUI 管理項目が存在していた。

## 修正内容

- `shared/llm/factory.py`: role別routing wrapper、provider/model/functionログ、provider不一致停止、lazy import を追加。
- `shared/llm/__init__.py`: Gemini/OpenAI client の即時importをやめ、lazy export に変更。
- `yokaze_daily/main.py`: 本文生成は `client_for_role("text")`、画像プロンプト生成は `client_for_role("image_prompt")` 経由に変更。
- `new_account_daily/main.py`: 本文生成を `client_for_role("text")` 経由に変更。
- `ai_pickup/score_and_draft.py`: `generate_llm_text(...)` を追加し、本文生成を `client_for_role("text")` 経由に変更。
- `ai_pickup/recommend_today_post.py` / `ai_pickup/x_research_analyze.py`: `generate_llm_text(...)` 経由に変更。

## 変更ファイル

実アプリ本体側（Git管理外）:

- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\factory.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\__init__.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\yokaze_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\new_account_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\score_and_draft.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\recommend_today_post.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\x_research_analyze.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py`

共有用リポジトリ側:

- `docs/BUG_HISTORY.md`
- `reports/latest_report.md`
- `reports/codex_report_20260515_0045.md`

## テスト結果

- 実API呼び出し: なし。
- 構文確認: `python -m compileall ...` 結果 OK。
- モックテスト: `python -m unittest discover -s tests -v` 結果 8 tests OK。
- 確認内容:
  - `TEXT_LLM_PROVIDER=openai` のとき text role が openai を選ぶ。
  - `IMAGE_PROMPT_LLM_PROVIDER=gemini` が本文providerと混線しない。
  - provider mismatch は `RuntimeError` で停止。
  - `yokaze_daily` / `ai_pickup` / `new_account_daily` が provider routing を経由する。
  - 対象ランタイム内の `call_gemini_text(` / `call_gemini(` / `requests.post(` 直呼び残件なし。

## 発見した問題

- 実アプリ本体 `01_context01_myself` は Git リポジトリではなかったため、コード修正そのものを GitHub に commit / push できない。
- `0001_test` は docs / reports 共有用の Git リポジトリであり、今回 push できるのはレポートと履歴のみ。
- `factory.normalize_provider(None)` は既存互換のため未設定時 `gemini` のまま。GUI保存値が必ず入る運用なら問題は出にくいが、未設定時の既定providerを `openai` に寄せるかは別途判断が必要。

## 未解決事項

- `01_context01_myself` を Git 管理する、または本体コードを GitHub 管理リポジトリへ移す必要がある。
- 今回のコード差分はローカル実アプリフォルダに存在するが、GitHub URL として直接レビューできない。
- `tools/settings_manager.py` 自体は今回コード変更なし。GUI保存値は既に存在していたため、routing側で実行時の整合性を担保した。

## 次にやるべきこと

- `01_context01_myself` を GitHub 管理対象にする。
- そのうえで、今回の実アプリ修正差分を commit / push し、コードレビュー可能なURLを作る。
- 実API確認はユーザー許可後に限定して行う。

## ChatGPTへ相談したいこと

- `TEXT_LLM_PROVIDER` 未設定時の default を既存互換の `gemini` に残すか、GUI default と合わせて `openai` に変更するか。
- 実アプリ本体 `01_context01_myself` を `0001_test` に統合するか、別リポジトリとして管理するか。
