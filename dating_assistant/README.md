# Dating Assistant

## No.144 通常フロー

通常の使い方では、「プロフィール登録」で相手プロフィールを保存すると、自動で会話対象としてlocal登録されます。ユーザーが「プロフィールからpartner作成」を意識する必要はありません。

基本の流れ:

1. 「プロフィール登録」に相手プロフィールを貼り付ける
2. 保存前プレビューを確認する
3. local保存する
4. dating_assistant が重複を確認し、未登録なら会話対象を自動作成する
5. 既に会話対象がある場合は重複作成せず、既存の相手を使う
6. 「相手と会話する」画面で、初回メッセージ候補や返信候補を作る

「保存済みプロフィール管理」は、保存済みプロフィールの確認や手動管理が必要な場合だけ使う補助画面です。通常運用の主導線は「プロフィール登録」から「相手と会話する」へ進みます。

情報が少ないプロフィールでも保存と会話対象化ができます。不足項目はwarningとして表示されますが、完全空欄でない限り、1件のプロフィールデータとして保存できます。実際の送信はユーザー本人がマッチングアプリ上で手動で行います。GUIはlocal記録のみを行い、自動送信、外部API通信、実LLM API呼び出し、マッチングアプリ操作は行いません。

## No.145 一般ユーザー向けの基本操作

購入者・一般ユーザーは、基本的に次の順番で使います。

1. 「プロフィール登録」に相手プロフィールを貼り付ける
2. 内容を確認して保存する
3. 自動で会話対象として登録される
4. 「この相手と会話する」から「相手と会話する」画面へ進む
5. 相手プロフィールと会話履歴を確認する
6. 会話履歴が空でも「次に送る文を作る」で初回候補A/B/Cを作る
7. 候補本文、使いどころ、狙い、注意点を確認する
8. 実際にマッチングアプリ上で手動送信する
9. 送った文だけを「送信済み」としてlocal記録する
10. 使わなかった候補は未使用候補として破棄する
11. 返信あり、反応よかった、微妙だった、などの送信結果メモを残す
12. 相手から返信が来たら、同じ「相手と会話する」画面で会話履歴に追加する

プロフィール情報が少なくても、まず保存して会話対象にできます。会話履歴が空でも初回候補は作れます。候補生成や送信済み記録はすべてlocal記録であり、マッチングアプリへの自動送信ではありません。

## 相手と会話する画面

GUIの最初のタブは、相手ごとの会話を進めるためのメイン画面です。相手を表示名中心で選び、プロフィール、会話履歴、相手別メモ、次に送る文の候補、送信済みlocal記録、送信結果メモを同じ画面で扱えます。
`partner_id`、YAML、内部status、raw JSONなどの開発者向け情報は通常操作では前面に出さず、必要な場合だけ詳細情報の折りたたみで確認します。

この画面でできること:

- 相手を選ぶ
- 相手のプロフィールを見る
- 会話履歴を見る
- 相手から返信が来たら会話履歴へlocal追加する
- 会話の目的と文の雰囲気を選んで、次に送る候補を3つ作る
- 実際に手動送信した文だけを送信済みとしてlocal記録する
- 送信結果メモや相手別メモを残す

候補生成や記録はlocal保存だけです。マッチングアプリへの自動送信、外部API通信、実LLM API呼び出しは行いません。実際の送信はユーザー本人がマッチングアプリ上で手動で行ってください。

## プロフィール保存の補足

### labelは内部保存IDです

`label` はユーザーが入力する項目ではありません。ChatGPTプロジェクト側のプロフィール整理テキストにも `label` は不要です。
GUIでプロフィールを保存するとき、dating_assistant が `profile_YYYYMMDD_HHMMSS` や `profile_<safe_hint>_YYYYMMDD_HHMMSS` 形式の安全な内部保存IDを自動生成します。
貼り付け内容に `label: 2026_20_28`、日本語、空白、記号入りのlabelが混じっていても、保存は止めずに安全な `profile_...` 形式へ補正します。
通常画面では保存IDを意識せず、表示名、自己紹介、趣味、写真メモなどを確認してください。完全空欄だけは保存対象がないためブロックしますが、情報が少ないプロフィールは1件のプロフィールデータとして保存できます。

