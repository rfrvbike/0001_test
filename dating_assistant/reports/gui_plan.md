# dating_assistant GUI化設計

作業No.: 100
更新日: 2026-06-07
対象: dating_assistant / マッチングアプリ会話支援

## 目的

既存CLIで行っているプロフィール登録、相手管理、会話履歴追加、候補生成、送信済み記録、ダッシュボード確認を、実運用で迷わず扱えるローカルGUIに整理する。

今回の作業では設計のみを行い、GUI本体の大きな実装は行わない。

## 非目的

- マッチングアプリへの自動送信は行わない。
- スクリーンショット画像、顔写真、本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しない。
- `data/local/` と `outputs/local/` 配下をGit管理しない。
- 実LLM API呼び出しを勝手に行わない。
- 外部投稿、X投稿、Discord接続は行わない。

## GUI方式比較

| 方式 | 長所 | 短所 | 適性 |
| --- | --- | --- | --- |
| Tkinter | Python標準で追加依存が少ない。ローカル完結しやすい。 | 入力フォーム、表、プレビュー、状態管理が増えると画面づくりが重くなる。見た目の調整も手間。 | 小さな管理ツール向き。今回の初期GUIには可能だが、拡張時に窮屈。 |
| Streamlit | テキストエリア、セレクト、表、タブ、確認ボタンを短く作れる。ローカルブラウザで使いやすい。既存Pythonロジックを再利用しやすい。 | Web UI用の軽い依存が増える。デスクトップアプリ単体配布には向かない。 | 最初の実用GUIとして最有力。 |
| Flask / FastAPI + HTML | UIとAPIを分離でき、将来の本格Web化に向く。 | HTML/CSS/JS/API設計が必要で、初期実装が大きくなる。 | 将来、複数画面や認証を持つ本格アプリにする場合向き。 |
| PySide / PyQt | 本格的なデスクトップアプリを作れる。表や複雑な操作に強い。 | 依存が重く、実装量が多い。配布や環境差分の注意が増える。 | 長期的に専用アプリ化する場合向き。 |

## 推奨方式

初期実装は **Streamlit** を推奨する。

理由:

- 既存のCLI処理をPython関数として呼び出しやすい。
- プロフィール貼り付け、会話履歴貼り付け、候補文プレビュー、ダッシュボード表示を1画面またはタブで素早く作れる。
- 自動送信を実装せず、「候補確認」「手動送信後の記録」という現在の安全運用と相性がよい。
- 設計変更が起きても画面を試しながら小さく直せる。

## 既存CLIとGUI操作の対応

| GUIでの操作 | 既存CLI | GUIでの扱い |
| --- | --- | --- |
| 実プロフィール作成 | `real-profile-create` | フォームまたは貼り付けからローカルYAMLへ保存する。 |
| 実プロフィール確認 | `real-profile-show` | PIIを含まない範囲で要約表示する。 |
| リハーサル | `real-profile-rehearse` | 候補品質確認用の別タブにする。 |
| 相手作成 | `partner-create` | 実プロフィール選択後、相手情報をフォームで作成する。 |
| 相手一覧 | `partner-list` / `partner-dashboard` | 要対応、返信待ち、アーカイブを分けて表示する。 |
| 相手詳細 | `partner-show` / `partner-timeline` | 会話履歴、候補、状態、メモをまとめて表示する。 |
| 相手発言追加 | `partner-add-turn --speaker partner` | 会話履歴インポートまたは手動入力で追加する。 |
| 自分発言追加 | `partner-add-turn --speaker user` | 手動送信済みの内容だけを追加する。 |
| 初回候補生成 | `partner-generate-first` | プレビュー表示まで。自動送信しない。 |
| 返信候補生成 | `partner-generate-reply` | プレビュー表示まで。自動送信しない。 |
| 誘い候補生成 | `partner-generate-invite` | ステージ条件を満たす場合のみ表示候補にする。 |
| 送信済み記録 | `partner-mark-sent` | 確認チェック後にだけ実行する。 |
| 候補破棄 | `partner-discard-suggestion` | 候補単位で破棄ボタンを出す。 |
| 状態更新 | `partner-update-status` | 原則は会話追加と候補処理から自動更新し、手動変更は詳細画面に限定する。 |
| メモ追加 | `partner-note` | 連絡方針や注意点だけを保存し、個人情報は保存しない。 |
| アーカイブ | `partner-archive` / `partner-unarchive` | 確認付きの操作にする。 |

