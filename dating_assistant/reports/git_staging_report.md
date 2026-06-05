# 作業No.20 git staging確認レポート

更新日: 2026-06-06

## 目的

`dating_assistant` の安全なGit管理対象を実際にステージし、commit前に実データや個人情報が混入していないことを確認する。

今回は `git add` とcommit前確認のみを実施し、`git commit` と `git push` は行っていない。

## 作業前Git状態

実行コマンド:

```powershell
git status --short
```

概要:

- `dating_assistant/` 配下の未追跡ファイル・ディレクトリが表示されていた。
- `dating_assistant/` 以外にも、既存の株分析/X運用系と思われる未追跡ファイルやレポートが多数表示されていた。
- 今回は `dating_assistant` のみを対象とし、dating_assistant以外には `git add` していない。
- 既存の株分析/X運用系コードには変更を加えていない。

## 実行したgit add

実行したコマンド:

```powershell
git add dating_assistant/README.md
git add dating_assistant/app.py
git add dating_assistant/main.py
git add dating_assistant/config
git add dating_assistant/data/examples
git add dating_assistant/data/local/conversations.example.json
git add dating_assistant/data/local/partners/.gitkeep
git add dating_assistant/outputs/examples
git add dating_assistant/outputs/local/.gitkeep
git add dating_assistant/prompts
git add dating_assistant/reports
git add dating_assistant/src
git add dating_assistant/tests
git add dating_assistant/tools
```

補足:

- `dating_assistant/data/local/real_profiles/.gitkeep` は既にGit管理済みのため、今回の新規stage対象には表示されていない。
- Windows環境の改行設定により、複数ファイルで `LF will be replaced by CRLF` の警告が出たが、ステージ対象の安全性には影響しない。

## staged files確認

実行コマンド:

```powershell
git diff --cached --name-only
```

stagedに含まれたファイル群:

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

stagedに含まれていないことを確認した実データ:

- `dating_assistant/data/local/real_profiles/*.yaml`
- `dating_assistant/data/local/partners/*.yaml`
- `dating_assistant/outputs/local/*.md`
- `dating_assistant/**/__pycache__/*`
- `dating_assistant/**/*.pyc`
- `dating_assistant` 以外のファイル

禁止パターン確認:

```powershell
git diff --cached --name-only | Select-String -Pattern "data/local/real_profiles/.*\.yaml|data/local/partners/.*\.yaml|outputs/local/.*\.md|__pycache__|\.pyc$|^(?!dating_assistant/)"
```

結果:

- 該当なし。

## staged diff確認

実行コマンド:

```powershell
git diff --cached --stat
```

概要:

- `dating_assistant` の実装、設定、サンプル、テスト、出力例、プロンプト、レポートが追加対象。
- 本レポートと更新後の `latest_report.md` をstageした後、最終statは95ファイル、6061行追加だった。

確認結果:

- 実プロフィールYAMLの混入なし。
- 実partner YAMLの混入なし。
- `outputs/local/*.md` の混入なし。
- `__pycache__` / `*.pyc` の混入なし。
- `dating_assistant` 以外の混入なし。

local配下のstaged diff:

```powershell
git diff --cached -- dating_assistant/data/local dating_assistant/outputs/local
```

確認結果:

- `dating_assistant/data/local/conversations.example.json`
- `dating_assistant/data/local/partners/.gitkeep`
- `dating_assistant/outputs/local/.gitkeep`

上記のみが対象で、実データは含まれていない。

## 個人情報・実データ混入チェック

チェック対象:

- staged対象の `dating_assistant` ファイル

実行コマンド:

```powershell
git grep --cached -n -e LINE -e ライン -e Instagram -e インスタ -e 本名 -e 勤務先 -e 会社名 -e 学校名 -e 大学名 -e 高校 -e 最寄り駅 -e 住所 -e 電話番号 -e メールアドレス -e スクリーンショット -e 顔写真 -- dating_assistant
```

検出結果:

- READMEの禁止注意として検出。
- safety設定の警告語として検出。
- 実装内の危険語検出リストとして検出。
- テスト用の警告語・異常系入力として検出。
- テンプレートの禁止例として検出。
- レポート内の検索語一覧・安全確認文として検出。

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
Ran 94 tests in 0.349s

OK
```

補足:

- `argparse` の異常系テストにより、無効な `--speaker` に対するusage表示が出るが、テストは成功している。

## 安全確認

- 実LLM API呼び出しなし
- 外部通信なし
- 自動送信なし
- 外部投稿なし
- 顔写真・スクリーンショット画像保存なし
- 実プロフィールYAMLはGit除外
- 実partner YAMLはGit除外
- `outputs/local` の実出力はGit除外
- `dating_assistant` 以外はstageしていない
- `git commit` 未実行
- `git push` 未実行

## 次の推奨作業

ユーザー確認後にcommitする。

commitメッセージ案:

```text
feat: add dating assistant CLI workflow
```

本文案:

```text
- Add real profile creation and rehearsal flow
- Add partner management, suggestions, dashboard, and timeline
- Add safety checks and local-data git exclusions
- Add tests and reports
```