プロフィール登録では、ChatGPTプロジェクトから貼り付けた内容が少なくても、`display_name` や `profile_text` が空という理由だけでは保存を止めません。保存先の `label` は自動候補を使って補完され、情報が少ない内容は `profile_status: minimal` または `profile_status: incomplete` としてlocal YAMLへ保存されます。少量でも1件のプロフィールデータとして扱い、あとで不足項目を補完できます。

`display_name` が空の場合は「表示名未設定」として扱います。`profile_text` が空の場合は「プロフィール本文未設定。あとで補完できます。」として保存されます。写真メモだけある場合は「プロフィール本文なし。写真メモのみ登録。」として保存されます。保存はlocalのみで、自動送信、外部API通信、実LLM API呼び出し、マッチングアプリ操作は行いません。

保存ボタンは、画面上の貼り付け欄と補助入力欄をまとめた保存用payloadを作ってからlocal YAMLへ保存します。完全空欄だけは保存対象なしとして止めますが、表示名なし、本文なし、写真メモなし、趣味なし、年齢なし、エリアなし、アプリ名なしでは止めません。不足項目はwarningとして表示され、保存後にpartner作成へ進めます。

古い「label は必須です」「表示名とプロフィール本文または写真メモが必要です」のような赤エラーが出る場合は、古いStreamlitプロセスを見ている可能性があります。`start_dating_assistant_gui.bat` から起動し直すと、dating_assistant用の古いStreamlitプロセス停止とGUI import preflightを実行してから起動します。

マッチングアプリのプロフィール分析、初回文、返信文、誘い文をローカルで下書きするツールです。
GUI版では、プロフィール貼り付け、partner作成、会話履歴管理、3候補生成、送信済みlocal記録、送信結果メモまでをブラウザ画面で操作できます。
実LLM API、外部通信、自動送信、外部投稿は行いません。生成結果は必ず人間が確認してから使用してください。

## dating_assistantとは

dating_assistantは、マッチングアプリ上のやり取りをユーザー本人が安全に進めるためのローカル補助ツールです。
相手プロフィールや会話履歴をもとに、送信文候補、会話ステージ、温度感、次の一手、誘い系アクションの可否を確認できます。
インターネット上のWebサービスではなく、PC内で動くローカルGUIです。

## できること

- プロフィール情報をまとめて貼り付け、real_profileとしてlocal保存する
- 保存済みプロフィールからpartnerを作成する
- 会話履歴を貼り付けてpartnerに追加する
- 相手別メモと送信結果メモをlocal保存する
- 目的・トーンを選び、候補A/B/Cの3候補を生成する
- 会話ステージ、温度感、次の一手おすすめ、誘い系アクションの可否を確認する
- 実際に手動送信した文だけ、送信済みlocal記録として残す
- 未使用候補を破棄して整理する

## できないこと

- マッチングアプリへ直接接続しない
- 自動送信しない
- 外部投稿しない
- 実LLM API呼び出しを行わない
- スクリーンショット画像そのものや顔写真そのものを保存しない
- 本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスなどの個人情報を保存しない

## 起動方法

普段は、リポジトリルートにある次のbatをダブルクリックします。

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\start_dating_assistant_gui.bat
```

ブラウザで開くURL:

```text
http://localhost:8501
```

ChromeやEdgeなどのブラウザで操作します。これはPC内で動くローカルGUIであり、インターネット上の公開Webサービスではありません。

## GUI更新後の再起動

GUI更新後に `cannot import name ... from gui_helpers` のようなImportErrorが出る場合は、古いStreamlitプロセスをブラウザで見続けている可能性があります。
`start_dating_assistant_gui.bat` は起動前に、dating_assistant用の古いStreamlitプロセスだけを自動停止し、GUI import preflightを実行します。
preflightで不足importが見つかった場合は、Streamlitを起動せず、足りない関数名を表示します。

手動で確認する場合:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "streamlit|gui_streamlit_app|dating_assistant|start_dating" } | Select-Object ProcessId, Name, CommandLine
```