## 画面構成案

### 1. ダッシュボード

- 要対応の相手を上部に表示する。
- 返信待ち、アーカイブ済み、下書き中を分ける。
- `pending_suggestions` がある相手は「候補確認待ち」として目立たせる。
- `conversation_stage` と `next_action` を並べて表示する。

### 2. プロフィール取り込み

- ユーザー本人プロフィールを貼り付ける入力欄を用意する。
- 保存前に、保存される項目だけをプレビューする。
- 本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスらしき文字列があれば警告する。
- 保存先は `dating_assistant/data/local/real_profiles/` に限定する。

### 3. 相手作成・プロフィール貼り付け

- 相手プロフィールを貼り付け、趣味、雰囲気、会話のきっかけだけを構造化する。
- 外見情報は保存しても会話生成の中心にしない。
- 相手プロフィールと自分の実プロフィールを紐づけてpartnerを作る。
- 保存先は `dating_assistant/data/local/partners/` に限定する。

### 4. 会話履歴インポート

- マッチングアプリから手動コピーした会話テキストを貼り付ける。
- 送信者を「自分」「相手」に手動で割り当てられるプレビュー画面を挟む。
- 日時が取れる場合は保存し、取れない場合は順序のみ保存する。
- インポート前に既存履歴との差分を表示し、二重登録を避ける。
- スクリーンショット画像そのものは保存しない。

### 5. 候補確認

- 候補文、生成理由、注意点を並べて表示する。
- 「コピー用テキスト」を1クリックで選択できる形にする。
- 「手動で送信した」チェックを入れた場合のみ `partner-mark-sent` 相当の処理を実行する。
- 送信していない文は送信済みにしない。

## 会話履歴インポートのデータ変換案

入力例は実データではなく、ダミーテキストだけを使う。

```text
相手: こんばんは。週末は何してました？
自分: カフェで少しゆっくりしてました。
相手: いいですね。落ち着く場所好きです。
```

変換後の内部イメージ:

```yaml
conversation_history:
  - speaker: partner
    text: こんばんは。週末は何してました？
    source: manual_import
  - speaker: user
    text: カフェで少しゆっくりしてました。
    source: manual_import
  - speaker: partner
    text: いいですね。落ち着く場所好きです。
    source: manual_import
```

変換ルール:

- `自分`, `自分:`, `me`, `user` は `speaker: user` に寄せる。
- `相手`, `相手:`, `partner` は `speaker: partner` に寄せる。
- 判定できない行は保存前プレビューで手動指定にする。
- 連続する同一話者の短文は、保存前に結合するか個別保存するか選べるようにする。
- インポート後は `message_state` を再計算し、最後の発言者に応じて `awaiting_user_action` と `awaiting_partner_reply` を更新する。

## partner / profile 紐づけ

GUIでは次の順序で紐づける。

1. 自分の実プロフィールを選択する。
2. 相手プロフィールを貼り付ける、または既存partnerを選ぶ。
3. 会話履歴を貼り付ける。
4. プレビューで相手ID、実プロフィールID、会話履歴の保存先を確認する。
5. 保存する。

安全条件:

- 既存partnerにインポートする場合は、partner IDを明示表示する。
- 新規partner作成時は、同じ表示名や同じプロフィール要約が既にないか警告する。
- `data/local/` 配下以外には保存しない。

## 進行ステージ設計

既存の `status`, `next_action`, `message_state`, `pending_suggestions` に加えて、次の任意フィールドを追加する。

```yaml
conversation_stage: opening
round_count: 0
phone_suggest_ready: false
phone_suggested_at: null
phone_done: false
meet_suggest_ready: false
meet_suggested_at: null
last_human_confirmed_action: null
```

### フィールド定義

| フィールド | 意味 |
| --- | --- |
| `conversation_stage` | 会話の進行段階。候補生成とダッシュボード表示に使う。 |
| `round_count` | 相手発言と自分発言の往復数。電話提案の早すぎ防止に使う。 |
| `phone_suggest_ready` | 電話提案を検討してよい状態。自動提案ではなく候補表示の許可。 |
| `phone_suggested_at` | 電話提案候補を出した日時。 |
| `phone_done` | 実際に電話したことをユーザーが手動で記録した状態。 |
| `meet_suggest_ready` | 会う提案を検討してよい状態。電話後または十分な会話後に立てる。 |
| `meet_suggested_at` | 会う提案候補を出した日時。 |
| `last_human_confirmed_action` | ユーザーが最後に確認して実行した操作。監査用。 |

