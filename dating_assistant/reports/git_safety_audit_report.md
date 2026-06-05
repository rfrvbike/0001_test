# dating_assistant Git安全監査レポート

更新日: 2026-06-05
作業No.: 18

## 目的

コミット前に、Git管理対象と除外対象を確認し、実データや個人情報が混入していないことを確認する。

## 確認したGit状態

実行コマンド:

```powershell
git status --short
```

概要:

- `dating_assistant/` は未追跡ディレクトリとして表示されている。
- `.gitignore` は `git status --short` 上では個別変更として表示されていない。
- `dating_assistant/` 以外にも、株分析/X運用系と思われる未追跡ファイルやレポートが多数表示されている。
- 今回の監査では、既存の株分析/X運用系コードには変更を加えていない。
- `git add`、`git commit`、`git push` は実行していない。

`dating_assistant` のGit管理候補確認:

```powershell
git ls-files -o --exclude-standard dating_assistant
```

確認結果:

- 実装ファイル、設定ファイル、サンプル、テスト、README、reports、`.gitkeep` が候補として表示された。
- `data/local/real_profiles/*.yaml` は候補に表示されなかった。
- `data/local/partners/*.yaml` は候補に表示されなかった。
- `outputs/local/*.md` は候補に表示されなかった。
- `__pycache__` と `*.pyc` は候補に表示されなかった。

## Git除外確認

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

確認結果:

- `dating_assistant/data/local/real_profiles/` の実プロフィールYAMLはGit除外されている。
- `dating_assistant/data/local/partners/` の実partner YAMLはGit除外されている。
- `dating_assistant/outputs/local/` の実出力MarkdownはGit除外されている。
- `.gitkeep` は追跡可能な候補として残っている。

## Git管理対象にしてよいファイル

今回の確認では、以下はGit管理対象候補として問題ない。

- `dating_assistant/main.py`
- `dating_assistant/app.py`
- `dating_assistant/README.md`
- `dating_assistant/src/*.py`
- `dating_assistant/config/*.yaml`
- `dating_assistant/prompts/*.md`
- `dating_assistant/tests/*.py`
- `dating_assistant/tools/*.py`
- `dating_assistant/data/examples/*.yaml`
- `dating_assistant/outputs/examples/*.md`
- `dating_assistant/data/local/conversations.example.json`
- `dating_assistant/data/local/real_profiles/.gitkeep`
- `dating_assistant/data/local/partners/.gitkeep`
- `dating_assistant/outputs/local/.gitkeep`
- `dating_assistant/reports/*.md`

## Git管理対象にしないファイル

以下はGit管理対象にしない。

- `dating_assistant/data/local/real_profiles/*.yaml`
- `dating_assistant/data/local/partners/*.yaml`
- `dating_assistant/outputs/local/*.md`
- `dating_assistant/**/__pycache__/`
- `dating_assistant/**/*.pyc`

確認済みの除外対象例:

- `dating_assistant/data/local/real_profiles/rehearse_cafe_movie.yaml`
- `dating_assistant/data/local/partners/partner_006.yaml`
- `dating_assistant/data/local/partners/partner_007.yaml`
- `dating_assistant/outputs/local/real_profile_rehearse_rehearse_cafe_movie_20260605_233805.md`

## 個人情報・実データ混入チェック

確認対象:

- `dating_assistant/README.md`
- `dating_assistant/reports/*.md`
- `dating_assistant/data/examples/*.yaml`
- `dating_assistant/outputs/examples/*.md`
- `dating_assistant/tests/*.py`
- `dating_assistant/config/*.yaml`

検索語:

```text
LINE
ライン
Instagram
インスタ
本名
勤務先
会社名
学校名
大学名
高校
最寄り駅
住所
電話番号
メールアドレス
スクリーンショット
顔写真
```

検出結果:

- READMEでは、入力禁止事項や安全注意として危険語が含まれていた。
- `config/safety_policy.yaml` では、保存禁止語・警告語として危険語が含まれていた。
- testsでは、プライバシー警告や危険語検出のテストデータとして含まれていた。
- `data/examples/real_profile_template.yaml` では、テンプレート上の禁止例として含まれていた。
- reportsでは、安全確認の説明として「顔写真」「スクリーンショット」が含まれていた。

判断:

- 実在の個人名、連絡先、住所、勤務先、学校名、SNS IDなどの実データ混入は確認されなかった。
- 検出された語は、注意文、禁止例、安全テスト、ポリシー設定として妥当。
- サンプルデータの「カフェ映画の人」などは実個人情報ではない。

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
Ran 94 tests in 0.346s

OK
```

補足:

- `argparse` の異常系テストにより、無効な `--speaker` に対するusage表示が出るが、テストは成功している。

## 安全確認

- 実LLM API呼び出しなし
- 外部通信なし
- 自動送信なし
- 外部投稿なし
- 顔写真やスクリーンショット画像そのものの保存なし
- 個人情報を含む実データのGit管理なし
- 実プロフィールYAMLはGit除外
- 実partner YAMLはGit除外
- `outputs/local` の実出力はGit除外
- 既存の株分析/X運用系コードへの変更なし
- `git add`、`git commit`、`git push` は未実行

## 次の推奨作業

次にgit addするなら候補:

- `dating_assistant/README.md`
- `dating_assistant/app.py`
- `dating_assistant/main.py`
- `dating_assistant/config/`
- `dating_assistant/data/examples/`
- `dating_assistant/data/local/conversations.example.json`
- `dating_assistant/data/local/partners/.gitkeep`
- `dating_assistant/data/local/real_profiles/.gitkeep`
- `dating_assistant/outputs/examples/`
- `dating_assistant/outputs/local/.gitkeep`
- `dating_assistant/prompts/`
- `dating_assistant/reports/`
- `dating_assistant/src/`
- `dating_assistant/tests/`
- `dating_assistant/tools/`

コミット前の注意:

- `git add dating_assistant/` を使う場合でも、先に `git status --short --ignored` や `git ls-files -o --exclude-standard dating_assistant` で候補を再確認する。
- `data/local/real_profiles/*.yaml`、`data/local/partners/*.yaml`、`outputs/local/*.md` が候補に出ていないことを再確認する。
- ユーザー確認後にのみ `git add` と `git commit` を行う。
