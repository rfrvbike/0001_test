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
python main.py partner-archive --partner-id partner_001 --reason "検証用データ整理"
python main.py partner-unarchive --partner-id partner_001 --status paused
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
python main.py partner-dashboard --include-archived
python main.py partner-dashboard --archived-only
python main.py partner-dashboard --sort received
python main.py partner-dashboard --save-output
```

- `--active-only`: `paused` / `closed` / `archived` を除外
- `--status`: 指定ステータスのみ表示
- `--needs-action`: 自分の対応待ち、または未送信候補がある相手のみ表示
- `--waiting`: 相手の返信待ちのみ表示
- `--include-archived`: アーカイブ済みも表示
- `--archived-only`: アーカイブ済みのみ表示
- `--sort`: `updated`, `received`, `sent` の古い順で表示
- `--save-output`: 確認用ダッシュボードを `outputs/local/` に保存

```text
partner-list:
  登録済みpartnerの一覧確認

partner-dashboard:
  返信すべき相手、返信待ち、未送信候補、誘い検討を判断する運用確認
```

ダッシュボードは確認専用で、自動送信や外部通信は行いません。

## partnerのアーカイブ

検証用partnerや終了したpartnerは、削除せずにアーカイブできます。
アーカイブ済みpartnerは通常の `partner-dashboard` からは非表示になり、実データYAMLは `data/local/partners/` に残ります。

```powershell
python main.py partner-archive --partner-id partner_001 --reason "検証用データ整理"
python main.py partner-unarchive --partner-id partner_001 --status paused
python main.py partner-dashboard --include-archived
python main.py partner-dashboard --archived-only
```

- アーカイブは削除ではありません。
- 誤ってアーカイブした場合は `partner-unarchive` で `paused`, `chatting`, `warm_chat`, `invite_ready` に戻せます。
- `partner-show` ではアーカイブ済みであることを明示します。
- `partner-timeline` にはアーカイブ/解除イベントが残ります。
- `data/local/partners/` はGit管理対象外です。

## partnerを一括アーカイブする

検証用partnerや終了済みpartnerを、削除せずにまとめてアーカイブできます。
デフォルトはdry-runで、`--apply` を付けない限りpartner YAMLは変更されません。

```powershell
python main.py partner-bulk-archive --contains "運用テスト" --dry-run
python main.py partner-bulk-archive --contains "運用テスト" --apply --reason "検証用データ整理"
python main.py partner-bulk-archive --partner-id partner_001 --partner-id partner_002 --dry-run
python main.py partner-bulk-archive --status paused --dry-run
```

- `--contains`: `display_name` に指定文字列を含むpartnerを対象にします。
- `--status`: 指定statusのpartnerを対象にします。
- `--partner-id`: 指定したpartnerだけを対象にします。複数指定できます。
- `--include-archived`: 既に `archived` のpartnerもdry-run表示対象に含めます。
- `--apply`: 実際に `archived` へ変更します。条件なしの `--apply` は禁止です。
- `--reason`: 一括アーカイブ理由をactivity_logへ残します。
- `--force`: `--apply` の対象が多い場合の確認用です。

一括アーカイブは削除ではありません。実partner YAMLは `data/local/partners/` に残り、このディレクトリはGit管理対象外です。既に `archived` のpartnerは再archiveせずskipします。

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
`invite_ready`, `invited`, `scheduling`, `met`, `paused`, `closed`, `archived`

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

## Streamlit GUI

GUI版は、CLIで行っていた相手管理、プロフィール登録、会話履歴インポート、候補生成、送信済み記録、候補破棄をローカル画面で操作するための補助画面です。
マッチングアプリへの自動送信、外部投稿、外部API通信、実LLM API呼び出しは行いません。

かんたん起動:

リポジトリルートにある次のbatファイルをダブルクリックします。

```text
start_dating_assistant_gui.bat
```

起動後、ブラウザでdating_assistant GUIが開きます。
自動で開かない場合は、PowerShellに表示されるURLをブラウザで開いてください。
通常は次のURLです。

```text
http://localhost:8501
```

このbatはGUIを起動するだけです。
マッチングアプリへの自動送信、マッチングアプリ操作、外部投稿、実LLM API呼び出しは行いません。

初回セットアップ:

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test"
python -m venv .venv_dating_gui
.\.venv_dating_gui\Scripts\python.exe -m pip install -r dating_assistant/requirements-gui.txt
```