### `conversation_stage` 候補

- `opening`: 初回または序盤。挨拶、共通点、軽い質問。
- `chatting`: 通常会話。相手の温度感を見ながら返信。
- `rapport`: 2〜3往復以上あり、会話が自然に続いている。
- `phone_ready`: 電話提案を検討してよい。
- `phone_suggested`: 電話提案候補を出した、または手動送信済み。
- `phone_done`: 電話済み。
- `meet_ready`: 会う提案を検討してよい。
- `meet_suggested`: 会う提案候補を出した、または手動送信済み。
- `paused`: 返信待ち、温度感低下、または保留。
- `archived`: 対象外または終了。

既存YAMLとの互換性のため、これらのフィールドがない場合は初期値を補完する。

## 電話提案までの流れ

電話提案は2〜3往復後を基本にする。

判定条件:

- `round_count >= 2` を目安にする。
- 相手が質問を返している、または会話を広げている。
- 返信が極端に短くない。
- 相手が不安そう、忙しそう、警戒していそうな文脈では出さない。
- 初回メッセージや外見だけの流れでは出さない。

候補文の方向性:

- 軽く、断りやすくする。
- 「よかったら」「無理なければ」を使い、圧を下げる。
- 長電話や即日通話を前提にしない。

例:

```text
メッセージだと少しずつになっちゃうので、もし抵抗なければ今度10分くらい電話で話してみませんか？
```

## 電話後に会う提案へ進む流れ

会う提案は、電話済みまたは十分に自然な会話が続いている場合に限定する。

判定条件:

- `phone_done: true` または `conversation_stage: meet_ready`。
- 相手が会話に前向き。
- 場所や時間を一方的に決めない。
- 最初から長時間、遠出、密室、夜遅い予定に寄せない。

候補文の方向性:

- 短時間、明るい時間、カフェやご飯など自然な予定にする。
- 相手が断りやすい余白を残す。

例:

```text
この前話していて楽しかったので、よかったら今度カフェかご飯でも行きませんか？
```

## 候補生成の安全ゲート

- `opening` では電話や会う提案を出さない。
- `round_count < 2` では原則 `phone_suggest_ready` にしない。
- `phone_done` がない状態では、会う提案を強く出さない。
- `pending_suggestions` が残っている場合は、新しい候補生成より確認を優先する。
- 候補文は必ずユーザーが確認し、手動で送る。
- GUIからマッチングアプリに送信する機能は作らない。

## 最小GUI実装計画

### 作業No.108

- partnerビューに「候補生成」セクションを追加する。
- partner状態から初回メッセージ候補と返信候補を自動判定し、既存のlocal生成ロジックだけを呼び出す。
- 生成結果は `pending_suggestions` にlocal保存する。自動送信、外部投稿、実LLM API呼び出しは行わない。
- `pending_suggestions` が残っている場合、相手返信待ち、archived、情報不足の場合は新規生成を止める。
- `partner-mark-sent` 相当のボタンは今回追加しない。

### 作業No.109

- pending_suggestions欄に、安全確認付きの送信済み記録UIを追加する。
- 「この候補を実際に手動送信した」確認チェックがONの場合だけ、送信済み記録ボタンを有効化する。
- 候補本文をそのまま送った場合は `suggestion_id` 指定相当で記録し、pending suggestionを `sent` に更新する。
- 修正文を送った場合はcustom text指定相当で会話履歴へuser発話を追加する。元候補がpendingに残る場合があることをGUI上で案内する。
- この操作はlocal YAMLへの記録のみで、マッチングアプリへの送信、自動送信、外部通信は行わない。
- 候補破棄ボタンは作業No.110で追加する。

### 作業No.110

- pending_suggestions欄に、安全確認付きの候補破棄UIを追加する。
- 「この候補を未使用候補として破棄する」確認チェックがONの場合だけ、破棄ボタンを有効化する。
- 破棄理由入力欄とプレビューを表示し、既存の `partner-discard-suggestion` 相当のlocal処理を呼び出す。
- 候補破棄では `conversation_history` を変更しない。timeline/activity_logには破棄記録を残す。
- archived partnerでは破棄不可にする。
- この操作はlocal整理のみで、マッチングアプリへの送信・削除、自動操作、外部通信は行わない。

### 作業No.111

