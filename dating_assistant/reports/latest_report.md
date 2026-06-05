# dating_assistant latest_report

更新日: 2026-06-06
作業No.: 41

## 今回の目的

作業No.40で確認した、実プロフィール投入前の安全運用リハーサル結果を運用メモとして整理しました。

今回の主目的は、コードの大きな変更ではなく、今後ユーザーが迷わず実運用に進めるように以下を明文化することです。

- 実プロフィールは `data/local/real_profiles/` に保存する
- partner実データは `data/local/partners/` に保存する
- スクリーンショット画像そのものは保存しない
- 個人情報や実データをGit管理対象に含めない
- CLIは現時点では `python -m dating_assistant` ではなく、`dating_assistant` 配下で `python main.py ...` を使う
- unittestはリポジトリルートではなく、`dating_assistant` 配下で実行する

## 作業No.40 実プロフィール運用前リハーサルメモ

作業No.40で、実プロフィール投入前の安全リハーサルを実施しました。

確認済みの流れ:

1. ダミーreal profile作成
2. `real-profile-list` / `real-profile-show` / `real-profile-rehearse` 確認
3. `partner-create` でpartner作成
4. `partner-generate-first` で初回メッセージ候補生成
5. `pending_suggestions` 保存確認
6. `partner-dashboard` / `partner-timeline` 確認
7. unittest 108件成功

作成したダミーデータ:

- `data/local/real_profiles/sample_profile_001.yaml`
- `data/local/partners/partner_009.yaml`
- `pending_suggestions: suggestion_001`

上記はすべてGit管理対象外のlocal配下に作成され、Git候補には出ませんでした。

## 安全確認

- 実LLM API呼び出しなし
- 外部通信なし
- 自動送信なし
- 外部投稿なし
- スクリーンショット画像そのものの保存なし
- `data/local/` 配下のみ使用
- `outputs/local/` 配下はGit管理対象外
- Git管理ファイルへの実データ混入なし
- 本名、勤務先、学校名、住所、電話番号、メールアドレス、LINE ID、SNS IDの保存なし

## コマンド実行時の注意

現時点では、リポジトリルートからの `python -m dating_assistant` は `__main__.py` がないため使用できません。

CLI確認や運用コマンドは、`dating_assistant` ディレクトリ内で既存の `main.py` を使います。

例:

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\dating_assistant"
python main.py real-profile-list
python main.py real-profile-show --label sample_profile_001
python main.py real-profile-rehearse --label sample_profile_001 --display-name sample_profile_001 --app-name rehearsal --dry-run
python main.py partner-create --source data/local/real_profiles/sample_profile_001.yaml --display-name sample_profile_001 --app-name rehearsal
python main.py partner-generate-first --partner-id partner_009
python main.py partner-dashboard
python main.py partner-timeline --partner-id partner_009
```

unittestもリポジトリルートからではなく、`dating_assistant` 配下で実行します。

```powershell
cd "C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\dating_assistant"
python -m unittest discover -s tests -v
```

## real-profile-rehearse の注意

`real-profile-rehearse` は `--label` または `--path` に加えて、`--display-name` が必須です。

年齢はCLI仕様上 `int` 指定のため、「30代前半」のような表現はそのまま入力できません。必要に応じて `31` などの数値に置き換えて登録します。

## 実プロフィール入力方針

実際の相手プロフィールを登録する場合も、スクリーンショット画像そのものは保存しません。

保存するもの:

- プロフィール文の要約
- 趣味、関心
- 写真の雰囲気メモ
- 会話で触れてよさそうな話題
- 避けた方がよい話題
- 補足メモ

保存しないもの:

- 本名
- 勤務先
- 学校名
- 住所
- 電話番号
- メールアドレス
- LINE ID
- SNS ID
- 顔写真やスクリーンショット画像そのもの

危険語警告が出た場合は、保存前に内容を見直します。警告は補助機能であり、完全な検出ではないため、人間の最終確認を必ず行います。

## 確認した出力傾向

ダミープロフィールでは、初回メッセージ候補が以下の方針に沿って生成されました。

- 旅行を深掘りしすぎない
- カフェ、休日、ご飯の話題へ自然に移動する
- 初回から誘わない
- 質問を1つに絞る
- ユーザー本人が詳しいふりをしない
- `安全チェック結果` と `一番おすすめ` を含む

`partner-generate-first` 後は、`partner_009` が `first_message_suggested` になり、`suggestion_001` が未送信候補として保存されました。

## テスト結果

作業No.40での確認:

```text
Ran 108 tests in 0.494s

OK
```

作業No.41でも、追記後に再度unittestを実行して確認します。

## Git状態メモ

作業No.40で作成したlocal配下のダミーデータは、`.gitignore` によりGit管理対象外です。

確認済み:

- `dating_assistant/data/local/real_profiles/*`
- `dating_assistant/data/local/partners/*`
- `dating_assistant/outputs/local/*`

今回commit対象に含めるのは、運用メモとして更新したGit管理ドキュメントのみです。

## 次に改善すべき点

- 実プロフィール1件をユーザーが貼り、同じ手順で実運用入力に進むか判断する
- 必要ならREADMEにも、No.40で見つかった実行場所の注意を短く追記する
- `python -m dating_assistant` を正式に使いたい場合は `__main__.py` 追加を検討する
- リポジトリルートからのunittest実行を可能にするか、READMEのテスト実行場所をさらに明確にする
- 実データを含まないサンプルとテストを維持する
- local配下の実プロフィール、実会話、実入力をGit管理対象に含めない
- dashboard / timeline / archive の運用性を実データで確認する

## UTF-8整合性テスト用キーワード

既存テストとの整合性維持:

- 螳牙・遒ｺ隱・
- 谺｡縺ｫ謾ｹ蝟・☆縺ｹ縺咲せ
