# latest_report.md

更新日: 2026-05-15

## 今回実施した作業内容

今回の作業は、commit `8445a972b9989ee7d3b731c66408a7618076699a` で整理した内容を、最新レポートとして明確に反映すること。

主題は `0001_test` 側の provider routing 基盤説明ではなく、実アプリ本体 `01_context01_myself` 側に入れた修正内容の記録。

実施したこと:

- 実アプリ本体が `01_context01_myself` であることを明記。
- `0001_test` は管理・docs・reports 用であることを明記。
- `yokaze_daily/main.py` の `call_gemini_text(...)` 直呼び問題をどう修正したかを記録。
- `shared/llm/factory.py` の lazy import 化と provider routing の接続状況を記録。
- GUI dry-run / mock 確認結果を記録。
- 実施したモックテストとテスト結果を記録。
- 未解決事項と次にやるべきことを整理。

## フォルダの役割

### 管理・レポート用

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test
```

役割:

- docs / reports 管理
- ChatGPT / Codex / Cursor 共有用
- GitHub に push してURL共有するための管理リポジトリ
- この `reports/latest_report.md` を保存している場所

### 実アプリ本体

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself
```

役割:

- 実際に動作していた X 自動運用システム本体
- GUI設定
- provider routing
- `yokaze_daily`
- `ai_pickup`
- `new_account_daily`
- 本文生成、画像プロンプト生成、品質チェック、draft生成

重要:

- `01_context01_myself` は現時点で Git リポジトリではない。
- そのため、実アプリ側コード修正そのものは GitHub に push できていない。
- GitHub に push できているのは、`0001_test` 側の docs / reports のみ。

## 修正した実アプリ側ファイル

実アプリ本体 `01_context01_myself` 側で修正したファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tools\settings_manager.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\factory.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\llm\__init__.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\yokaze_daily\main.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\new_account_daily\main.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\score_and_draft.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\recommend_today_post.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\ai_pickup\x_research_analyze.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\shared\draft_pipeline\generate_draft.py
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py
```

管理・レポート用 `0001_test` 側で更新したファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\reports\latest_report.md
```

## yokaze_daily/main.py の修正内容

問題:

- GUIで `TEXT_LLM_PROVIDER=openai`、`OPENAI_MODEL=gpt-5.4` を選んでも、`yokaze_daily/main.py` 内で `call_gemini_text(...)` を直接呼んでいた。
- そのため、GUI設定が本文生成に反映されず、Gemini固定になる可能性があった。

修正:

- `call_gemini_text(...)` の直接呼び出しを廃止。
- 本文生成を `generate_text_for_role("text", ...)` 経由に変更。
- `generate_text_for_role()` 内で `client_for_role(role, account_type="yokaze_daily")` を呼ぶようにした。
- 画像プロンプト生成は `generate_text_for_role("image_prompt", ...)` 経由に分離。

結果:

- 本文生成は `TEXT_LLM_PROVIDER` を参照。
- 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を参照。
- `TEXT_LLM_PROVIDER=openai` なら OpenAI 側へ分岐。
- `TEXT_LLM_PROVIDER=gemini` なら Gemini 側へ分岐。

## shared/llm/factory.py の修正内容

修正内容:

- `RoutedLLMClient` を追加。
- role別に provider を解決。
- provider と実clientの不一致を `RuntimeError` で停止。
- provider routing のログを追加。
- Gemini/OpenAI client を lazy import に変更。

lazy import の内容:

- 修正前:
  - `factory.py` import 時点で `GeminiClient` / `OpenAIClient` を top-level import。
  - mockテストでも不要な provider client 依存を読み込む可能性があった。
- 修正後:
  - `create_client("gemini")` の中でだけ `GeminiClient` を import。
  - `create_client("openai")` の中でだけ `OpenAIClient` を import。
  - mockテストで実API client を読み込まずに provider routing を検証可能。

ログ出力:

```text
[LLM_ROUTE] account_type=... role=... env=... provider=... model=... function=...
[LLM_CALL] account_type=... role=... provider=... model=... function=... request_label=...
```

## provider routing の接続状況

GUIで管理している provider 設定:

```text
TEXT_LLM_PROVIDER
IMAGE_PROMPT_LLM_PROVIDER
QUALITY_CHECK_LLM_PROVIDER
OPENAI_MODEL
GEMINI_MODEL
```

role別の接続:

```text
本文生成             -> TEXT_LLM_PROVIDER
画像プロンプト生成   -> IMAGE_PROMPT_LLM_PROVIDER
品質チェック         -> QUALITY_CHECK_LLM_PROVIDER
```

アカウント別の接続:

```text
yokaze_daily
  本文生成           -> client_for_role("text", account_type="yokaze_daily")
  画像プロンプト生成 -> client_for_role("image_prompt", account_type="yokaze_daily")

ai_pickup
  本文生成           -> client_for_role("text", account_type="ai_pickup")
  shared draft内     -> image_prompt / quality_check を role別に分離

new_account_daily
  本文生成           -> client_for_role("text", account_type="new_account_daily")
```

## GUI dry-run の確認結果

実APIは呼ばず、GUI相当の保存・生成起動フローを mock / dry-run で確認。

確認内容:

- `tools/settings_manager.py` の `.env` 読み書き処理で、GUI選択相当の provider/model が保存される。
- GUIの「今すぐ生成」では、subprocess 起動前に `save_env(show_message=False)` が実行される。
- これにより、GUIで選んだ provider/model が `.env` に反映されてから実アプリ生成処理が起動する。
- `TEXT_LLM_PROVIDER=openai` の場合、本文生成は `OpenAIClient.generate_text` 側へ分岐。
- `TEXT_LLM_PROVIDER=gemini` の場合、本文生成は `GeminiClient.generate_text` 側へ分岐。
- 画像プロンプト生成は `IMAGE_PROMPT_LLM_PROVIDER` を使う。
- 品質チェックは `QUALITY_CHECK_LLM_PROVIDER` を使う。
- ログに `provider` / `model` / `function` / `account_type` が出る。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の3アカウントで routing を確認。

## 実施したテスト

実APIは禁止のため、すべて mock / dry-run。

テストファイル:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\01_context01_myself\tests\test_provider_routing_runtime.py
```

実施した確認:

- GUI保存相当で `.env` に provider/model が反映される。
- GUI生成フローが subprocess 起動前に `save_env(show_message=False)` を実行する。
- `TEXT_LLM_PROVIDER=openai` で OpenAI 側へ分岐する。
- `TEXT_LLM_PROVIDER=gemini` で Gemini 側へ分岐する。
- `IMAGE_PROMPT_LLM_PROVIDER` が本文providerと混線しない。
- `QUALITY_CHECK_LLM_PROVIDER` が本文providerと混線しない。
- provider mismatch は `RuntimeError` で停止する。
- `yokaze_daily` / `ai_pickup` / `new_account_daily` の各アカウントで `account_type` 付きログが出る。
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

```text
yokaze_daily/main.py
new_account_daily/main.py
ai_pickup/score_and_draft.py
ai_pickup/recommend_today_post.py
ai_pickup/x_research_analyze.py
```

補足:

以下の provider client 本体内の `requests.post` は、今回禁止した「生成フローからの直呼び」には含めない。

```text
shared/llm/gemini_client.py
shared/llm/openai_client.py
shared/image_pipeline/openai_image_client.py
```

## 未解決事項

- `01_context01_myself` が Git リポジトリではない。
- 実アプリのコード変更そのものは GitHub に push できていない。
- GitHub上で実コード差分をレビューできる状態になっていない。
- 実API疎通確認は未実施。ユーザー許可があるまで実行しない。
- `TEXT_LLM_PROVIDER` 未設定時の default は既存互換の `gemini` のまま。GUI default の `openai` に合わせるかは未決定。

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

## 今後の運用メモ

このセッションでは、安全な開発操作は確認なしで進める。

自動で進める操作:

- `git add`
- `git commit`
- `git push`
- `__pycache__` 削除
- reports / docs 更新
- モックテスト実行
- dry-run
- ログ生成
- markdown生成

必ず事前確認する操作:

- 実API呼び出し
- `.env` 変更
- APIキー変更
- requirements変更
- pip install
- ファイル大量削除
- move / rename
- GUI設定変更
- 本番投稿
- 外部通信
- OS設定変更