手動で停止する場合:

```powershell
Stop-Process -Id <PID> -Force
```

## 初回メール入力が出た場合

Streamlitの初回画面でメール入力が出た場合は、何も入力せずEnterでOKです。
これはStreamlit側の任意入力であり、dating_assistant本体には不要です。

## 基本の使い方

1. `start_dating_assistant_gui.bat` をダブルクリック
2. ブラウザで `http://localhost:8501` を開く
3. 「プロフィール登録」タブで相手プロフィールをまとめて貼り付ける
4. 抽出プレビューを確認する
5. 必要に応じて不足分・修正欄を直す
6. real_profileとして保存する
7. 「プロフィールからpartner作成」タブで保存済みプロフィールからpartnerを作成する
8. 「partnerビュー」でpartnerを選択する
9. 必要なら「会話履歴インポート」タブで会話履歴を貼り付ける
10. 相手別メモを入力する
11. 目的・トーンを選ぶ
12. 生成前チェックを確認する
13. 3候補を生成する
14. 候補A/B/Cから送る文を人間が選ぶ
15. マッチングアプリ上でユーザー本人が手動送信する
16. GUIで送信済みlocal記録をする
17. 送信結果メモを残す
18. 相手から返信が来たら会話履歴に追加する
19. 次の候補生成へ進む
20. 使わなかった候補は未使用候補として破棄する

## プロフィール登録の流れ

「プロフィール情報まとめ貼り付け欄」に、プロフィール文、趣味、エリア、年齢、写真の印象メモなどをまとめて貼り付けます。
画像そのものは保存せず、読み取ったテキストと短いメモだけを入力します。
抽出プレビューを確認し、抽出できなかった項目や違う項目だけを「不足分・修正欄」で直してから保存します。
不足分・修正欄は補助用です。まず一括貼り付け欄を使い、初期表示では必須エラーを出さず、保存時に必要項目を確認します。

ChatGPTプロジェクトでプロフィールを整理してから貼り付ける場合は、次の標準フォーマットがおすすめです。

```text
display_name:
サンプル

app_name:
未設定

age:
未設定

area:
未設定

profile_text:
はじめまして。
プロフィールを見ていただき、ありがとうございます。

interests:
* 自然が好き
* 食事が好き

photo_memo:
* 落ち着いた雰囲気

conversation_hooks:
* 自然の話

first_message_hints:
* 返信しやすい質問を1つ入れる

avoid_topics:
* 未設定

notes:
未設定

privacy_notes:
* 個人情報は保存しない
```

`profile_text:` は次の項目キーまでを自己紹介として読み取ります。
`interests:`、`photo_memo:`、`conversation_hooks:`、`first_message_hints:`、`avoid_topics:`、`privacy_notes:` は箇条書きとして読み取ります。
`未設定` は空欄として扱います。
ChatGPTプロジェクト側で `label` を出せる場合は、英数字・ハイフン・アンダースコアの保存用labelを含めてください。
`label` がない場合は、dating_assistant側で `profile_YYYYMMDD_HHMMSS` 形式などの安全なlabel候補を自動作成します。
プロフィール本文、趣味、メモにはコロン、ハイフン、引用符、改行、日本語、絵文字が含まれていてもlocal YAMLとして安全に保存できるようにしています。
貼り付けから抽出された値は保存ボタン時のpayloadにも反映されます。補助入力欄が空のままでも、抽出済みの表示名、プロフィール本文、写真メモ、趣味は保存に使われます。
自動候補はそのまま保存確定せず、不足分・修正欄と抽出プレビューに表示されます。
保存前に確認するのは表示名、自己紹介、趣味、写真メモなどの内容です。labelは通常画面で入力・修正する必要はありません。
貼り付け内容に日本語や数字始まりのlabelが混じっていても、保存時に安全な内部IDへ補正します。

