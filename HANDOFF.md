# 引き継ぎ資料 — スプレッドシート＋GASタスク管理ツールのローカルDL

作成日: 2026-09-22
作成者: Claude Code (このセッションでの作業ログ)

## 目的

Google スプレッドシート + それに紐づく Google Apps Script (GAS) で構成された
タスク/スケジュール管理ツールを、編集・移行・解析のためにローカル環境へ
ダウンロードする。

## 対象ファイル（Google Drive上のオリジナル）

| 名前 | Drive File ID | URL | GAS スクリプトID |
|---|---|---|---|
| concept | `1rrebBJwNjFnAtWU7WS6JGubJAVUVjp2OuxE7CperkQc` | https://docs.google.com/spreadsheets/d/1rrebBJwNjFnAtWU7WS6JGubJAVUVjp2OuxE7CperkQc/edit | `1q-vHyJe6HhCUO058F2MalV4NQcIcXWsFe249st_4roOp4PdieTLpcpTu` |
| 原稿 | `1EdIS79ldts_qCN-D_BTkDV07g9m9rz23Rt3yxCtsxtI` | https://docs.google.com/spreadsheets/d/1EdIS79ldts_qCN-D_BTkDV07g9m9rz23Rt3yxCtsxtI/edit | `1zqvhyTziWiGSPzbtep9PLU44TRnkX0N4XUltmBp29yKOR9pmodLiZniT` |

所有者アカウント: kuro.movile@gmail.com

## 完了した作業

1. **Google Drive接続の疎通確認**
   - Claude (claude.ai) の Google Drive コネクタ経由でアクセス。
   - 一度、接続不調（`list_recent_files` がファイルを返さない/対象ファイルが
     Not Found）が発生。ユーザーが接続設定を変更後、再接続して解消。

2. **GASコードのクローン（`clasp`使用）**
   - `clasp login` 済み（このマシン上でOAuth認可完了）。
   - `clasp clone <スクリプトID>` で2プロジェクトを取得。
   - 保存先:
     - `gas-projects/project1/` — 23ファイル。"concept" 側に紐づくメインの
       タスク/スケジュール管理ロジック一式
       （makeSchedule.js, menu.js, mode.js, workdata.js, myUtil.js, group.js,
       analysis.js, deleteBlank.js, portfolio.js, reference.js, todolist.js,
       setting.js, format.js, agendaData.js, site.js, reminder.js, tool.js,
       html.js, index.html, convert.js, task.js, validation.js, appsscript.json）
     - `gas-projects/project2/` — 4ファイル。"原稿" 側に紐づく小規模スクリプト
       （Code.js, sheet.js, data.js, appsscript.json）

3. **スプレッドシート本体のダウンロード**
   - Drive の `download_file_content`（export）で xlsx として取得。
   - 保存先:
     - `spreadsheets/concept.xlsx`（62,755 bytes）
     - `spreadsheets/manuscript.xlsx`（15,463 bytes、元ファイル名「原稿」）
   - 両ファイルとも zip 構造として整合性検証済み（`zipfile.testzip()` でOK）。

## ディレクトリ構成（現状）

```
task_tracking/
├── HANDOFF.md              ← 本ファイル
├── spreadsheets/
│   ├── concept.xlsx
│   └── manuscript.xlsx
└── gas-projects/
    ├── project1/            ← concept と紐づくGAS（メイン管理ツール本体と思われる）
    └── project2/            ← 原稿 と紐づくGAS（補助的なスクリプト）
```

## 注意点・トラブルシューティング履歴

- **大きなbase64データを手動転記しようとして2回破損させた**ため、最終的には
  Claude Code のセッションログ（`~/.claude/projects/.../<session-id>.jsonl`）
  から `toolUseResult` を直接パースし、base64デコードしてファイル化するPython
  スクリプトで復元した。同様の作業（GAS/スプレッドシートの再DL等）を行う際は、
  ツール出力を経由してファイル化する方式を使い、AIによる手動コピペは避けるのが安全。
- `clasp` の認証情報はこのマシンのユーザー（sh1）のホーム配下に保存されている
  想定（`~/.clasprc.json` 等）。別環境でclasp操作を続ける場合は再ログインが必要。
- Google Drive コネクタは一時的に不安定になることがある（今回は接続設定の
  変更で復旧）。

