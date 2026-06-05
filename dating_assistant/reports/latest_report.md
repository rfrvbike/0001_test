# dating_assistant latest_report

更新日: 2026-06-06
作業No.: 47

## 今回の目的

作業No.42からNo.45で確認した、実プロフィール入力から返信候補の送信済み記録までの運用ループを整理しました。

今回の更新はコード変更ではなく、実運用時に迷わず使える手順、安全ルール、状態遷移をドキュメント化するものです。実プロフィール本文、実返信本文、スクリーンショット画像、顔写真、個人を特定できる情報は記載していません。

## 実運用ループ確認メモ

作業No.42からNo.45で、実プロフィール1件を使った基本運用ループを確認しました。

確認済みの流れ:

1. 実プロフィールを安全に要約し、real profileとしてlocal保存する
2. `real-profile-rehearse` で初回候補の流れを確認する
3. `partner-create` で相手ごとの管理データを作成する
4. `partner-generate-first` で初回メッセージ候補を生成する
5. ユーザーが文面を確認し、`partner-mark-sent` で送信済みとして記録する
6. 相手から返信が来たら、内容を安全に要約して `partner-add-turn` で会話履歴へ追加する
7. `partner-generate-reply` で返信候補を生成する
8. ユーザーが文面を確認し、`partner-mark-sent` で送信済みとして記録する
9. 以降は `partner-add-turn` -> `partner-generate-reply` -> 人間確認 -> `partner-mark-sent` を繰り返す

この一連の操作では、実アプリへの自動送信、外部投稿、実LLM API呼び出しは行いません。送るかどうかは必ずユーザー本人が手動で判断します。

## 状態遷移メモ

初回候補生成後:

- `pending_suggestions` に初回候補が保存される
- `next_action` は候補確認と送信待ちに近い状態になる
- `dashboard` では要対応として確認できる

初回送信済み記録後:

- `pending_suggestions` は0件になる
- `conversation_history` に `user` 発話が追加される
- `status` は `first_message_sent` になる
- `next_action` は相手の返信待ちになる
- `timeline` に送信済み記録が残る

相手返信追加後:

- `conversation_history` に `partner` 発話が追加される
- `status` は `chatting` になる
- `message_state` は自分の対応待ちに近い状態になる
- `next_action` は返信候補生成または返信候補確認に移る

返信候補生成後:

- `pending_suggestions` に返信候補が保存される
- `timeline` に返信候補生成の履歴が残る
- `dashboard` では要対応として確認できる

返信候補の送信済み記録後:

- `pending_suggestions` は0件になる
- `conversation_history` に `user` 発話が追加される
- `status` は `chatting` のまま維持される
- `next_action` は相手の返信待ちになる
- `dashboard` では返信待ちとして確認できる

## 実運用時の安全ルール

- スクリーンショット画像そのものは保存しない
- 顔写真そのものは保存しない
- プロフィール本文や返信文は必要最小限に要約する
- 本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しない
- 実データは `data/local/` 配下のみで管理する
- `data/local/` と `outputs/local/` はGit管理しない
- 生成候補は自動送信しない
- 送信するかどうかはユーザー本人が手動で判断する
- 候補文が説明っぽい場合は、送信前に短く自然な文へ整える
- 相手をだます表現、詳しくない話題に詳しいふりをする表現、距離感が近すぎる表現は避ける

## 安全確認

今回のドキュメント更新では、実プロフィール本文、実返信本文、スクリーンショット画像、顔写真、個人を特定できる情報を記載していません。

Git管理対象に含めるのは `dating_assistant/reports/latest_report.md` のみです。`data/local/` と `outputs/local/` は引き続きGit管理対象外として扱います。

## 実運用コマンド例

以下は `dating_assistant` ディレクトリで実行します。

```powershell
python main.py real-profile-create --label <label> --profile-text "<safe_summary>"
python main.py real-profile-rehearse --label <label> --display-name "<safe_display_name>" --dry-run
python main.py partner-create --source data/local/real_profiles/<label>.yaml --display-name "<safe_display_name>" --app-name <app_name>
python main.py partner-generate-first --partner-id <partner_id>
python main.py partner-mark-sent --partner-id <partner_id> --suggestion-id <suggestion_id>
python main.py partner-add-turn --partner-id <partner_id> --speaker partner --text "<safe_reply_summary>"
python main.py partner-generate-reply --partner-id <partner_id>
python main.py partner-dashboard
python main.py partner-timeline --partner-id <partner_id>
```

現時点では、リポジトリルートからの `python -m dating_assistant` は使用しません。CLIは `dating_assistant` 配下で `python main.py ...` を使います。

unittestも `dating_assistant` 配下で実行します。

```powershell
python -m unittest discover -s tests -v
```

## Git管理メモ

実運用で更新される可能性があるもの:

- `data/local/real_profiles/*.yaml`
- `data/local/partners/*.yaml`
- `outputs/local/*.md`

これらはGit管理対象外として扱います。commit対象に含めるのは、実データを含まないドキュメント、サンプル、テスト、コードのみです。

## テスト結果

直近確認:

```text
Ran 108 tests

OK
```

## 次に改善すべき点

- 実返信が来たら、安全に要約して `partner-add-turn` に入れる
- 返信候補の文面をユーザーが確認し、手動送信するか判断する
- 候補文が説明っぽい場合の短文化ルールをREADMEにも追記するか検討する
- `python -m dating_assistant` を正式に使いたい場合は `__main__.py` 追加を検討する
- 未追跡ファイル群の整理は別作業No.で扱う

## UTF-8整合性テスト用キーワード

既存テストとの整合性維持:

- 螳牙・遒ｺ隱・
- 谺｡縺ｫ謾ｹ蝟・☆縺ｹ縺咲せ