画像から読み取る補助機能もあります。
Windowsキー + Shift + S でプロフィール画面を範囲選択したあと、「クリップボード画像を読み取る」を押します。
クリップボードから読めない場合は、png / jpg / jpeg / webp の画像ファイルを一時的に選択できます。
画像そのもの、顔写真、スクリーンショットは保存しません。
OCR結果の文字だけを画面で確認・修正し、「このテキストをプロフィール欄へ反映」してから保存前プレビューへ進みます。
OCRが未設定の場合でもGUI全体は起動します。その場合は、テキストを手入力またはメモ帳経由で貼り付けてください。
OCRを使う場合は、任意で `pytesseract` とWindows用Tesseract OCR本体のセットアップが必要です。
OCR結果に本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスが含まれる場合は保存前に削除してください。

### OCRセットアップは任意です

OCRは補助機能です。未設定でも、プロフィール情報まとめ貼り付け欄を使う通常運用はそのまま使えます。
画像から文字を読み取りたい場合だけ、Windowsローカル環境に次を用意してください。

1. Windows用Tesseract OCR本体をインストールする
2. `tesseract.exe` にPATHを通す
3. GUI用Python環境に `pytesseract` を追加する
4. 日本語を読む場合はTesseractの日本語言語データ `jpn` を追加する
5. 英語も読む場合は `eng` が使えることを確認する

確認コマンド:

