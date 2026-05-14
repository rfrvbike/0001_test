# Codex 作業レポート

## 実施した作業

- 実アプリ本体 `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself` 側で、provider routing が GUI 生成フローでも使われるかを確認した。
- 実APIは一切呼ばず、OpenAI / Gemini クライアントを mock に差し替えて dry-run 確認した。
- `reports/latest_report.md` が文字化けしていたため、今回の実アプリ側修正内容が分かるように UTF-8 の日本語で整理し直した。

## 01_context01_myself 側に入れた修正内容

実アプリ本体側では、以下を修正済み。

- `shared/llm/factory.py`
  - `RoutedLLMClient` を追加し、role別 provider routing を一元化。
  - `TEXT_LLM_PROVIDER` / `IMAGE_PROMPT_LLM_PROVIDER` / `QUALITY_CHECK_LLM_PROVIDER` を分離して読むようにした。
  - `provider` / `model` / `function` / `role` / `request_label` / `account_type` を `[LLM_ROUTE]` と `[LLM_CALL]` でログ出力。
  - provider設定と実際の client provider が一致しない場合は `RuntimeError` で停止。
  - Gemini/OpenAI client を top-level import せず、`create_client()` 内で lazy import するよう変更。
- `shared/llm/__init__.py`
  - Gemini/OpenAI client の即時 import をやめ、必要時だけ読み込む lazy export に変更。
- `tools/settings_manager.py`
  - GUIの「今すぐ生成」開始時に `save_env(show_message=False)` を実行。
  - GUIで選んだ provider/model が `.env` に保存されてから subprocess で各アカウント生成が走るよう補強。
- `yokaze_daily/main.py`
  - `call_gemini_text(...)` の直接呼び出しを廃止。
  - 本文生成は `client_for_role("text", account_type="yokaze_daily")` 経由に変更。
  - 画像プロンプト生成は `client_for_role("image_prompt", account_type="yokaze_daily")` 経由に変更。
- `new_account_daily/main.py`
  - Gemini固定の `call_gemini(...)` を廃止。
  - 本文生成は `client_for_role("text", account_type="new_account_daily")` 経由に変更。
- `ai_pickup/score_and_draft.py`
  - Gemini固定の `call_gemini(...)` を廃止。
  - `generate_llm_text(...)` を追加し、本文生成は `client_for_role("text", account_type="ai_pickup")` 経由に変更。
- `ai_pickup/recommend_today_post.py`
  - `call_gemini(...)` ではなく `generate_llm_text(...)` 経由に変更。
- `ai_pickup/x_research_analyze.py`
  - `call_gemini(...)` ではなく `generate_llm_text(...)` 経由に変更。
- `shared/draft_pipeline/generate_draft.py`
  - `text` / `image_prompt` / `quality_check` の各 client 生成に `account_type` を伝搬。
- `tests/test_provider_routing_runtime.py`
  - GUI保存、GUI生成前保存、provider分岐、role分離、3アカウントの routing を mock で検証するテストを追加・拡張。

## yokaze_daily/main.py の call_gemini_text 直呼び修正

修正前:

- `yokaze_daily/main.py` 内に `call_gemini_text(...)` の独自実装があった。
- preview生成、通常本文生成、画像プロンプト生成で `call_gemini_text(...)` を直接呼んでいた。
- そのため GUI で `TEXT_LLM_PROVIDER=openai` / `OPENAI_MODEL=gpt-5.4` を選んでも、本文生成が Gemini 側へ固定される可能性があった。

修正後:

- `call_gemini_text(...)` の独自実装と直接呼び出しを削除。
- 本文生成は `generate_text_for_role("text", ...)` に統一。
- `generate_text_for_role()` 内で `client_for_role(role, account_type="yokaze_daily")` を呼ぶ。
- 画像プロンプト生成は `generate_text_for_role("image_prompt", ...)` に分離。
- これにより、本文生成は `TEXT_LLM_PROVIDER`、画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を参照する。

## shared/llm/factory.py の lazy import

修正前:

- `factory.py` import 時点で `GeminiClient` / `OpenAIClient` を top-level import していた。
- テスト環境に `requests` がないだけで import が落ちる可能性があった。
- mock テストでも、使わない provider client の依存を読み込んでしまっていた。

修正後:

- `create_client("gemini")` の中でだけ `GeminiClient` を import。
- `create_client("openai")` の中でだけ `OpenAIClient` を import。
- factory自体は軽く import でき、mockテストでは実API client を読み込まずに provider routing を検証できる。

## GUIからの dry-run 確認結果

実GUIは起動せず、GUIと同じ設定保存・生成起動の流れを mock で確認した。