- GUI通し確認を実施し、主要画面と主要local操作が実運用前に破綻していないことを確認した。
- Streamlit AppTestで、partnerビュー、profile登録、partner作成、会話履歴インポート、候補生成、送信済み記録、候補破棄のUI表示を確認した。
- 一時ディレクトリのダミーデータで、profile保存、partner作成、会話履歴追加、返信候補生成、suggestion_id送信済み記録、custom text送信済み記録、候補破棄のlocal動作を確認した。
- pendingがある場合の生成ボタン文言を「候補生成不可」に調整した。
- custom text送信済み記録後の案内を、追加済みの候補破棄UIへ誘導する文言に調整した。
- `py_compile` と全体unittestは通過した。
- 残課題として、README/使い方整理、実運用時の注意事項整理、最終受け入れチェックを次作業で行う。

### 作業No.113

- GUI版を一旦完成扱いにできるよう、READMEと運用レポートへ使い方を整理した。
- Streamlit venvのセットアップ手順、GUI起動手順、起動確認用のheadlessコマンドを明記した。
- プロフィール登録、partner作成、会話履歴インポート、候補生成、人間確認、手動送信、送信済みlocal記録、候補破棄までの実運用フローを整理した。
- 電話提案と会う提案は、2から3往復後の温度感確認を前提にし、早すぎる誘いを避ける方針として明記した。
- 自動送信、外部投稿、実LLM API呼び出し、マッチングアプリ操作、local実データのGit管理を行わない安全ルールを再確認した。
- 新機能の大規模追加は行わず、ドキュメント整理と完成チェックに限定した。

### 作業No.116

- プロフィール登録画面に、プロフィール情報まとめ貼り付け欄と抽出プレビューを追加した。
- 貼り付け内容から display_name, app_name, age, area, profile_text, interests, photo_memo, avoid_topics, conversation_hooks, first_message_hints, safety_notes をlocalで簡易抽出できるようにした。
- 保存済みreal_profileの検索、選択中プロフィールの表示、既存partner候補の表示を追加した。
- 候補生成UIに目的選択、文章の雰囲気選択、場所指定欄、生成前チェックを追加した。
- 候補生成は既存のlocal生成を使い、3パターンをpending_suggestionsへ保存する形にした。
- 電話、会う提案、LINE交換は早すぎる可能性を警告し、自動送信やマッチングアプリ操作は追加していない。
- 相手別メモ、送信結果メモ、高度な自動抽出、さらに細かい文章品質改善は次回以降の改善候補として残した。

### Phase 1

- `dating_assistant/gui_app.py` などにStreamlitアプリを追加する。
- 既存CLIをシェル実行するのではなく、可能な範囲で既存のPython関数とストア層を呼び出す。
- 画面は次の5つに絞る。
  - ダッシュボード
  - partner詳細
  - プロフィール貼り付け
  - 会話履歴インポート
  - 候補確認
- 自動送信なし、mark-sentは確認チェック付きにする。

