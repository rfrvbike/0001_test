# Dating Assistant

マッチングアプリのプロフィール分析、初回文、返信文、誘い文をローカルで下書きするCLIツールです。
実LLM API、外部通信、自動送信、外部投稿は行いません。生成結果は必ず人間が確認してから使用してください。

## 基本コマンド

```powershell
python main.py generate-first --target data/examples/sample_target_cafe_movie.yaml
python main.py generate-reply --target data/examples/sample_target_cafe_movie.yaml --history data/examples/sample_conversation_movie_reply.yaml
python main.py invite --target data/examples/sample_target_cafe_movie.yaml --history data/examples/sample_conversation.yaml
python main.py review --message "確認したい文"
```

`--save-output` を付けると、生成結果をGit管理対象外の `outputs/local/` に保存します。
保存成功時はCLI末尾に `保存しました` と保存先を表示します。

## 相手ごとの管理

相手ごとのプロフィール、会話履歴、分析結果、メモを `data/local/partners/partner_NNN.yaml` に保存できます。
このディレクトリはGit管理対象外です。サンプルは `data/examples/sample_partner_cafe_movie.yaml` にあります。

```powershell
python main.py partner-create --source data/examples/sample_target_cafe_movie.yaml --display-name "カフェ好き" --app-name "sample"
python main.py partner-list
python main.py partner-show --partner-id partner_001
python main.py partner-add-turn --partner-id partner_001 --speaker partner --text "最近は映画をよく見ます"
python main.py partner-generate-first --partner-id partner_001
python main.py partner-generate-reply --partner-id partner_001 --save-output
python main.py partner-generate-invite --partner-id partner_001
python main.py partner-update-status --partner-id partner_001 --status chatting
python main.py partner-note --partner-id partner_001 --text "映画の話題が返信しやすそう"
```

`partner-generate-invite` は、会話量や温度感が不足している場合に無理な誘い文を出しません。
生成コマンドは分析結果と最後の提案文を相手ファイルへ記録しますが、送信は行いません。

## 未送信候補と送信済み管理

`partner-generate-first`, `partner-generate-reply`, `partner-generate-invite` は、一番おすすめの文を
`pending_suggestions` に未送信候補として保存します。AIは自動送信しません。

実際にユーザーがアプリ上で手動送信した後、送信した事実を記録します。

```powershell
python main.py partner-generate-reply --partner-id partner_001
python main.py partner-mark-sent --partner-id partner_001 --suggestion-id suggestion_001
python main.py partner-mark-sent --partner-id partner_001 --text "実際に送った文"
python main.py partner-discard-suggestion --partner-id partner_001 --suggestion-id suggestion_001
```

- 候補をそのまま送った場合は `partner-mark-sent --suggestion-id` を使います。
- 自分で修正して送った文は `partner-mark-sent --text` で登録できます。
- 使わなかった候補は `partner-discard-suggestion` で破棄できます。
- 相手から返信が来たら `partner-add-turn --speaker partner` で記録します。
- 自分が送った文は `partner-mark-sent` または `partner-add-turn --speaker user` で記録します。
- `partner-list` で次の行動と未送信候補数を確認できます。
- `partner-show` で現在の状態、未送信候補、最近の会話を確認できます。

## partner-timeline

相手ごとの会話、候補生成、送信済み化、破棄、メモ、ステータス変更を時系列で確認できます。

```powershell
python main.py partner-timeline --partner-id partner_001
python main.py partner-timeline --partner-id partner_001 --limit 20
python main.py partner-timeline --partner-id partner_001 --limit all
python main.py partner-timeline --partner-id partner_001 --verbose
python main.py partner-timeline --partner-id partner_001 --save-output
```

- 通常表示は直近30件です。
- `--verbose` は会話文や候補文を長めに表示します。
- `--save-output` は確認用タイムラインを `outputs/local/` に保存します。
- タイムライン確認による自動送信や外部通信は行いません。
- 実データはGit管理対象外の `data/local/partners/` と `outputs/local/` に保存します。
- 新しい操作履歴は `activity_log` に記録され、旧partnerデータは空の履歴として読み込めます。

## partner-dashboard

複数人と同時にやり取りする際、今日対応すべき相手、返信待ち、未送信候補、誘い検討、停止中・終了を横断して確認できます。

```powershell
python main.py partner-dashboard
python main.py partner-dashboard --needs-action
python main.py partner-dashboard --waiting
python main.py partner-dashboard --active-only
python main.py partner-dashboard --status chatting
python main.py partner-dashboard --sort received
python main.py partner-dashboard --save-output
```