- `tools/settings_manager.py` の `.env` 読み書き関数で、GUI選択相当の provider/model が保存されることを確認。
- `run_generation()` が subprocess 起動前に `save_env(show_message=False)` を実行することを確認。
- `ACCOUNTS` の起動先を確認。
  - `yokaze_daily`: `main.py`
  - `new_account_daily`: `main.py`
  - `ai_pickup`: `recommend_today_post.py`
- `TEXT_LLM_PROVIDER=openai` のとき、本文生成が `OpenAIClient.generate_text` 側へ分岐することを確認。
- `TEXT_LLM_PROVIDER=gemini` のとき、本文生成が `GeminiClient.generate_text` 側へ分岐することを確認。
- 画像プロンプト生成が `IMAGE_PROMPT_LLM_PROVIDER` を使うことを確認。
- 品質チェックが `QUALITY_CHECK_LLM_PROVIDER` を使うことを確認。
- ログに `provider` / `model` / `function` / `account_type` が出ることを確認。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の3アカウントで account-aware routing を確認。

## 実施したモックテスト

実アプリ本体側で以下を実行。

```text
python -m unittest discover -s tests -v
```

確認した主なテスト:

- GUI保存相当で `TEXT_LLM_PROVIDER` / `IMAGE_PROMPT_LLM_PROVIDER` / `QUALITY_CHECK_LLM_PROVIDER` / `OPENAI_MODEL` が `.env` に反映される。
- GUI生成フローが subprocess 起動前に `save_env(show_message=False)` を実行する。
- `TEXT_LLM_PROVIDER=openai` で `OpenAIClient.generate_text` 側へ分岐する。
- `TEXT_LLM_PROVIDER=gemini` で `GeminiClient.generate_text` 側へ分岐する。
- `IMAGE_PROMPT_LLM_PROVIDER` が本文providerと混線しない。
- `QUALITY_CHECK_LLM_PROVIDER` が本文providerと混線しない。
- provider mismatch は `RuntimeError` で停止する。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` が routing を経由し、`account_type` をログに出す。
- 対象ランタイム内に `call_gemini_text(` / `call_gemini(` / `requests.post(` の直呼びが残っていない。

## テスト結果

- 実API呼び出し: なし。
- 構文確認: OK。
- モックテスト: 11 tests OK。

構文確認コマンド:

```text
python -m compileall shared\llm tools\settings_manager.py yokaze_daily\main.py new_account_daily\main.py ai_pickup\score_and_draft.py ai_pickup\recommend_today_post.py ai_pickup\x_research_analyze.py shared\draft_pipeline\generate_draft.py tests\test_provider_routing_runtime.py
```

モックテストコマンド:

```text
python -m unittest discover -s tests -v
```

## まだ残っている直呼びの有無

対象ランタイム内では、以下の直呼び残件なし。

- `call_gemini_text(`
- `call_gemini(`
- `requests.post(`

確認対象:

- `yokaze_daily/main.py`
- `new_account_daily/main.py`
- `ai_pickup/score_and_draft.py`
- `ai_pickup/recommend_today_post.py`
- `ai_pickup/x_research_analyze.py`

補足:

- `shared/llm/gemini_client.py`、`shared/llm/openai_client.py`、`shared/image_pipeline/openai_image_client.py` 内の `requests.post` は provider client 本体なので、禁止対象の「ランタイム直呼び」ではない。

## 変更ファイル

実アプリ本体側（Git管理外）:

- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tools\settings_manager.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\factory.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\__init__.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\yokaze_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\new_account_daily\main.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\score_and_draft.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\recommend_today_post.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\x_research_analyze.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\draft_pipeline\generate_draft.py`
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py`

共有用リポジトリ側:

- `reports/latest_report.md`

## 発見した問題

- 実アプリ本体 `01_context01_myself` は Git リポジトリではない。
- そのため、実アプリのコード変更そのものは GitHub に push できていない。
- 現在 GitHub に push できるのは、`0001_test` 側の reports / docs のみ。

## 未解決事項

- 実アプリ本体 `01_context01_myself` を Git 管理する必要がある。
- GitHub上で実コード差分をレビューできる状態にはまだなっていない。
- 実APIによる疎通確認は未実施。ユーザー許可があるまで実行しない。

## 次にやるべきこと

- `01_context01_myself` を GitHub 管理対象にする。
- 実アプリ側の修正差分を commit / push できる状態にする。
- GitHub上で `tools/settings_manager.py`、`shared/llm/factory.py`、各アカウント `main.py` の差分をレビューできるようにする。
- ユーザー許可後、必要最小限の実API疎通確認を行う。
- 未設定時 default provider を `gemini` のままにするか、GUI default に合わせて `openai` にするか方針決定する。

## ChatGPTへ相談したいこと

- 実アプリ本体 `01_context01_myself` を `0001_test` に統合するか、別リポジトリとして管理するか。
- `TEXT_LLM_PROVIDER` 未設定時の default を既存互換の `gemini` に残すか、GUI default の `openai` に合わせるか。