起動例:

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\dating_assistant"
python -m streamlit run gui_streamlit_app.py
```

作業No.104で追加した最小範囲:

- `gui_streamlit_app.py` に「プロフィール登録」タブを追加する。
- 入力項目は label, display_name, app_name, age, area, profile_text, photo_memo, interests, avoid_topics, notes とする。
- 必須項目は label, display_name, profile_text または photo_memo のどちらかとする。
- 保存前に危険語警告と保存プレビューを表示する。
- 保存は `data/local/real_profiles/` 配下のlocal YAMLのみに行う。
- 同じlabelが存在する場合は上書きしない。
- partner作成、候補生成、mark-sentは今回の範囲外とする。

作業No.106で追加する最小範囲:

- `gui_streamlit_app.py` に「会話履歴インポート」タブを追加する。
- 対象partner選択、会話履歴貼り付け欄、自分/相手の発話者ラベル、保存確認チェックを用意する。
- `自分:`, `相手:`, `user:`, `partner:`, `me:`, `you:` の最小形式をturn候補へ変換する。
- 発話者を判定できない行は警告し、自動保存しない。
- 保存前に対象partner、追加予定turn数、speakerごとの発話、警告一覧、保存先をプレビュー表示する。
- 保存は確認チェック後に `data/local/partners/` 配下の選択partner YAMLへ追記する。
- 返信候補生成、mark-sent、自動送信、マッチングアプリ操作は今回の範囲外とする。

作業No.107で追加する最小範囲:

- `gui_streamlit_app.py` に「プロフィールからpartner作成」タブを追加する。
- `data/local/real_profiles/` 配下の保存済みreal_profileを一覧表示し、選択できるようにする。
- 入力項目は real_profile選択、partner display_name、partner app_name、source memo、保存確認チェックとする。
- 保存前にsource real_profile、display_name、app_name、初期status、空のconversation_history、空のpending_suggestions、保存先をプレビュー表示する。
- partner_id採番と保存は既存の `create_partner_from_target_profile` を使い、既存partnerと衝突させない。
- 保存は確認チェック後に `data/local/partners/` 配下のlocal YAMLのみに行う。
- 返信候補生成、mark-sent、自動送信、マッチングアプリ操作は今回の範囲外とする。

### Phase 2

- 会話履歴インポートのパーサーを独立モジュール化する。
- `conversation_stage` 推定を関数化し、単体テストを追加する。
- 電話提案、会う提案のゲート条件をテストする。

### Phase 3

- 候補文の比較、破棄理由、メモ、タイムライン表示を整える。
- 必要ならFlask/FastAPI化やPySide化を再検討する。

## テスト方針

- 既存CLIのテストは維持する。
- GUI本体は薄くし、データ変換、ステージ判定、候補ゲートを関数単位でテストする。
- 会話履歴インポートでは、ダミーデータだけを使う。
- local実データ、実プロフィールYAML、partner実データYAMLはテストに使わない。

## 結論

最初のGUIはStreamlitで小さく作るのがよい。

優先すべき実装は、見た目よりも「貼り付け、プレビュー、保存前確認、候補確認、手動送信後の記録」を安全に短い手順で行えること。

電話提案と会う提案は、`conversation_stage` と `round_count` を使って早すぎる誘いを防ぎ、必ずユーザー確認を挟む設計にする。

### 作業No.117

- No.116で追加したGUI導線を、プロフィール貼り付けから3候補生成までの実運用目線で確認した。
- プロフィール登録では、まとめ貼り付け欄を主導線として明示し、不足分・修正欄は補助入力であることを画面上で分かるようにした。
- 保存前プレビューに未抽出項目と確認メモを追加し、保存前にどこを直すべきか判断しやすくした。
- 候補生成では、日常会話向けの目的を上に置き、電話、会う提案、場所指定、LINE交換など距離が近い目的を下の方へ整理した。
- 初回や1往復目で電話、会う提案、LINE交換、大人っぽい雰囲気を選んだ場合の警告を強め、生成前チェック内だけでなく画面警告として表示する方針にした。
- 候補A/B/Cの使い分けを表示名に含め、どの候補が無難寄りか分かりやすくした。
- 自動送信、外部API通信、マッチングアプリ操作、local実データのGit管理は追加していない。

### 作業No.118

- partnerビューに相手別メモ欄を追加し、返信傾向、反応がよい話題、まだ早そうな誘い方などをlocalのpartner.notesへ追記できるようにした。
- 相手別メモは生成前チェックへ表示し、電話やLINE交換がまだ早そうなメモと目的選択がぶつかる場合に警告する方針にした。
- 送信済み候補に結果ステータスと自由メモを持たせ、返信あり、返信なし、反応よかった、話題が広がった、微妙だった、未確認などを記録できるようにした。
- 最近の送信結果メモは生成前チェックへ表示し、次回以降の判断材料として見られるようにした。
- 相手別メモと送信結果メモには既存の個人情報警告を再利用し、保存前プレビューで注意表示する。
- 自動送信、外部API通信、マッチングアプリ操作、画像保存、local実データのGit管理は追加しない。

### 作業No.119

- custom textを送信済みlocal記録した場合にも、`sent_custom_000001` 形式の安定した `sent_id` を付与する。
- AI候補由来の送信済み記録は `sent_generated_000001` 形式の `sent_id` と `source_type=generated_suggestion` を持たせる。
- 手入力文由来の送信済み記録は `source_type=custom_text` とし、AI候補由来と画面上で区別できるようにする。
- 古いsent済みsuggestionは `legacy_generated_<suggestion_id>` のfallback IDで表示し、結果メモ更新時に `sent_records` へ移行できるようにする。
- 送信結果メモは `sent_id` に紐づけ、最近の送信結果として生成前チェックへ表示する。
- 自動送信、外部API通信、マッチングアプリ操作、画像保存、local実データのGit管理は追加しない。
