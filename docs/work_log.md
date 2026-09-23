# 作業ログ

このプロジェクトの作業を時系列で記録する。詳しい経緯・判断理由は
`HANDOFF.md`（引き継ぎ資料）、各設計書（`設計書.md`, `webui設計書.md`）、
`docs/SPECIFICATION.md`, `docs/MODEMAP_RESTORATION.md` を参照。

## 2026-09-22

- **Google Drive連携でのファイル取得**（Claude）: スプレッドシート2冊
  （concept, 原稿）と、それぞれに紐づくGASプロジェクト2つを`clasp`で
  ローカルにクローン。`spreadsheets/`, `gas-projects/`（ともに.gitignore
  対象、再取得可能な元データのため）。
- **GASコード解析・仕様復元**（Kimi Code）: project1/project2の依存関係を
  解析、`docs/SPECIFICATION.md`（仕様書）を作成。ツールの正体は同人漫画の
  工程管理ツールと判明。project2（modemapマスタ＋残作業時間集計）を
  復元ターゲットに確定。
- **modemap DB復元**（Kimi Code）: data.js内のSQL全文からスキーマ・行を
  復元。`restoration/modemap.sql`, `restoration/modemap.csv`,
  `docs/MODEMAP_RESTORATION.md`。
- **taskman CLI設計・実装**（Kimi Codeが設計 → Claudeがレビュー・実装）:
  `設計書.md`をdata.js実物と突き合わせレビューし、2点の乖離を発見。
  - mode適用単位を「plotの先頭行のみ」から「行ごとに自分のmode」へ
    利用者確認の上で意図的に変更（実データで7 plot中4つに影響）。
  - plotの非連続再出現に対応するグルーピング方式を修正。
  `taskman/`パッケージ（master.py, sheet.py, analyze.py, cli.py）実装。
  `python -m taskman analyze <xlsx>` で残作業時間集計が可能に。
- **git初期化・初回コミット**（Claude）: `spreadsheets/`, `gas-projects/`を
  除外して初回コミット。リモート `git@github.com:kuromook/taskman.git`
  にpush。

## 2026-09-23

- **WebUIダッシュボード設計**（Claude）: 静的HTML生成方式（サーバー不要、
  新規依存なし）で`webui設計書.md`を作成。円グラフ・サイズ可変ドーナツを
  採用（利用者の希望）。dataviz skillでカラーパレットを検証
  （円グラフの輪の継ぎ目を含む隣接ペア）。半径スケールはsqrt
  （対数ではなく面積知覚ベース）、スライス角度に最小クリップ
  （10°未満は底上げ）を設計。
- **WebUIダッシュボード実装**（Claude）: `taskman/view_data.py`,
  `taskman/dashboard.py`, `taskman/templates/dashboard.html.tmpl`を実装。
  `analyze.py`に`total_time()`追加。`cli.py`に`dashboard`サブコマンド
  追加。`python -m taskman dashboard <xlsx> -o dashboard.html`で
  単一HTMLファイルを生成できるように。
- claude-in-chromeでブラウザ実機確認（3タブとも正常表示、リングサイズ・
  円グラフのクリップ・色を目視確認）。利用者も実機確認し「期待通り」と確認。
- 2件目のコミット・push。