- `--active-only`: `paused` / `closed` を除外
- `--status`: 指定ステータスのみ表示
- `--needs-action`: 自分の対応待ち、または未送信候補がある相手のみ表示
- `--waiting`: 相手の返信待ちのみ表示
- `--sort`: `updated`, `received`, `sent` の古い順で表示
- `--save-output`: 確認用ダッシュボードを `outputs/local/` に保存

```text
partner-list:
  登録済みpartnerの一覧確認

partner-dashboard:
  返信すべき相手、返信待ち、未送信候補、誘い検討を判断する運用確認
```

ダッシュボードは確認専用で、自動送信や外部通信は行いません。

## 実プロフィールYAML作成補助

スクリーンショット画像そのものは保存せず、読み取ったプロフィール文、趣味、写真の特徴メモだけを手入力してYAML化します。

```powershell
python main.py real-profile-create --label cafe_movie_001 --profile-text "カフェと映画が好きです。" --hobby カフェ --hobby 映画 --photo-memo "落ち着いた雰囲気"
python main.py real-profile-list
python main.py real-profile-show --label cafe_movie_001
```

長いコマンドを書きたくない場合は、対話式で順番に入力できます。

```powershell
python main.py real-profile-create --interactive
python main.py real-profile-create -i
python main.py real-profile-create --interactive --label cafe_movie_001
```

対話式では、label、年齢、プロフィール文、趣味、写真メモ、大まかな地域、関係性希望、補足メモを順番に入力します。
プロフィール文と補足メモは複数行入力でき、空行のみで終了します。趣味と写真メモは1つずつ入力し、空行のみで終了します。
保存前に確認画面が出て、`y` または `Y` を入力した場合だけ保存します。`n` や空欄では保存しません。
`--interactive` 指定時は対話式入力を優先し、`--label` は初期値として利用します。

作成したYAMLは既存のtarget profile形式と互換です。

```powershell
python main.py partner-create --source data/local/real_profiles/cafe_movie_001.yaml --display-name "カフェ映画の人" --app-name pairs
```

実運用前に、real profileからpartner作成と初回候補生成までを一括確認できます。

```powershell
python main.py real-profile-rehearse --label cafe_movie_001 --display-name "カフェ映画の人" --app-name pairs
python main.py real-profile-rehearse --path data/local/real_profiles/cafe_movie_001.yaml --display-name "カフェ映画の人" --app-name pairs
python main.py real-profile-rehearse --label cafe_movie_001 --display-name "カフェ映画の人" --app-name pairs --save-output
python main.py real-profile-rehearse --label cafe_movie_001 --display-name "カフェ映画の人" --app-name pairs --dry-run
```

通常実行ではpartnerを作成し、初回メッセージの一番おすすめを `pending_suggestions` に保存します。
dry-runではreal profileを読み込み、初回候補を生成しますが、partner YAML、pending_suggestions、activity_logは保存しません。
このコマンドも自動送信はしません。実際に送った後は以下で記録します。

```powershell
python main.py partner-mark-sent --partner-id partner_001 --suggestion-id suggestion_001
```

- `--label` は英数字、ハイフン、アンダースコアのみ使用できます。
- 実プロフィールはGit管理対象外の `data/local/real_profiles/` に保存します。
- スクリーンショット画像そのもの、顔写真そのものは保存しないでください。
- 本名、勤務先、学校名、SNS ID、LINE ID、最寄り駅、住所、電話番号、メールアドレスは入力しないでください。
- 危険語の警告が出た場合は、保存内容を見直してください。
- 個人情報警告は補助機能であり、完全な検出ではありません。

## ステータス

`new_profile`, `first_message_suggested`, `first_message_sent`, `chatting`, `warm_chat`,
`invite_ready`, `invited`, `scheduling`, `met`, `paused`, `closed`

## プライバシー

- 本名、勤務先、学校名、SNS ID、LINE ID、最寄り駅を保存しないでください。
- スクリーンショット画像そのものを保存しないでください。必要な特徴だけを短いメモとして入力してください。
- 個人を特定できる情報、連絡先、住所、詳細な行動履歴を入力しないでください。
- `data/local/partners/` と `outputs/local/` はGit管理対象外ですが、端末上のファイル管理も慎重に行ってください。
- テストは `DATING_ASSISTANT_PARTNER_DIR` で一時ディレクトリへ切り替え、実データを汚しません。

## サンプル出力の再生成

```powershell
python tools/regenerate_example_outputs.py --dry-run
python tools/regenerate_example_outputs.py
```

## テスト

```powershell
python -m unittest discover tests
```
