# dating_assistant latest_report

最新更新日: 2026-06-07
最新作業No.: 116

## 作業No.116 GUI実運用入力フロー改善

Streamlit GUIの実運用開始後に使いやすくするため、プロフィール登録、保存済みプロフィール選択、候補生成まわりを改善しました。

実装した内容:

1. プロフィール情報まとめ貼り付け欄
2. 貼り付け内容からのlocal簡易抽出
3. 抽出結果の保存前プレビュー
4. 保存済みreal_profileの検索と選択中プロフィール表示
5. 既存partner候補の表示
6. 候補生成の目的選択
7. 文章の雰囲気選択
8. 場所指定つき会う提案の入力欄
9. 生成前チェック
10. 3パターンの候補生成とpending_suggestionsへのlocal保存

安全確認:

- 実LLM API呼び出しは追加していません。
- 自動送信機能は追加していません。
- マッチングアプリ操作機能は追加していません。
- data/local/ と outputs/local/ の実データはGit管理しません。
- 電話、会う提案、LINE交換は早すぎる場合に警告し、最終判断はユーザーが行います。

次回以降の改善候補:

- 相手別メモ
- 送信結果メモ
- より高度な自動抽出
- 文章品質のさらに細かい改善

最新更新日: 2026-06-07
最新作業No.: 113

## 作業No.113 GUI版完成チェック

作業No.108からNo.112で追加・確認したStreamlit GUIについて、READMEと運用レポートを整理し、GUI版を一旦完成扱いにできる状態を確認しました。
今回の作業はドキュメント整理と完成チェックに限定し、新機能の大規模追加は行っていません。

整理した内容:

1. Streamlit venvのセットアップ手順
2. GUI起動手順
3. headlessでのGUI起動確認手順
4. プロフィール登録からpartner作成までの流れ
5. 会話履歴インポートから候補生成までの流れ
6. 人間確認、手動送信、送信済みlocal記録の流れ
7. 未使用候補の破棄手順
8. 電話提案と会う提案の温度感ルール
9. 自動送信・外部通信・実LLM API呼び出しを行わない安全ルール

GUIで扱える主な操作:

- partner一覧表示
- partner選択
- partner状態表示
- conversation_history表示
- pending_suggestions表示
- timeline表示
- プロフィール登録フォーム
- 会話履歴インポート
- 保存済みprofileからpartner作成
- 初回候補生成
- 返信候補生成
- 送信済みlocal記録
- 候補破棄

実運用フロー:

1. GUIを起動します。
2. プロフィール登録タブで、相手プロフィールを安全な要約として入力し、real profileとして保存します。
3. 保存済みreal profileからpartnerを作成します。
4. 必要に応じて会話履歴をインポートします。
5. partnerを選択し、状態、会話履歴、timeline、pending_suggestionsを確認します。
6. 初回候補または返信候補を生成します。
7. 候補文は必ず人間が確認し、必要なら自然な短文に整えます。
8. 実際のマッチングアプリではユーザー本人が手動送信します。
9. 手動送信後だけ、GUIで送信済みlocal記録を行います。
10. 相手から返信が来たらlocalに記録し、次の返信候補を生成します。
11. 使わなかった候補は候補破棄で整理します。

電話・会う提案の方針:

- 初回から誘わず、まずプロフィールに自然に触れる。
- 2往復目は共感と軽い質問に留め、深掘りしすぎない。
- 2から3往復して温度感が良い場合だけ、短時間で断りやすい電話提案を検討する。
- 会う提案は、電話後または十分に自然な会話が続いた後に、カフェやご飯など軽めに出す。
- 相手の反応が薄い場合は進めない。

安全確認:

- GUIはマッチングアプリへ自動送信しません。
- GUIは外部投稿を行いません。
- GUIは実LLM API呼び出しを行いません。
- 送信済み記録はlocal YAMLへの記録のみです。
- 候補破棄は `conversation_history` を変更しません。
- `data/local/` と `outputs/local/` はGit管理対象外です。
- スクリーンショット画像そのもの、顔写真そのもの、本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しません。

残課題:

- 大きな未完了機能はありません。
- 今後は実運用しながら、画面表示や文言の細かい使い勝手を必要に応じて改善します。

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

## 候補文の短文化・自然化ルール

生成された候補文は、そのまま送信せず、必ずユーザーが確認します。

候補文が説明っぽい場合は、送信前に以下の方針で短く整えます。

- 1通に入れる話題は1つ、多くても2つまでにする
- 質問は原則1つにする
- 相手のプロフィールに触れたことが自然に伝わる程度にする
- 長い前置きや解説は削る
- 「詳しくないけど」「あまり詳しくないですが」のような言い訳が多すぎる場合は短くする
- 初回から誘わない
- 外見だけを褒めない
- 下心や距離感の近すぎる表現は避ける
- 相手をだます表現や、詳しくない話題に詳しいふりをする表現は避ける
- 最後は相手が返しやすい軽い質問で終える

### 短文化の例

以下は実データではなく、安全なダミー例です。

Before:

```text
自然の写真がとても素敵で、落ち着いた雰囲気が伝わってきました。
カフェもお好きとのことなので、休日はそういう場所でゆっくり過ごされることが多いのでしょうか？
```

After:

```text
自然の写真、雰囲気よくて素敵ですね。
休日はカフェでゆっくりすることが多いですか？
```

Before:

```text
落ち着いたカフェがお好きなんですね。自分もカフェは好きですが、そこまで詳しいわけではないので、もしおすすめのお店などがあれば聞いてみたいです。
```

After:

```text
落ち着いたカフェいいですね。
最近行ってよかったお店とかありますか？
```

## 送信前チェック

送信前に、ユーザーが以下を確認します。

- 自分が実際に言いそうな文か
- 長すぎないか
- 質問が多すぎないか
- 相手のプロフィールを読んだことが自然に伝わるか
- いきなり誘っていないか
- 下心や距離感の近すぎる表現がないか
- 詳しくない話題に詳しいふりをしていないか
- 相手が返しやすい文になっているか

問題なければ、ユーザーが手動で送信します。その後、CLIでは `partner-mark-sent` でローカル記録のみ行います。

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

## 作業No.117 実運用スモーク確認・微修正

確認内容:

- GUIのプロフィール登録、まとめ貼り付け、抽出プレビュー、保存済みreal_profile検索、partner作成、partner表示、会話履歴、pending_suggestions、timeline、目的・トーン選択、3候補生成導線を確認した。
- Streamlit AppTestで主要タブ、貼り付け欄、保存済みプロフィール検索、目的・トーン選択、候補生成ボタンが例外なく表示されることを確認した。

修正内容:

- プロフィール登録画面で、まとめ貼り付け欄を主導線として説明し、下の入力欄は不足分・修正用であることを明示した。
- 抽出プレビューに未抽出項目と保存前確認メモを追加した。
- 候補生成の目的を実運用向けに並べ替え、電話、会う提案、場所指定、LINE交換など距離が近い目的を下の方へ整理した。
- 初回や1往復目で誘い系や大人っぽい雰囲気を選んだ場合の警告を強めた。
- 生成前チェックの警告を画面上のwarningとしても表示するようにした。
- 候補A/B/Cの説明を候補表示名に含めた。

安全確認:

- 自動送信、外部API通信、マッチングアプリ操作機能は追加していない。
- `data/local/` と `outputs/local/` をGit管理対象にしていない。
- 実プロフィールYAMLやpartner実データYAMLはcommit対象にしていない。