## 引き継ぎ事項（2026-09-22 Kimi Codeにて完了）

- [x] `gas-projects/project1` と `project2` のコード内容を精査し、
      2つのGASプロジェクトがどう連携しているかを整理した。
      → **結論: ライブラリ呼び出しによる直接連携は皆無（project2 → project1 の
      呼び出し0件・宣言のみの死に依存）。原稿ブックのデータを介した間接連携のみ。**
- [x] `spreadsheets/*.xlsx` を開き、シート構成・命名規則・データモデルを
      ドキュメント化した。（openpyxlによるパースで確認）
- [x] タスク管理ツールとしての要件を逆算し、移植/再実装方針を検討した。
- [x] ローカルのxlsxをプログラムで解析して内容を確認した。

**上記すべて `docs/SPECIFICATION.md`（仕様書）にまとめ済み。**

### 仕様書の要点

- このツールは**同人漫画制作の工程管理ツール**（concept=企画ブック、
  原稿=ページ×工程マトリクス）。
- project1 は外部ライブラリ `library`（ID `1EvLyg...`）に46カ所依存しており、
  ライブラリなしでは現行コードは一切動かない。
- トリガー/onOpen なしの完全手動運用。2014年時点で analysis 系は放棄宣言あり。
- Sites/UiApp/ScriptDb 依存経路は廃止APIのため死滅。
- 再実装の推奨スコープと技術置き換え対応表は仕様書 §9 参照。

### 次にやること（新たな未着手）

- [x] 外部ライブラリ `library` / Cloud SQL DB の所在確認 → **2026-09-22 利用者より
      「すでに失われている」ことを確認。外部ブック4冊・Docs・Sites も同様に
      失われた扱いでよいものとする**。
- [x] modemap DB の復元可能性の検証 → **可能と判明**。SQL全文が data.js に残って
      おり、スキーマ・カラム名・行（モード名）は高確度で復元できた。
      成果物: `restoration/modemap.sql`（DDL+シード）, `restoration/modemap.csv`,
      `docs/MODEMAP_RESTORATION.md`（復元仕様・カテゴリ対応表・キャリブレーション手順）

### プロジェクトのターゲット（2026-09-22 に利用者より方針確定）

- **本プロジェクトの復元ターゲットは project2**（Cloud SQL の modemap マスタ
  = タスクの重みデータ、および「原稿 lineart の残作業時間集計→analysis 出力」
  機能）。これが最後まで実際に使われていたツール。
- **project1 は参考扱い**（モード体系・工程分類の理解のための参考资料）。
- 残る決定事項: 復元版の実装方式（docs/MODEMAP_RESTORATION.md §6 の
  A/B/C 案。B案「GAS＋スプレッドシート化」を推奨）。

### 進捗メモ（2026-09-22、Kimi Code セッション終了時点 → Claude へ引き継ぎ）

- 実装方式は**利用者により「ローカルPython版・最小構成・将来WebUI」が確定**
  （MODEMAP_RESTORATION.md §6 の案C相当。マスタ=CSV、入力=元形式のxlsx、
  出力=CLI）。
- **実装前の設計が完了し、`設計書.md`（プロジェクトルート）がレビュー待ち**。
  設計内容: `taskman/` パッケージ4モジュール構成、openpyxlのみ依存、
  analyze.py は data.js の逐語対応の純粋関数、未定義モードは警告+skip。
- **次の作業: `設計書.md` のレビュー → その通り実装開始**（§7 の手順1〜6）。
  設計変更がなければそのまま進めてよい。
- マスタ CSV（`restoration/modemap.csv`）の値は仮置き。実装検証で値の一致は
  求めない（ウエイトは実測キャリブレーションで後から調整する）。

### 実装完了（2026-09-23、Claude セッション）