起動:

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test"
.\.venv_dating_gui\Scripts\python.exe -m streamlit run dating_assistant/gui_streamlit_app.py
```

起動確認だけを行う場合:

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test"
.\.venv_dating_gui\Scripts\python.exe -m streamlit run dating_assistant/gui_streamlit_app.py --server.headless true --browser.gatherUsageStats false --server.port 8501
```

基本フロー:

1. GUIを起動します。
2. プロフィール登録タブで、相手プロフィールのテキストや写真印象メモを「プロフィール情報まとめ貼り付け欄」にまとめて貼り付けます。
3. 抽出プレビューを確認し、抽出できなかった項目や違う項目だけを不足分・修正欄で直してreal profileとして保存します。
4. 保存済みreal profileを検索・選択し、内容を確認してpartnerを作成します。
5. 必要に応じて、会話履歴インポートで既存のやり取りをpartnerへ記録します。
6. partnerを選択し、プロフィール、会話履歴、timeline、pending_suggestionsを確認します。
7. 相手別メモに、返信傾向、反応がよい話題、まだ早そうな誘い方などを必要に応じて追記します。
8. 目的と文章の雰囲気を選び、生成前チェックで会話ステージ、温度感、次の一手おすすめ、誘い系アクションの可否を確認してから初回候補または返信候補を3つ生成します。
9. 候補文を人間が確認し、必要なら短く自然な文へ整えます。
10. 実際のマッチングアプリ上では、ユーザー本人が手動で送信します。
11. 手動送信した後だけ、GUIで送信済みlocal記録を行います。AI候補をそのまま送った場合も、修正した手入力文を送った場合も、送信済み記録にはlocal用の `sent_id` が付きます。
12. 送信結果メモに、返信あり、話題が広がった、微妙だった、未確認などの結果を追記します。結果メモは `sent_id` に紐づくため、どの文章への反応だったか後から確認できます。
13. 相手から返信が来たら、会話履歴インポートまたは相手返信追加で記録し、次の返信候補を生成します。
14. 使わなかった候補は、必要に応じて候補破棄で整理します。

運用ルール:

- GUIは送信文候補を `pending_suggestions` に保存するだけで、自動送信しません。
- 送信済み記録は、ユーザーが実際に手動送信した後だけ行います。
- AI候補由来の送信済み記録は `generated_suggestion`、手入力文由来の送信済み記録は `custom_text` として区別されます。
- 候補破棄は `conversation_history` を変更せず、マッチングアプリ側の内容も削除しません。
- 相手別メモと送信結果メモはlocalのpartnerデータに保存され、次回以降の生成前チェックや判断材料として表示されます。
- 生成前チェックでは、会話履歴、相手別メモ、最近の送信結果メモをもとに、会話ステージ、温度感と理由、次の一手おすすめ、電話・会う提案・LINE交換・大人っぽい雰囲気の可否を表示します。
- `data/local/` と `outputs/local/` はGit管理対象外です。
- スクリーンショット画像そのもの、顔写真そのもの、本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しません。
- 相手別メモや送信結果メモにも、本名、勤務先、学校名、SNS ID、LINE ID、住所、電話番号、メールアドレスを書かないでください。
- 生成候補は必ず人間が確認し、相手との温度感に合わない場合は送らないでください。
- 電話、会う提案、LINE交換、少し大人っぽい雰囲気は目的として選べますが、GUIでは下の方に並べ、早すぎる可能性を警告します。実際に送るかはユーザーが判断してください。
- LINE交換や大人っぽい雰囲気は、電話・会う提案よりさらに慎重に扱います。初回や1往復目では原則として避け、表示された可否判定と注意点を確認してください。

電話・会う提案の目安:

- 1往復目はプロフィールに自然に触れる軽い質問を優先します。
- 2往復目は共感と相手の好みを深掘りしすぎない質問にします。
- 2から3往復して温度感が良い場合だけ、短時間で断りやすい電話提案を検討します。
- 電話後、または十分に自然な会話が続いた後に、カフェやご飯など軽い会う提案を検討します。
- 相手の反応が薄い場合や距離感が近すぎる場合は、電話や会う提案へ進めません。

## テスト

```powershell
python -m unittest discover tests
```
