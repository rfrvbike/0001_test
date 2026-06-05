# 作業No.19 git add dry-run確認レポート

更新日: 2026-06-05

## 目的

`dating_assistant` をGit管理対象にする前に、実データや個人情報がステージ対象に混ざらないことを確認する。

今回はdry-runのみ実施し、実際の `git add`、`git commit`、`git push` は行っていない。

## Git状態

実行コマンド:

```powershell
git status --short
```

概要:

- `dating_assistant/` 配下の未追跡ファイル・ディレクトリが表示されている。
- `dating_assistant/` 以外にも、既存の株分析/X運用系と思われる未追跡ファイルやレポートが多数表示されている。
- 今回は `dating_assistant` のdry-run確認のみを対象とし、dating_assistant以外には変更を加えていない。

## Git管理対象候補

実行コマンド:

```powershell
git ls-files -o --exclude-standard dating_assistant
```

候補概要:

- `dating_assistant/README.md`
- `dating_assistant/app.py`
- `dating_assistant/main.py`
- `dating_assistant/config/*.yaml`
- `dating_assistant/data/examples/*.yaml`
- `dating_assistant/data/local/conversations.example.json`
- `dating_assistant/data/local/partners/.gitkeep`
- `dating_assistant/outputs/examples/*.md`
- `dating_assistant/outputs/local/.gitkeep`
- `dating_assistant/prompts/*.md`
- `dating_assistant/reports/*.md`
- `dating_assistant/src/*.py`
- `dating_assistant/tests/*.py`
- `dating_assistant/tools/*.py`

補足:

- `dating_assistant/data/local/real_profiles/.gitkeep` は既にGit管理済みのため、未追跡候補には表示されなかった。
- `data/local/real_profiles/*.yaml` は候補に表示されなかった。
- `data/local/partners/*.yaml` は候補に表示されなかった。
- `outputs/local/*.md` は候補に表示されなかった。
- `__pycache__` と `*.pyc` は候補に表示されなかった。

## Git管理対象外であることを確認したもの

以下はGit管理対象外であることを確認した。

- `dating_assistant/data/local/real_profiles/*.yaml`
- `dating_assistant/data/local/partners/*.yaml`
- `dating_assistant/outputs/local/*.md`
- `dating_assistant/**/__pycache__/*`
- `dating_assistant/**/*.pyc`

実行コマンド:

```powershell
git check-ignore -v dating_assistant/data/local/real_profiles/rehearse_cafe_movie.yaml dating_assistant/data/local/partners/partner_006.yaml dating_assistant/data/local/partners/partner_007.yaml dating_assistant/outputs/local/real_profile_rehearse_rehearse_cafe_movie_20260605_233805.md
```

結果:

```text
.gitignore:30:dating_assistant/data/local/real_profiles/* dating_assistant/data/local/real_profiles/rehearse_cafe_movie.yaml
.gitignore:27:dating_assistant/data/local/partners/* dating_assistant/data/local/partners/partner_006.yaml
.gitignore:27:dating_assistant/data/local/partners/* dating_assistant/data/local/partners/partner_007.yaml
.gitignore:32:dating_assistant/outputs/local/* dating_assistant/outputs/local/real_profile_rehearse_rehearse_cafe_movie_20260605_233805.md
```

## git add dry-run結果

実行コマンド:

```powershell
git add -n dating_assistant
```

ステージ予定の概要:

- README、app、main
- config配下のYAML
- data/examples配下のサンプルYAML
- data/localのサンプルJSONと`.gitkeep`
- outputs/examples配下のサンプル出力
- outputs/localの`.gitkeep`
- prompts配下のプロンプトMarkdown
- reports配下のレポートMarkdown
- src配下のPython実装
- tests配下のPythonテスト
- tools配下の補助スクリプト

dry-runでステージ予定に含まれなかったもの:

- 実プロフィールYAML
- 実partner YAML
- `outputs/local` の実出力Markdown
- `__pycache__`
- `*.pyc`
- `dating_assistant` 以外のファイル

判断:

- dry-run結果に実データ混入なし。
- dry-run結果に個人情報を含む実ローカルデータなし。
- dry-run結果にPythonキャッシュなし。

## 個人情報・実データ混入チェック

チェック対象:

- `dating_assistant/README.md`
- `dating_assistant/reports/*.md`
- `dating_assistant/data/examples/*.yaml`
- `dating_assistant/outputs/examples/*.md`
- `dating_assistant/tests/*.py`
- `dating_assistant/config/*.yaml`

検索語:

```text
LINE / ライン / Instagram / インスタ / 本名 / 勤務先 / 会社名 / 学校名 / 大学名 / 高校 / 最寄り駅 / 住所 / 電話番号 / メールアドレス / スクリーンショット / 顔写真
```

検出結果:

- READMEの禁止注意として検出された。
- safety設定の警告語として検出された。
- テスト用の警告語・異常系入力として検出された。
- テンプレートの禁止例として検出された。
- レポート内の検索語一覧・安全確認文として検出された。

判断:

- 実在の連絡先、住所、SNS ID、個人名、実プロフィール本文の混入は確認されなかった。
- 検出内容は注意文、ポリシー、テスト、テンプレート、監査説明として妥当。

## テスト結果

実行場所:

```text
C:\Users\oyue_\OneDrive\ドキュメント\GitHub\0001_test\dating_assistant
```

実行コマンド:

```powershell
C:\Users\oyue_\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover tests
```

結果:

```text
Ran 94 tests in 0.382s

OK
```

補足:

- `argparse` の異常系テストにより、無効な `--speaker` に対するusage表示が出るが、テストは成功している。

## 結論

git addしてよい候補:

- `dating_assistant/README.md`
- `dating_assistant/app.py`
- `dating_assistant/main.py`
- `dating_assistant/config/`
- `dating_assistant/data/examples/`
- `dating_assistant/data/local/conversations.example.json`
- `dating_assistant/data/local/partners/.gitkeep`
- `dating_assistant/outputs/examples/`
- `dating_assistant/outputs/local/.gitkeep`
- `dating_assistant/prompts/`
- `dating_assistant/reports/`
- `dating_assistant/src/`
- `dating_assistant/tests/`
- `dating_assistant/tools/`

git addしてはいけないもの:

- `dating_assistant/data/local/real_profiles/*.yaml`
- `dating_assistant/data/local/partners/*.yaml`
- `dating_assistant/outputs/local/*.md`
- `dating_assistant/**/__pycache__/*`
- `dating_assistant/**/*.pyc`

次の推奨作業:

- ユーザー確認後にのみ、実際の `git add` を行う。
- `git add` 前に、もう一度 `git add -n dating_assistant` を確認する。
- 実際にステージした後は `git status --short` でステージ内容を確認する。