- `設計書.md` をレビューし、data.js（project2）と突き合わせて乖離を発見。
  1. **【重大・利用者確認済みで意図的に変更】mode適用単位**。data.js の
     `getWorkTime()` は `modemap[workdata[0]['mode']]` — そのplotの
     **シート上で最初に出現した行のmode**だけで重みテーブルを1つ選び、
     plot内の全行に同一の重みを適用していた（設計書§5.1の擬似コードは
     行ごとにmode参照しており、実は元コードと食い違っていた）。実データで
     検証したところ7 plot中4つ（砕月暴走・会議・万博 蛸蜥蜴・事件後）で
     modeが行によって混在しており、有意な差になることを確認。
     → これはページ単位でmodeが変わりうる工程管理ツールとして元コードの
     見落としと判断し、**利用者に確認の上、「行ごとに自分のmodeを使う」
     方式へ意図的に変更**（元コードの忠実再現ではなく実用上正しい方を採用）。
     修正前後で合計が56.3h→60.3hに変化（mode混在4 plotのみ値が変わり、
     他3 plotは不変であることを確認済み）。
  2. plotは同一シート内で非連続に再出現しうる（例: 砕月暴走）ため、
     グルーピングは「plot名で全行をフィルタ」で実装（連続ブロック分割ではない）。
  - 設計書の「未定義モードは元TypeError」という記述は誤り（実際は無言で
    NaN→出力フィルタで消える、クラッシュしない）と判明。警告+スキップという
    実装方針自体は妥当なので変更なし（ただし未定義モードのスキップ単位も
    上記1の変更に合わせて「plot単位」→「行単位」になっている）。
- 実装ファイル: `taskman/__init__.py`, `master.py`, `sheet.py`, `analyze.py`,
  `cli.py`, `__main__.py`。依存は openpyxl のみ（設計書どおり）。
- 動作確認: `python -m taskman analyze spreadsheets/manuscript.xlsx` で実行し、
  正常終了。sketch/lineart群が全plotで0件（非表示）になるが、これは元データで
  sketch/head/body/clothが全ページ `finished` 済みのため正しい挙動と確認済み。
  object/illustrate/effect群は正常に値が出力される（合計 60.3h、上記「行ごとに
  自分のmodeを使う」方式での結果）。
- テストコードは方針どおり書いていない（設計書§8: スモーク実行のみ）。

### 未着手・次にやること

- [ ] `restoration/modemap.csv` の重み値は仮置きのため、実測キャリブレーション
      （MODEMAP_RESTORATION.md §5）が必要。
- [ ] xlsxへの書き戻し（analysisシート相当）は未実装（設計書2.2で将来拡張と
      明記済み）。CLIオプション or WebUIで対応する場合は改めて設計が必要。
- [ ] concept ブック（`spreadsheets/concept.xlsx`）側の lineart 読込は
      データ開始行が異なる（原稿=3行目、concept=4行目）ため未対応。
      設計書§7-7の `--data-start-row` オプション案を検討するか判断待ち。

### WebUIダッシュボード実装完了（2026-09-23、Claude）

- `webui設計書.md`（円グラフ・サイズ可変ドーナツ方式）どおり実装。
  `python -m taskman dashboard <input.xlsx> [-o dashboard.html]` で
  サーバー不要の単一HTMLファイルを生成する
  （新規Python依存なし。Chart.jsはCDN参照）。
- 実装ファイル: `taskman/view_data.py`（画面用データ変換）、
  `taskman/dashboard.py`（HTML生成）、
  `taskman/templates/dashboard.html.tmpl`、`analyze.py`に`total_time()`
  追加、`cli.py`に`dashboard`サブコマンド追加。
- タブ1（全体俯瞰）: plotごとのサイズ可変ドーナツ（外径=残時間の
  sqrtスケール、塗り=進捗％）。タブ2（plot別）・タブ3（カテゴリ別）は
  通常の円グラフ＋数値表。色は dataviz skill検証済みパレット
  （円の輪の継ぎ目を含む隣接ペアも検証済み）。
- ブラウザ実機確認済み（claude-in-chrome、3タブとも正常表示）。
- 設計からの変更点: HTML生成をstring.Template→素朴なstr.replace()に変更
  （JSのテンプレートリテラルとの`$`衝突を避けるため。依存追加なしは
  変わらず）。詳細は`webui設計書.md`末尾「実装メモ」参照。
- `dashboard.html`（生成物）は`.gitignore`に追加済み（ビルド出力のため
  コミット対象外）。
- 未着手: concept側ブック対応、タブ3の8件超フォールバックは実装済みだが
  実データでは未発動（現状7 plot）。サイズ・角度のクリップ定数は仮値の
  まま（見た目に違和感なかったため今回調整なし）。