```powershell
tesseract --version
tesseract --list-langs
.\.venv_dating_gui\Scripts\python.exe -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

GUI用Python環境へ入れる例:

```powershell
.\.venv_dating_gui\Scripts\python.exe -m pip install pytesseract
```

`tesseract --list-langs` に `jpn` が出ない場合、日本語OCRは未設定です。
その場合はTesseractの日本語言語データを追加するか、プロフィール文をテキストで貼り付けてください。
`pytesseract` はPythonからTesseract OCR本体を呼び出すためのラッパーです。
`pytesseract` だけを入れても、Tesseract OCR本体が未導入、または `tesseract.exe` にPATHが通っていない場合はOCRできません。
WindowsでPATHが通っているか分からない場合は、PowerShellで `where.exe tesseract` を確認してください。
標準的なインストール先は `C:\Program Files\Tesseract-OCR\tesseract.exe` です。
このファイルが存在する場合は、`C:\Program Files\Tesseract-OCR` をPATHに追加してからGUIを起動し直してください。
Tesseract本体、言語データ、インストーラー、画像ファイルはリポジトリに入れません。

## 保存済みプロフィールからpartner作成

「プロフィールからpartner作成」タブで保存済みプロフィールを検索し、内容を確認してpartnerを作成します。
既存partner候補が表示された場合は、重複作成しないように確認してください。

選択中プロフィールは、通常画面ではJSONではなくカード形式で表示されます。
表示名、年齢、エリア、自己紹介、趣味、写真メモ、会話に使えそうな話題、避けた方がよい話題、安全メモを確認してから作成してください。
内部pathなどの詳細情報は通常表示には出さず、「詳細データを表示」の折りたたみ内で確認できます。

partner作成前には「作成されるpartner」のカードで、表示名、元プロフィール、状態、初期ステージ、作成時に含まれる内容、注意事項を確認します。
partner表示名、アプリ名、作成時メモを入力すると、保存プレビューに反映されます。
詳細JSONは開発者確認用として折りたたみにあります。
既存partner候補が出た場合は、既存partnerを開くか、新しく作成するかを確認してから進めてください。

## 会話履歴インポート

「会話履歴インポート」タブで、相手と自分の発話を貼り付けます。
`相手:`、`自分:`、`partner:`、`user:` などのラベルを使うと取り込みやすくなります。
保存前プレビューを確認し、発話者や順番が正しい場合だけlocal保存します。
画面内の貼り付け例を参考に、スクリーンショット画像ではなく読み取ったテキストを貼り付けます。
解析できない場合は、理由候補と対処を確認し、「自分:」「相手:」の形式に直すか、1発言ずつ手動追加します。

## 返信候補生成

partnerビューで目的・トーンを選び、生成前チェックを確認してから3候補を生成します。
候補生成はlocalの `pending_suggestions` に保存するだけで、自動送信ではありません。

## 候補A/B/Cの見方

- 候補A: 一番無難。迷ったらこれ
- 候補B: 少し親しみやすい。会話を広げたいとき
- 候補C: 少し距離を縮める。ただし警告がある場合は慎重に使う

候補はそのまま送る前に必ず人間が確認してください。
会話ステージ、温度感、注意点、品質チェックを見て、誘い系やLINE交換が早すぎないか確認します。

## 会話ステージ・温度感・次の一手おすすめの見方

生成前チェックでは、会話履歴、相手別メモ、最近の送信結果メモをもとに判断材料を表示します。
初回や1往復目では、電話、会う提案、LINE交換、大人っぽい雰囲気は慎重に扱います。
温度感が低い場合は、短く返しやすい雑談を優先してください。

## 電話提案・会う提案・LINE交換の注意

電話提案:

- 2〜3往復後、相手の反応が良い場合に検討
- 短時間、軽く、断りやすく
- 電話番号は聞かない
- 強引に誘わない

会う提案:

- カフェ、お茶、ランチなど軽め
- 夜遅い誘い、自宅、ホテル、密室系は避ける
- 場所指定は押しつけない
- 断りやすい文にする

LINE交換:

- 初回や1往復目では基本避ける
- LINE IDそのものは保存しない
- アプリのままでも大丈夫という余白を残す
- 個人情報に近いため慎重に扱う

## 大人っぽい話題の扱い

- 下ネタではなく、軽い恋愛感・大人っぽい雰囲気までにする
- 露骨な性的表現は禁止
- 身体の部位を褒めない
- 写真を性的に見ない
- ホテル、自宅、密室系の誘いは禁止
- 初回や温度感が低い場合は使わない
- 使う場合も、雰囲気、距離感、話しやすさ程度に留める

## 相手別メモの使い方

返信時間帯、反応がよい話題、まだ早そうな誘い方などを短くlocal保存します。
本名、勤務先、学校名、SNS ID、LINE ID、住所、電話番号、メールアドレスは書かないでください。

## 送信結果メモの使い方

実際に手動送信した文に対して、返信あり、反応よかった、話題が広がった、微妙だった、未確認などを記録します。
送信結果メモは `sent_id` に紐づくため、どの文章への反応だったか後から確認できます。

## 実際に送った後のlocal記録

マッチングアプリ上でユーザー本人が手動送信した後だけ、GUIで送信済みlocal記録を行います。
AI候補をそのまま送った場合も、修正した手入力文を送った場合も、local記録のみです。

## 未使用候補の破棄

送らなかった候補は、未使用候補として破棄できます。
候補破棄はlocalの整理だけで、マッチングアプリ側の内容を変更しません。

## データ保存場所

- 実プロフィール: `dating_assistant/data/local/real_profiles/`
- partner実データ: `dating_assistant/data/local/partners/`
- local出力: `dating_assistant/outputs/local/`

## Gitに入れてはいけないもの

- `dating_assistant/data/local/`
- `dating_assistant/outputs/local/`
- 実プロフィールYAML
- partner実データYAML
- `.env`
- token、secret、credential
- 個人情報や実データ

## 安全ルール

- 自動送信しない
- マッチングアプリへ直接接続しない
- 実際の送信はユーザー本人が手動で行う
- GUIの送信済み記録はlocal記録のみ
- スクリーンショット画像そのものを保存しない
- 顔写真そのものを保存しない
- 本名、勤務先、学校名、LINE ID、SNS ID、住所、電話番号、メールアドレスは保存しない
- `data/local/` をGitに入れない
- `outputs/local/` をGitに入れない
- 実プロフィールYAMLをcommitしない
- partner実データYAMLをcommitしない

## トラブルシュート

- GUIが開かない: `start_dating_assistant_gui.bat` をもう一度起動し、PowerShellにエラーが出ていないか確認します。
- `http://localhost:8501` が開かない: 既に別のStreamlitが動いていないか確認し、PowerShellに表示されたURLを開きます。
- Streamlitのメール入力が出る: 何も入力せずEnterでOKです。
- 既存partnerが見つからない: archivedを含める設定や保存済みプロフィール検索を確認します。
- プロフィール抽出がうまくいかない: 不足分・修正欄で必要な項目だけ直してから保存します。
- 候補が生成されない: 既存のpending_suggestionsが残っている場合は、確認、送信済み記録、または破棄を先に行います。
- 送信済み記録が見つからない: 実際に手動送信した文だけがlocal記録対象です。
- 送信結果メモが反映されない: 送信済みlocal記録に紐づく `sent_id` を選んで結果メモを保存してください。
- `data/local/` の実データをcommitしそうになった場合: commitせず停止し、Git状態を確認してください。
- テストが失敗した場合: 失敗したテスト名とエラーを確認し、実データではなく一時ディレクトリを使っているか確認します。

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
partnerビューでは、基本情報と会話状態をカード形式で確認できます。message_stateなどの詳細JSONは折りたたみ内にあり、通常画面では日本語ラベル中心で表示します。
プロフィール登録では、テキスト一括貼り付けに加えて、任意のローカルOCR補助でスクリーンショット内の文字を読み取れます。OCR未設定でも通常のテキスト貼り付け運用は使えます。

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
9. 候補A/B/Cのタイトル、使いどころ、狙い、品質チェック、注意点を確認し、必要なら短く自然な文へ整えます。
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

