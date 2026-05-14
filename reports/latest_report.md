# Codex 作業レポート

## リポジトリとフォルダの役割

今回の重要な前提:

- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test`
  - 管理・ドキュメント・レポート共有用リポジトリ。
  - GitHub に push できるのはこのリポジトリ。
  - `reports/latest_report.md` は、この管理用リポジトリに保存している。
- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself`
  - 実際に動作していた X 自動運用の実アプリ本体。
  - `yokaze_daily`、`ai_pickup`、`new_account_daily`、GUI設定、LLM provider 実装が入っている。
  - 現時点では Git リポジトリではないため、実アプリのコード差分そのものは GitHub に push できていない。

今回の本題は `01_context01_myself` 側の実アプリ修正。
`0001_test` はその作業内容を記録・共有するための管理場所。

## 実アプリ本体フォルダ

実アプリ本体は以下。

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself
```

主な実アプリ構成:

- `yokaze_daily/main.py`
- `ai_pickup/main.py`
- `ai_pickup/score_and_draft.py`
- `ai_pickup/recommend_today_post.py`
- `ai_pickup/x_research_analyze.py`
- `new_account_daily/main.py`
- `tools/settings_manager.py`
- `shared/llm/factory.py`
- `shared/llm/gemini_client.py`
- `shared/llm/openai_client.py`
- `shared/draft_pipeline/generate_draft.py`

## 今回の目的

GUI で以下を選んでいるのに、実行ログでは Gemini 側が呼ばれていた問題を修正・確認すること。

```text
TEXT_LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.4
```

原因は、実アプリ本体 `01_context01_myself` の一部生成フローで、GUI設定や `shared/llm/factory.py` を経由せず、Gemini 固定関数を直接呼んでいたこと。

## yokaze_daily/main.py の call_gemini_text 直呼び修正

修正前:

- `yokaze_daily/main.py` 内に `call_gemini_text(...)` の独自実装が存在。
- preview生成、通常本文生成、画像プロンプト生成で `call_gemini_text(...)` を直接呼び出し。
- そのため `TEXT_LLM_PROVIDER=openai` をGUIで選んでも、本文生成が Gemini 側へ固定される可能性があった。

修正後:

- `call_gemini_text(...)` の独自実装を廃止。
- 本文生成は `generate_text_for_role("text", ...)` に統一。
- `generate_text_for_role()` 内で `client_for_role(role, account_type="yokaze_daily")` を呼ぶ。
- 通常本文生成は `TEXT_LLM_PROVIDER` を参照。
- 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を参照。
- ログに `account_type=yokaze_daily`、`provider`、`model`、`function`、`role`、`request_label` が出る。

結果:

- `TEXT_LLM_PROVIDER=openai` のとき本文生成は OpenAI 側へ分岐。
- `TEXT_LLM_PROVIDER=gemini` のとき本文生成は Gemini 側へ分岐。
- 画像プロンプト生成は本文providerと混線せず、`IMAGE_PROMPT_LLM_PROVIDER` を使う。

## shared/llm/factory.py の lazy import 修正

修正前:

- `shared/llm/factory.py` の import 時点で `GeminiClient` / `OpenAIClient` を top-level import していた。
- mockテストでも、使わない provider client やその依存を読み込む可能性があった。
- テスト環境に `requests` がないだけで、factory import が失敗する問題があった。

修正後:

- `create_client("gemini")` の中でだけ `GeminiClient` を import。
- `create_client("openai")` の中でだけ `OpenAIClient` を import。
- factory自体は軽く import できる。
- mockテストでは実API client を読み込まずに provider routing を検証できる。
- `RoutedLLMClient` で provider mismatch を検出し、設定と実clientが一致しない場合は `RuntimeError` で停止。

ログ出力:

```text
[LLM_ROUTE] account_type=... role=... env=... provider=... model=... function=...
[LLM_CALL] account_type=... role=... provider=... model=... function=... request_label=...
```

## GUI設定との接続状況

GUI設定ファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tools\settings_manager.py
```

GUIで管理している provider 設定:

- `TEXT_LLM_PROVIDER`
- `IMAGE_PROMPT_LLM_PROVIDER`
- `QUALITY_CHECK_LLM_PROVIDER`
- `OPENAI_MODEL`
- `GEMINI_MODEL`

接続状況:

- GUIの「今すぐ生成」実行時に、subprocess 起動前に `save_env(show_message=False)` を実行するよう補強。
- これにより、GUIで選んだ provider/model が `.env` に保存されてから各アカウントの生成処理が起動する。
- 各アカウントの生成処理は `.env` を読み、`shared/llm/factory.py` の `client_for_role(...)` を経由する。

provider role の対応:

- 本文生成: `TEXT_LLM_PROVIDER`
- 画像プロンプト生成: `IMAGE_PROMPT_LLM_PROVIDER`
- 品質チェック: `QUALITY_CHECK_LLM_PROVIDER`

アカウント別確認:

- `yokaze_daily`
  - 本文生成: `client_for_role("text", account_type="yokaze_daily")`
  - 画像プロンプト生成: `client_for_role("image_prompt", account_type="yokaze_daily")`
- `ai_pickup`
  - 本文生成: `client_for_role("text", account_type="ai_pickup")`
  - shared draft pipeline 内で `image_prompt` / `quality_check` も role 別に分離。