候補A/B/Cの見方:

- 候補A: 一番無難。迷ったらこれを優先します。
- 候補B: 少し親しみやすい。自分の話を少しだけ混ぜて会話を広げます。
- 候補C: 少し距離を縮める。ただし会話ステージが浅い場合は、強い誘いではなく次につながる一言に抑えます。
- 各候補には、使いどころ、狙い、会話ステージとの相性、品質チェック、注意点が表示されます。

初回メッセージの方針:

- いきなり電話、会う提案、LINE交換は入れません。
- 相手プロフィールの話題を1つだけ自然に拾い、質問は1つまでにします。
- 「プロフィール見ました」「共通点があります」などのテンプレ感が強い表現は避けます。
- 褒めすぎず、相手が軽く返しやすい文にします。

電話・会う提案の目安:

- 1往復目はプロフィールに自然に触れる軽い質問を優先します。
- 2往復目は共感と相手の好みを深掘りしすぎない質問にします。
- 2から3往復して温度感が良い場合だけ、短時間で断りやすい電話提案を検討します。
- 電話後、または十分に自然な会話が続いた後に、カフェやご飯など軽い会う提案を検討します。
- 相手の反応が薄い場合や距離感が近すぎる場合は、電話や会う提案へ進めません。

誘い系・距離感の方針:

- 電話提案は、短時間、断りやすい言い方、自然な理由を添えることを優先します。
- 会う提案は、カフェ、お茶、ランチなど軽めにし、夜遅い誘い、自宅、ホテル、密室系は避けます。
- LINE交換は、会話が続いて温度感が良い場合だけ、アプリのままでもよい余白を残します。LINE IDそのものは保存しません。
- 大人っぽい雰囲気は下ネタではなく、軽い恋愛感や落ち着いた印象に留めます。露骨な性的表現、身体の部位、ホテル、自宅、密室系は使いません。
- 送る前に、長さ、質問数、褒めすぎ、テンプレ感、個人情報、LINE交換の唐突さ、大人っぽさの強さを必ず確認してください。

実運用リハーサルでの確認ポイント:

- 初回はプロフィール貼り付け後、初回候補A/B/Cを確認し、電話、会う提案、LINE交換が混ざっていないことを見ます。
- 1往復目は相手の返信へのリアクションがあるか、質問が1つまでか、誘い系に警告が出ているかを確認します。
- 2から3往復目は、温度感と次の一手おすすめを見て、雑談継続か控えめな電話提案かを判断します。
- 電話、会う提案、LINE交換、大人っぽい雰囲気は、生成前チェックの可否判定と候補ごとの品質チェックを見て、送るかどうかをユーザーが判断します。
- 相手別メモや送信結果メモに「電話はまだ早そう」「質問多めの文は微妙だった」などを残すと、生成前チェックの注意点に反映されます。

## テスト方法

```powershell
python -m unittest discover tests
```