- `new_account_daily`
  - 本文生成: `client_for_role("text", account_type="new_account_daily")`

## その他の実アプリ修正

`01_context01_myself` 側で以下も修正済み。

- `new_account_daily/main.py`
  - Gemini固定の `call_gemini(...)` を廃止。
  - 本文生成を `client_for_role("text", account_type="new_account_daily")` 経由へ変更。
- `ai_pickup/score_and_draft.py`
  - Gemini固定の `call_gemini(...)` を廃止。
  - `generate_llm_text(...)` を追加し、本文生成を `client_for_role("text", account_type="ai_pickup")` 経由へ変更。
- `ai_pickup/recommend_today_post.py`
  - `call_gemini(...)` ではなく `generate_llm_text(...)` 経由へ変更。
- `ai_pickup/x_research_analyze.py`
  - `call_gemini(...)` ではなく `generate_llm_text(...)` 経由へ変更。
- `shared/draft_pipeline/generate_draft.py`
  - `text` / `image_prompt` / `quality_check` の各 client 生成に `account_type` を伝搬。
- `shared/llm/__init__.py`
  - Gemini/OpenAI client の即時 import をやめ、必要時だけ読み込む lazy export に変更。

## 実施したモックテスト

実APIは禁止のため、すべて mock / dry-run で確認。

実アプリ本体側で追加・拡張したテスト:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py
```

確認した内容:

- GUI保存相当で `.env` に provider/model が反映される。
- GUI生成フローが subprocess 起動前に `save_env(show_message=False)` を実行する。
- `TEXT_LLM_PROVIDER=openai` のとき本文生成が `OpenAIClient.generate_text` 側へ分岐する。
- `TEXT_LLM_PROVIDER=gemini` のとき本文生成が `GeminiClient.generate_text` 側へ分岐する。
- 画像プロンプト生成が `IMAGE_PROMPT_LLM_PROVIDER` を使う。
- 品質チェックが `QUALITY_CHECK_LLM_PROVIDER` を使う。
- provider mismatch は `RuntimeError` で停止する。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の3アカウントで `account_type` 付きログが出る。
- 対象ランタイム内に `call_gemini_text(` / `call_gemini(` / `requests.post(` の直呼びが残っていない。

## テスト結果

実API呼び出し:

```text
なし
```

構文確認:

```text
python -m compileall shared\llm tools\settings_manager.py yokaze_daily\main.py new_account_daily\main.py ai_pickup\score_and_draft.py ai_pickup\recommend_today_post.py ai_pickup\x_research_analyze.py shared\draft_pipeline\generate_draft.py tests\test_provider_routing_runtime.py
```

結果:

```text
OK
```

モックテスト:

```text
python -m unittest discover -s tests -v
```

結果:

```text
11 tests OK
```

## 直呼びの残件

対象ランタイム内では、以下の直呼び残件なし。

```text
call_gemini_text(
call_gemini(
requests.post(
```

確認対象:

- `yokaze_daily/main.py`
- `new_account_daily/main.py`
- `ai_pickup/score_and_draft.py`
- `ai_pickup/recommend_today_post.py`
- `ai_pickup/x_research_analyze.py`

補足:

- `shared/llm/gemini_client.py`
- `shared/llm/openai_client.py`
- `shared/image_pipeline/openai_image_client.py`

上記 client 実装内の `requests.post` は provider client 本体なので、今回禁止した「生成フローからの直呼び」には含めない。

## 変更ファイル

実アプリ本体側、Git管理外:

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

管理・レポート用リポジトリ側:

- `C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\reports\latest_report.md`

## まだ残っている課題

- 実アプリ本体 `01_context01_myself` が Git リポジトリではない。
- そのため、実アプリのコード変更そのものは GitHub に push できていない。
- GitHub 上で実コード差分をレビューできる状態になっていない。
- 実APIによる疎通確認は未実施。ユーザー許可があるまで実行しない。
- `TEXT_LLM_PROVIDER` 未設定時の default は既存互換の `gemini` のまま。GUI default の `openai` に合わせるかは方針決定が必要。

## 次にやるべきこと

1. `01_context01_myself` を GitHub 管理対象にする。
2. 実アプリ側の修正差分を commit / push できる状態にする。
3. GitHub上で以下の差分をレビューできるようにする。
   - `tools/settings_manager.py`
   - `shared/llm/factory.py`
   - `shared/llm/__init__.py`
   - `yokaze_daily/main.py`
   - `new_account_daily/main.py`
   - `ai_pickup/*.py`
   - `shared/draft_pipeline/generate_draft.py`
   - `tests/test_provider_routing_runtime.py`
4. ユーザー許可後、必要最小限の実API疎通確認を行う。
5. 未設定時 default provider を `gemini` のままにするか、GUI default に合わせて `openai` にするか決める。

## ChatGPTへ相談したいこと

- 実アプリ本体 `01_context01_myself` を `0001_test` に統合するか、別リポジトリとして管理するか。
- Git管理外の実アプリ修正を、どのタイミングで正式な GitHub 管理へ移すか。
- `TEXT_LLM_PROVIDER` 未設定時の default を既存互換の `gemini` に残すか、GUI default の `openai` に合わせるか。
