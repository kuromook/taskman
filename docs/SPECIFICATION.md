# タスク管理ツール 仕様書（リバースエンジニアリング版）

- 作成日: 2026-09-22
- 作成方法: `gas-projects/project1`（23ファイル）・`gas-projects/project2`（4ファイル）・
  `spreadsheets/*.xlsx`（2ファイル）を精査して仕様を逆算したもの。
  オリジナルの設計書は存在しない。
- 注意: 本書は「コードとスナップショットから読み取れる仕様」を記述する。
  推測が入る箇所は「※推測」と明記する。

---

## 1. エグゼクティブサマリ

このツールは**同人漫画制作の工程管理ツール**である。

- 「concept」ブック（企画・タスク管理）と「原稿(manuscript)」ブック（ページ×工程の進捗
  マトリクス）の2系統スプレッドシートを横断集計し、以下を自動生成する:
  1. 日別タイムライン（`timeline` シートへの見積工数書き出し）
  2. 工程別の残作業時間分析（`analysis`/`design`/`manuscript` シートへの集計）
  3. 残り日数換算のリマインダー メール（1日9時間稼働想定）
  4. Liquid Planner へのタスク登録用文字列（セル背景色でタスク紐付け）
  5. 週次スケジュールチャート（Google Document への画像挿入）
  6. アジェンダ（時間帯別の作業一覧＋作業指針）の Google Sites 公開
- ただしコードには 2014-05-05 時点での**大規模な機能放棄の記録**があり
  （`analysis.js:4-8`「analysis system is abandoned」「Liquid Planner makes scheduling
  easy.」、`reminder.js:4-6`、`todolist.js:4`）、実際に現役で使われていたのは
  一部の集計パイプラインに絞られていたと推測される。
- 2014年以降に Google 廃止となった API（SitesApp / UiApp / ScriptDb）に依存する
  経路は現在動作しない。

### 1.1 最重要の事実（3点）

1. **project1 は外部ライブラリ `library`（ID `1EvLyg...`, v16）に46カ所依存**しており、
   このライブラリのソースはローカルに存在しない。`library.getSheet` / `sendmail` /
   `cellReverse` 等が無ければ現行コードは**一切動かない**。
2. **project2 → project1 のライブラリ呼び出しは 0 件**。`appsscript.json` で
   `MYAPPscheduling` v72 を宣言しているだけで、コード内では未使用（死に依存）。
   2プロジェクトは「原稿スプレッドシートのデータ」を介した**間接連携**のみ。
3. **トリガー自動実行の仕組みは一切存在しない**（`ScriptApp` 不使用、`onOpen` は
   コメントアウト）。すべてメニューからの手動実行が前提。

---

## 2. 用語集

| 用語 | 意味 |
|---|---|
| ブック | Google スプレッドシート本体（concept / 原稿 / 外部マスタ等） |
| 工程マトリクス | `lineart`/`color`/`parts` シートの「行=ページ、列=工程」2次元表。セル値=進捗ステータス |
| ステータス | マトリクスセルに入る値: `finished` / `not use` / `pending` / `working` / `partial` / 空白(未着手) |
| 時刻帯 (timeSlot) | `morning`/`afternoon`/`evening`/`night`（実時間帯）＋`today`/`tomorrow`（擬似時間帯） |
| week 割当 | タスク行に `week1`…`week9` / `later` を手動入力して週計画を立てる運用 |
| タグ構文 | 作業の `info`/`tag` 文字列に含む `[section]` `(mode)` `<operation>` 形式のメタ情報 |
| principle | 作業指針ドキュメント（Google Docs）。見出しにタグを付け、agenda とマッチングさせる |
| LP | Liquid Planner（当時併用していたプロジェクト管理SaaS）。セル背景色=LPタスク色 |
| QCサイト | `qc.paranoiacat.com`（作者の品質管理ツール。作業名からリンクを生成） |

---

## 3. システム構成

### 3.1 コンポーネント構成図

```
┌──────────────────────────────────────────────────────────────────┐
│ concept ブック (ID: 0AsGG...UZlE)                                │
│  project / concept / misc / study / programming / loop / rebuild │
│  scenario / color / lineart / parts / calendar / construction    │
│  timeline / analysis / design / manuscript / chart / ...         │
│   └─ project1 (GAS, 23ファイル)  ← 本ツールのメインエンジン        │
└──────────────┬───────────────────────────────────────────────────┘
               │ project シートの ssID 経由で横断読み込み
               ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ 原稿 ブック               │    │ project2 (GAS, 4ファイル)        │
│  lineart / color / parts  │◄──►│  scheduleメニュー: task analysis │
│  analysis (出力先)        │    │  Cloud SQL の modemap を参照    │
└──────────────────────────┘    └─────────────────────────────────┘

┌─ 外部マスタ（ハードコードID参照・ローカル非所持）───────────────────────┐
│ schedule-init (0AsGG...V0R0E): daylist / mode / group / scenario(色)  │
│ log (0AsGG...GZHc): 1シート目=見積ログ / docs シート                  │
│ reference (0AsGG...eWc): converter / googleDocs / pdfDocs / ...       │
│ Google Docs: timeAgenda (1tadL...) / principle (1QvIrU.../個別)       │
│ Google Sites: paranoiacatworks/agenda 等（廃止）                       │
│ Cloud SQL: project-211906:asia-northeast1:sh1-sql/modemap（project2） │
│ 外部GASライブラリ: library (1EvLyg...) / MYLIBhtml / MYLIBsummary /   │
│                    MYLIBarray                                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 project1 / project2 の役割分担

| | project1 | project2 |
|---|---|---|
| バインド先 | concept ブック | 原稿 ブック |
| スクリプトID | `1q-vHyJe6HhCUO058F2MalV4NQcIcXWsFe249st_4roOp4PdieTLpcpTu` | `1zqvhyTziWiGSPzbtep9PLU44TRnkX0N4XUltmBp29yKOR9pmodLiZniT` |
| ファイル数 | 23 | 4 |
| ランタイム | V8 | 未指定（`for each` 旧構文=Rhino前提。V8では構文エラー） |
| タイムゾーン | America/Los_Angeles | Asia/Tokyo |
| 役割 | 全プロジェクト横断の集計・スケジュール・分析・通知エンジン | 原稿 lineart の残作業時間集計のみ（単機能） |
| project1 への依存 | ― | `MYAPPscheduling` を宣言するが**呼び出し0件** |

### 3.3 連携関係の結論

- **コード呼び出しによる直接連携は存在しない**（双方向とも0件）。
- project1 は concept ブックの `project` シートに記載された ssID 経由で原稿ブックの
  `parts`/`color`/`lineart`/`rebuild` シートを `library.getSheet(name, id)` で直接開く
  （`portfolio.js:248-269`）。
- project2 は原稿ブックの `lineart` シートを読み、`analysis` シートに残時間を書く。
- つまり連携は「**原稿ブックというデータを介した間接連携**」である。
  project2 が `modemap` DB（Cloud SQL）を正とする設計は、project1 が依存する
  schedule-init の `mode` シートを置き換える後継実装と推測される（置き換え途中）。

### 3.4 外部ライブラリ依存（project1）

| ライブラリ | 使用数 | 主な使用シンボル（推測機能） |
|---|---|---|
| `library` (v16) | 46カ所 | `getSheet`（シートラッパー取得）/ `sendmail`（メール送信）/ `viewMode`,`viewManual`,`hideRowsBorder`（ビュー制御）/ `cellReverse`,`cellsConcat`,`unique`,`deepCopy`,`encode`,`math60`（汎用処理）/ `getDic`,`getDicByColumn`,`aryConsistObj`,`objConsistObj`,`arrayApply`,`objApply`（シート→オブジェクト変換）/ `TableHtmlFromAry`（HTML生成）/ `cellConsistencyCheck` |
| `MYLIBhtml` (v1) | 4カ所 | `taged`,`sand`,`end`（HTMLタグ生成: site.js のみ） |
| `MYLIBarray` (v1) | 2カ所 | `mergedArray`（配列マージ: site.js のみ） |
| `MYLIBsummary` (v12) | 2カ所 | `pubData`,`readPublishData`（発行実績: 不使用系） |

さらに、**project1 内に定義が無いのに参照されているシンボル**が多数存在し、
いずれも外部 `library` 由来または削除済みコードと推測される:
`ProjectCalendar`, `readScenarioData`, `ScenarioData(Array)`, `InitSetting`, `Dic`,
`ProjectSetting`, `modeDataArray`, `modeMapArray`, `createProject`, `applyWeek`,
`scenarioNewEntry`, `scenariosSetPP`, `applyScenarioDataToLineartSheet`,
`todoListUpdate`, `testDeleteSummry`, `summeryDocId`, `thisSSId`。
これらを呼ぶ経路は現在エラーになる（§8.1 参照）。

---

## 4. データモデル

### 4.1 concept ブック（21シート、named range なし）

シート命名規則は日付系ではなく**工程/機能カテゴリ名（英語小文字）**。
ブック種別の判定は `ss.getName()`（'concept' / '原稿' 等）で行う（`setting.js:29`）。

| # | シート名 | 可視 | サイズ | 種別 | 内容 |
|---|---|---|---|---|---|
| 1 | project | visible | A1:K3 | **設定マスタ** | name,status,ssID,summaryDocID,localPrincipleID,daylist,color,milestone,agendaNumber,startDate,deadline。`Project()` が読む |
| 2 | concept | hidden | A1:E19 | タスク一覧 | A=name,B=tag,C=memo(作品名),D=work time,E=status。タグに `[outsidework]<research>` 等のタグ構文 |
| 3 | study | visible | A1:E2 | タスク一覧 | 同上形式 |
| 4 | misc | visible | A1:E4 | タスク一覧 | 〃 |
| 5 | programming | visible | A1:E4 | タスク一覧 | 〃 |
| 6 | loop | visible | A1:F15 | 繰り返しタスク | +E=on/off、F=`(on evening tuesday)` 形式のルール式 |
| 7 | rebuild | visible | A1:R29 | 修正依頼管理 | 1-5行=level定義(demand/revise/fatal/need/research)、7行目〜データ(level/place/problem/tag/solution/progress/date/worktime) |
| 8 | scenario | hidden | A1:L12 | シナリオ | 1シーン=4行ブロック(scene/plot/mode/work time ＋ progress/page/pp ＋ compose/write/continuity/rough ＋ character/place/item/cut) |
| 9 | lineart | hidden | A1:AG6 | 工程マトリクス | ペン入れ。§4.4 共通構造 |
| 10 | color | hidden | A1:AP18 | 工程マトリクス | 彩色。構成は lineart と同型 |
| 11 | parts | hidden | A1:I5 | 工程マトリクス | パーツ/素材設計(rough/research/parts/image board) |
| 12 | timeline | hidden | A1:T27 | **GAS出力先** | §4.4.3 |
| 13 | analysis | hidden | A1:Z62 | **GAS出力先(集計ハブ)** | B-E=construction集計、F-M=work analysis、N-T=result総括、U-Z=task表。`scheduleReminder` は R3:R5 を読む |
| 14 | design | hidden | A1:I28 | **GAS出力先** | `makeDesignAnalysis` の書き込み先（ヘッダのみのスナップショット） |
| 15 | manuscript | hidden | A1:L90 | **GAS出力先** | `makeLineArtAnalysis` の書き込み先（ヘッダのみ） |
| 16 | construction | hidden | A2:M30 | 工事量見積 | E4:H10=数量見積(comic page 16枚×indicator 60等)、E13:H16=summary(rest/finished/all)、E19:I22=週別、E24:H29=金額見積(総計190,000、`=F26*G26` 数式)。A-C列=プロジェクト名/イベント/日付 |
| 17 | calendar | hidden | A1:M18 | マイルストーン | 1行目=イベント名、2行目=genre(milestone/reminder/event)、3行目=日付、4行目=span、5行目〜=TODO。**A10=開始日・A12=締切**（`showInputStartDate/EndDate` の書き込み先） |
| 18 | chart | hidden | G4:L13 | チャート用集計 | 行=concept/other/scenario/design/…finishing、列=week1..week4/later。`getChartDataBySheet` が (4,7) 起点で読む |
| 19 | convert | hidden | A1:H83 | Photoshop変換設定 | name/preset/opacity/layerName/character/alternative/parts/page。`convertSheetSort` が整備 |
| 20 | tone | hidden | A1:K6 | トーン指定 | 10%net/20%net/…/black/white/gradation。GAS 未参照 |
| 21 | DSM | hidden | A1:I9 | 設計行列 | Design Structure Matrix（plot/scenario/character rough…の依存「x」）。GAS 未参照 |

**`project` シートの設定値（スナップショット時点）**:

| name | status | ssID | daylist | color | agendaNumber | 期間 |
|---|---|---|---|---|---|---|
| concept | active | 0AsGGBeb_eVwhdGpfbm0wbGI3MldLSnhmUW12eWdUZlE（自己） | daylist | black | 4 | ― |
| 漫画原稿 | active | 0AsGGBeb_eVwhdDY4ZFFpWGwzQXNZY1A3T0RKYXF1UWc（旧ID形式） | daylist | f691b2 | 4 | startDate=2014-07-01, deadline=2014-07-29 |

※ 原稿の ssID が旧形式IDで、現在の原稿ブックID（`1EdIS79...`）と不一致。
原稿ブックが作り直されたか、スナップショットが古いかは不明。※推測

### 4.2 原稿 ブック（4シート、named range なし）

| シート名 | 可視 | サイズ | 内容 |
|---|---|---|---|
| lineart | visible | A1:V37 | ペン入れ進捗。**A=page,B=plot,C=mode,D=scene,E=title**。F-V=工程列: sketch/head/body/cloth(character系)、item/background(lineart系)、base/erotic/shadow/back/front/mood/onomatopeia/speaking 等(monofin系)。データ3行目〜（35ページ分）。値=finished/not use/空白 |
| color | visible | A1:AJ7 | 彩色工程（表紙・目次等6行）。concept color と同型 |
| parts | hidden | A1:I7 | キャラ/背景パーツ。F3:I3 に `=COUNTBLANK(F4:F6)+COUNTIF(...)` 数式（範囲が生き残っている） |
| analysis | visible | A1:B12 | **project2 の出力先**。A=name(plot+" "+カテゴリ)、B=残り時間(h)。A2/B2に `=SUM(...)` 数式 |

### 4.3 外部ブック・外部リソース（ハードコードID）

| ID | 用途 | 参照箇所 |
|---|---|---|
| `0AsGGBeb_eVwhdGpfbm0wbGI3MldLSnhmUW12eWdUZlE` | concept本体（`project` シート） | setting.js:14 |
| `0AsGGBeb_eVwhdERqV3ozbFlKeHo4a2dFNk5ZbUV0R0E` | **schedule-init**（`daylist`/`mode`/`group`/`scenario`色） | setting.js:123, tool.js:21, mode.js, group.js |
| `0AsGGBeb_eVwhdEJOSmpiNW5iWHdTVXIxb3I5R0dGZHc` | log（1シート目=見積ログ、`docs` シート） | portfolio.js:118, todolist.js:103 |
| `0AsGGBeb_eVwhdDdFQUM3TEdTZWtKT09aSVpnRC1ReWc` | reference（`converter`/`googleDocs`/`pdfDocs`/`eBooks`/`books`/`web`） | reference.js:321（現在未使用ルート） |
| `1EdIS79ldts_qCN-D_BTkDV07g9m9rz23Rt3yxCtsxtI` | 原稿（project2 が openById） | project2/data.js:102,128 |
| Doc `1tadLOuTbBdBTS49DrTImAF9X02p3TFsBJD7qX4OIHQ8` | timeAgenda（時間別agenda文書） | setting.js:151 |
| Doc `1QvIrUWxUpLUtrRSGyUSx8hUJLtJCmIFigHlxoTWUzIw` | principle マスタ | reference.js:446 |
| Sites `…/paranoiacatworks/agenda` 等 | agenda/speech/work-summary 公開先（廃止） | site.js:75,124 |
| Cloud SQL `project-211906:asia-northeast1:sh1-sql/modemap` | mode別作業時間マスタ（project2） | project2/data.js:4 |

### 4.4 共通データ構造

#### 4.4.1 工程マトリクス（lineart / color / parts 共通）

```
      A      B      C     D          E        F〜            最終列
1行目: page | scene | mode | salesTag | option | operation名（div1-4, character sketch, …）
2行目:      （section名: character / lineart / monofin / colorfin / material / cut 等）
3行目:      （集計数式: =COUNTBLANK+COUNTIF("partial"/"pending"/"working") / =SUM(...)）
4行目〜: データ。セル値 = 進捗ステータス
```

- GAS は `(4,6)`〜最終行×最終列をスキャンし、セル値が時刻帯正規表現
  （`morning|afternoon|evening|night|today|tomorrow`）に一致したものを
  「その時刻帯に予定されている作業」として拾う（`portfolio.js:175-197`）。
- **セル背景色もデータ**。`WorkDataC` の `color` に保持され、
  LPタスク識別子として使われる（§5.4）。ヘッダのオレンジ `#FF9900`=作業列。
- ステータス語彙: `finished`（完了）/ `not use`（対象外）/ `pending` /
  `working` / `partial`（一部完了）/ 空白（未着手＝残作業）。

#### 4.4.2 行指向タスク（concept / misc / study / programming / loop / rebuild / scenario）

| シート | 列構成 | 備考 |
|---|---|---|
| concept系4シート | A=name,B=tag,C=memo,D=work time,E=status | tag に `[section](mode)<operation>` 構文 |
| loop | +E=on/off,F=ルール式 | ルール式: `(on|everyday) <時刻帯> <曜日>`。例: `(on evening tuesday)` |
| rebuild | level/place/problem/tag/solution/progress/date/worktime | 7行目〜。修正依頼=バグ管理 |
| scenario | 4行×1シーンのブロック | scene/plot/mode/work time ＋ 進捗＋登場要素 |

#### 4.4.3 timeline シート（出力フォーマット）

```
1行目: morning | afternoon | evening | night | today | tomorrow | 週の日付(7列目〜) | later
2-3行目: （予備/クリア対象）
4行目:   "estimated total : X H"（時刻帯別の見積合計）
5-10行目: parts / color / concept / outsidework / lineart / scenario : X hour
11行目〜: 作業明細
```
時刻帯の列番号は schedule-init `daylist` シートの `id` 列で決まる。
`formatTimelineTop` が calendar!A10/A12（開始日/締切）から週の日付ラベルを生成する。

#### 4.4.4 analysis シート（出力フォーマット）

| 領域 | 範囲 | 内容 |
|---|---|---|
| construction 集計 | B-E | 工事量の計画×係数。`=B3*C3/10` 等の数式 |
| work analysis | F3:M10 | section別の all/finished/not use/rest/pending/workers/outsource |
| indigestion | E3:E9 | 計画−実績の未消化数 |
| result 総括 | N2:T5 | design/lineart/misc の indigestion/rest/finished/all。**R3:R5=rest時間**（reminder が読む） |
| task 表 | U3:Z | U=色,V=タスク名,W=finished,X=rest,Y=progress%,Z=all。3行目に SUM 数式 |

#### 4.4.5 時間の単位体系（※3系統并存・要注意）

| 系統 | 単位 | 変換 |
|---|---|---|
| `WorkDataA`（行指向タスク） | **0.1時間単位の整数** | `getHour()=time/10`、`getMin()=time*6` |
| `WorkDataC`（マトリクス） | **分**（動的計算） | `dic.modeMap.time()` = `ratio×val×60/1000` |
| project2（原稿分析） | 分→`parseInt`→`/60` | 時間(h)で出力 |

#### 4.4.6 時刻帯（daylist）体系

- schedule-init の `daylist` シート: `timeSlot, period, id, docId, url` 列から構築。
- `agendaNumber=4` は**ハードコード**（project シートの値は参照しない。
  `daylist8` 分岐は dead code）。
- `SettingData` は dayList（実4帯）→ todayList（+today）→ allDayList（+tomorrow）
  と3段階のリスト＋それぞれの正規表現 `re` を生成（`setting.js:108-122`）。

---

## 5. 機能仕様（メニュー経路）

### 5.0 メニュー定義全体

`menuData()`（menu.js:90-166）が concept 用・manuscript 用の2構成を返す。
`CreateMenu()`（menu.js:168）は concept 版のみ登録。`onOpen` はコメントアウト
（menu.js:172-176）のため**メニュー表示自体が手動実行**。manuscript 構成の
呼び出し元はコード上存在しない。

**【concept メニュー】項目→実行関数対応表**

| メニュー | 項目 | 実行関数 | 定義場所 | 現状 |
|---|---|---|---|---|
| daily | Agenda | `makeAgenda` | portfolio.js:370 | △ Sites廃止で失敗する |
| schedule | task analysis | `writeTaskAnalysis` | task.js:72 | ○ 現役 |
| schedule | background color | `showCellBackgroundColor` | task.js:15 | ○ |
| schedule | set mode validation | `setModeValidation` | validation.js:25 | ○ |
| schedule | reNew Portfolio | `reNewPortfolio2` | portfolio.js:374 | ○ 現役（中核） |
| tool | delete blanks | `deleteBlanks` | deleteBlank.js:3 | ○ |
| tool | lineart stripe | `lineartStripeGd` | tool.js:71 | ✕ UiApp廃止 |
| tool | convert sheet sort | `convertSheetSort` | convert.js:1 | ○ |
| test | restCheckFormat | `restCheckFormat` | format.js:92 | ✕ ProjectSetting未定義 |
| test | consistency check | `modeConsistencyCheck` | tool.js:1 | ○ |
| maintenance | Work analysis | `reNewWorkStructure` | analysis.js:756 | ✕ readScenarioData未定義 |
| maintenance | scenario set PP | `scenariosSetPP` | ― | ✕ 未定義（死項目） |
| maintenance | make principle | `makePrinciple` | reference.js:351 | ○ |
| maintenance | todo list | `todoListUpdate` | ― | ✕ 未定義（死項目） |
| maintenance | deleteScheduleSection | `testDeleteSummry` | ― | ✕ 未定義（死項目） |
| maintenance | putChartToSummery | `putScheduleChartToSummeryReverse` | makeSchedule.js:153 | △ |
| maintenance | publish summary | `publishSummary` | reminder.js:60 | △ 不使用系 |
| maintenance | new scenario entry | `scenarioNewEntry` | ― | ✕ 未定義（死項目） |
| maintenance | apply to lineart sheet | `applyScenarioDataToLineartSheet` | ― | ✕ 未定義（死項目） |
| maintenance | create calendar | `createProject` | ― | ✕ 未定義（死項目） |
| maintenance | apply week | `applyWeek` | ― | ✕ 未定義（死項目） |
| maintenance | save estimation log | `saveLog` | portfolio.js:378 | ○ |
| man | 各種マニュアル×4 | `schedulingManual` 等 | menu.js:72-86 | ○ `library.viewManual` 委譲 |

**【manuscript メニュー】**: view 6項目（`showAll`/`lineartView`/`normalLineartView`/
`eroticLineartView`/`eroticFinishingView`/`normalFinishingView` → `library.viewMode`
委譲）＋ schedule/tool/test（concept と同一配列を再利用）。呼び出し元なし。

### 5.1 portfolio 再構成（`reNewPortfolio2`）— 現役の中核

`portfolio()`（portfolio.js:331-367）の処理フロー:

1. `project = new Project()` — concept 本体の `project` シートを読み
   プロジェクト一覧を構築（`list`/`active`/`listMilestoneProject`/`current`）。
   アクティブ判定は**スプレッドシート名の一致**（`setting.js:28-34`）。
2. `settingData = new SettingData()` — schedule-init の `daylist` シートから
   時刻帯マスタを構築。
3. `moduleInit()` — `MYAPP.timelineFormat.portfolio/timeline`（timeline の
   クリア範囲）を構築。
4. `portfolioInit()` — `weekWorkA`/`weekWorkC`=[]、`dic={groupMap:GroupMap,
   docList:DocList, todoList:TodoList, modeMap:ModeMap}`、`agendaReference={}`。
5. `makePortfolio()`（portfolio.js:273-326）:
   - `MYAPP.timelineFormat.portfolio()` で timeline 書込領域をクリア;
   - active プロジェクトごとに `makePrinciple()`（作業指針パース）を
     `agendaReference[name]` に保持;
   - プロジェクト名が `"concept"` なら `.concept()`、それ以外なら `.manuscript()`
     で各シートを走査（§5.1.1）;
   - `makeAgendaData()` で時間帯別 `agendas` を構築（§5.5）;
   - `writeDayWork3(day)` で timeline に「estimated total / カテゴリ別時間 /
     作業明細」を書き込み;
   - `deleteBlankRows('timeline')`。
6. 返値 `{agenda(), saveLog()}`:
   - `agenda()` → `updateSiteOfSpeech()` + `updateSiteOfAgenda()`（Sites。廃止）
   - `saveLog()` → `addEstimateWorkTime()`（§5.7）

#### 5.1.1 シート走査（`makePortfolioData(id, re)`）

| 走査 | 対象 | 抽出条件 | 生成オブジェクト |
|---|---|---|---|
| `.concept()` | concept/misc/study/programming | E列の値が時刻帯 `re` に一致 | `WorkDataA` → `weekWorkA` |
| 〃 | loop | on/off が有効＋当日ルール一致 | `WorkDataLoop`→`WorkDataA` |
| 〃 | rebuild | 7行目以降を全行 | `RebuildData` |
| `.manuscript()` | parts/color/lineart | (4,6)〜でセル値が `re` に一致。**背景色も取得** | `WorkDataC` → `weekWorkC` |
| 〃 | rebuild | 同上 | `RebuildData` |
| `.analysis()` | 上記3シート＋rebuild | より広い正規表現（finished/pending/rejected 等） | 分析用（task analysis で使用） |
| 〃 | scenario | 4行ブロックを `ScenarioData` でパース | `scenarioDataArray` |

#### 5.1.2 作業オブジェクト（workdata.js）

- `WorkDataA(sheet,name,time,week,info,memo)`: info 文字列から
  `[section]`/`(mode)`/`<operation>` を正規表現で分解。time は 0.1h 単位。
  `count()` は `week` の `weekN`→N（`later`→0）。
- `WorkDataC(name,page,scene,mode,operation,section,color,val,option,salesTag)`:
  所要時間は `dic.modeMap.time(mode,operation,section,option)` で動的計算（分）。
  `group()` は `dic.groupMap.check()` で `alone`/`vertical`/`horizontal` 判定。
- `WorkDataLoop`: `(on|everyday) <時刻帯> <曜日>` をパース。
  `isActive()` は **`getUTCDay()`** で曜日照合（§7.2 タイムゾーン問題）。
- `DataArray` / `TimelineArray`: 集計メソッド群（§5.3 で使用）。

### 5.2 Work analysis（`reNewWorkStructure`）— 集計パイプラインの統括

`analysis.js:756-802`。設計上の中核だが `readScenarioData()` が未定義のため
**現状は途中で例外終了する**（§8.1）。設計上のフロー:

```
reNewWorkStructure()
 ├─ moduleInit()                              （format.js:25）
 ├─ readConstructionData()                    analysis!A3:C9 → constDataArray
 ├─ readScenarioData()                        ※未定義シンボル。ここで落ちる
 ├─ design / manuscript シートをクリア        clearRangeByIndex
 ├─ makePortfolioData(ssID, re).analysis()    全シート走査 → weekWorkA/C
 ├─ makeWorkAnalysis()                        analysis!F3:M10（§5.3.1）
 ├─ indigestionAnalysis()                     analysis!E3:E9（計画−実績）
 ├─ makeDesignAnalysis()                      design シートへ5ブロック書込（§5.3.2）
 ├─ makeLineArtAnalysis()                     manuscript シートへ（§5.3.3）
 ├─ makeMiscAnalysis()                        analysis!N7〜（タイトル別集計）
 ├─ makeTotalAnalysis()                       analysis!N2:T5（総括）
 └─ scheduleReminder()                        残り日数メール（§5.6）
```

### 5.3 分析機能の内訳

#### 5.3.1 状態別集計（`makeWorkAnalysis`, analysis.js:605）

`DataArray(weekWorkA+weekWorkC).getWorkAnalysis()` で section 別の
finished/pending/rejected/workers/outsource/notUse/time を集計し
analysis!F3:M10 に書く。

#### 5.3.2 design 分析（`makeDesignAnalysis`, analysis.js:463）

`getDesignSummaryList`（operation別: rough/research/parts/image board の
finished/total）を design シートの3ブロック構造（blank/conBlank/rest/con/total）
に setValues＋setBorder。

#### 5.3.3 lineart 分析（`makeLineArtAnalysis`, analysis.js:542）

scenario 未登録シーンを construction の単価係数（0.4page/4page/2page…）で
見積もり補完し、シーン別ラインナート集計（MUST/NEED/QUALITY 等の finishing
区分）を manuscript シートに書く。

#### 5.3.4 その他の集計

- `makeMiscAnalysis`: memo（タイトル名）別の concept/misc/outsidework 集計 → analysis!N7〜
- `makeTotalAnalysis`: design/lineart/misc の indigestion/rest/finished/all → N2:T5
- `indigestionAnalysis`: construction 計画との差分 → E3:E9
- `makeWorkSummary`（analysis.js:657）: design/manuscript/construction の
  サマリブロックから週別 rest を読み、
  `WorkSummaryArray(...).writeSummary('timeline')` で週列（列7〜）に
  `mathRound(total)+'H'` を書く（週次スケジュール生成の実体）。
  `exportCalendar(cal)`（CalendarApp イベント生成）は呼び出し元コメントアウト済み=dead。

### 5.4 task analysis（`writeTaskAnalysis`）— Liquid Planner 連携

1. project/setting 初期化 → `makePortfolioData(ssID, re).analysis()` で
   広い正規表現で全シート走査。
2. `makeTaskAnalysis()`（task.js:41）: `DataArray.getTaskData()` でセル色で
   グルーピング → `getTaskAnalysis(color, name)` で
   (color, name, finishedH, restH, progress%, allH) を計算。
3. analysis!U4:Z に書き込み、3行目に `=SUM(...)` 数式。
4. 結果を `Browser.msgBox` で「liquid planner entry」用文字列として表示。
5. `getTaskHash()`（task.js:27）: analysis!U4:Z から `{背景色: タスク名}` の
   対応表を読む。`showCellBackgroundColor()` はアクティブセルの色→タスク名
   を msgBox 表示。

**背景色の役割**: マトリクスのセル背景色 = LP のタスク識別子。同色の作業が
同じ LP タスクに集約される設計。

### 5.5 agenda 生成（`makeAgendaData`, agendaData.js）

- `postWorkData`: `workData.val` が `settingData.allDayList.re` に一致する
  作業を、日別 × group別（all/alone/horizontal/vertical）に振り分け
  （`AgendaData`, agendaData.js:94 → グローバル `agendas`）。
- `principle()`（agendaData.js:27）: `library.deepCopy(principleList)` を
  各作業の name/section/mode/operation タグでマッチング（タグ無指定=全マッチ）
  し、該当 principle を日別に保持。
- `agendaTextListOfVH(day, group, ...)`: vertical は operation×color、
  horizontal は page×color のユニーク組み合わせ集計で「operation 合計min /
  内訳一覧」テキストを生成。
- `getQcList(day)`: その日の section/operation/mode のユニークリスト
  （`library.unique`）。
- 公開経路: `updateSiteOfAgenda/Speech`（SitesApp、廃止）→
  HTML は `MYLIBhtml.taged` で生成し `SitesApp.getPageByUrl(...).setHtmlContent()`
  で上書き（site.js:75-77）。Webアプリ版（`doGet`+index.html）は ScriptDb
  経由で現状死滅。index.html は時間帯タブ＋作業一覧＋
  `qc.paranoiacat.com/qc/process/...` リンク＋タグクラウド＋principle タブ。

### 5.6 reminder（通知）

| 関数 | 方式 | 内容 | 現状 |
|---|---|---|---|
| `scheduleReminder` (reminder.js:114) | メール（`library.sendmail`） | analysis!R3:R5（design/lineart/misc の rest 時間）を読み、1日9時間（`count=9`）で割って残り日数を計算。本文: 「１日9時間作業して、xxxwork is rest xxxtime days / xxxwork rest : xxxtime H」。`reNewWorkStructure` 末尾で自動呼び出し | 設計上は現役（呼出元は壊れている） |
| `workReminder` (reminder.js:9) | メール | 冒頭コメント「abandoned (2014.5.5)」。`ProjectCalendar`（未定義）でカレンダー走査し8日以内リマインダ/3日以内イベントを集約送信 | 死滅 |
| `calendarForSummary` (reminder.js:86) | シート書込 | `CalendarApp.getAllCalendars()` の全イベントを construction!A2:C へ | 不使用系 |
| `publishSummary` (reminder.js:60) | シート書込 | `MYLIBsummary.readPublishData()` から発行実績を construction!K2:P6 へ | 不使用系 |

メール送信は MailApp/GmailApp を直接使わず一切 `library.sendmail` に委託
（宛先設定は library 側依存＝不明）。

### 5.7 週次チャート出力（`putScheduleChartToSummery[Reverse]`）

1. 'chart' シートの空白列削除 → G4:最終行を読む（flag=1 で転置）。
2. `Charts.newDataTable().newBarChart().setStacked()` で積み上げ横棒チャートの
   Blob をグローバル `ImageList` に蓄積（makeSchedule.js:56-68）。
3. `writeChartImage(DocId, "Scheduling")`: summary Doc 内の見出しテキストを
   検索し、その直後の既存画像を削除して新チャート画像を挿入。
Reverse 版がメニュー「putChartToSummery」に登録。

### 5.8 見積ログ（`addEstimateWorkTime`, portfolio.js:114）

- アクティブSSの先頭シート `(2,1,7,1)` を読み、ログSS（`0AsGG...GZHc`）の
  先頭シート2行目に**行挿入**。
- 日付・当日見積（`DataArray.getHour('today', ...)`: F=misc/G=lineart/
  H=concept+scenario）＋ `=SUM(B2:D2)`, `=B2-F2` 等の数式を書く。
- 日次の「見積 vs 実績」を記録する運用。

### 5.9 principle（作業指針）管理（reference.js）

- `makePrinciple()`（reference.js:351）: Google Docs を構造解析。
  共通 Doc（`1QvIrU...`）＋各プロジェクトの `localPrincipleID` の個別 Doc。
  **Heading5=見出し（タグ構文 `(mode)[section]<operation>--alternative--` を
  パース）**、斜体段落=参照URL、Normal=説明、リスト項目=手順。
  `PrincipleData` リストを `principleList` グローバルへ。
- agenda とタグマッチングさせて「その作業の注意書き」として添付する設計。
- `principleViewer()`: UiApp でモードタグ一覧表示（廃止API＝死滅）。
- `makeReferenceMapByIni()`: reference ブックから参照タグ→URL を構築
  （portfolio.js:342 でコメントアウト＝現行未使用）。

### 5.10 シート整備系

| 機能 | 関数 | 内容 |
|---|---|---|
| mode バリデーション | `modeValidation` (validation.js:1) | lineart/color/parts の C4:C に `newDataValidation().requireValueInList`（候補= schedule-init `mode` シート由来、`total==100` のモード一覧） |
| rest 数式整備 | `restCheckFormat` (format.js:92) | 3シートの2行目に `=COUNTBLANK+COUNTIF("partial"/"pending"/"working")`、3行目に `=COUNTIF("*")` |
| ヘッダー生成 | `makeHeader` (format.js:180) | 2行目=rest 未完了数、3行目=rest 合計数式 |
| 週ヘッダー生成 | `formatTimelineTop` (format.js:132) | calendar!A10/A12（空なら `Browser.inputBox` で入力）から週日付ラベルを生成。`dayList` グローバル依存（未定義のため現状エラーになる可能性） |
| モード整合チェック | `modeConsistencyCheck` (tool.js:1) | 3シートのヘッダと mode シートを照合→msgBox |
| lineart ストライプ | `lineartSheetStripe` (tool.js:31) | A列のページ偶奇でゼブラ背景 `setBackgroundRGB(240,230,210)` |
| convert ソート | `convertSheetSort` (convert.js:1) | convert シートを character 別＋レイヤ優先度 `{HAIR,PUPIL,SKIN,CLOTH,RIBBON:1, その他:2, EYELASH,EYE,EYEBROW:3}` でソートし全クリア後に書き戻し（フォント色・ストライプ付き） |
| 余白削除 | `deleteBlanks` 等 (deleteBlank.js) | 空行列削除・範囲クリア。timeline 書込後の後処理等で広く使用 |

---

## 6. 処理フロー詳細

### 6.1 日別タイムライン生成フロー（現役）

```
ユーザーが各シートに時刻帯名を手動入力（morning 等）
        │
        ▼
reNewPortfolio2() ── portfolio()
        │
        ├─ Project: project シート → active プロジェクト一覧
        ├─ SettingData: daylist → 時刻帯マスタ＋正規表現
        ├─ ModeMap: mode シート → section×operation×mode の時間比率
        ├─ GroupMap: group シート → alone/vertical/horizontal 判定
        │
        ├─ makePortfolioData(ssID, allDayList.re)
        │    ├─ concept 系: concept/misc/study/programming + loop + rebuild
        │    │            → WorkDataA[] (weekWorkA)
        │    └─ manuscript 系: parts/color/lineart + rebuild
        │                     → WorkDataC[] (weekWorkC, 背景色付き)
        │
        ├─ makeAgendaData() → agendas[時刻帯]（作業+principle+QCリスト）
        │
        └─ writeDayWork3(時刻帯) → timeline シート
             4行目: estimated total : X H
             5-10行目: カテゴリ別時間（parts/color/concept/outsidework/lineart/scenario）
             11行目〜: 作業明細
```

### 6.2 週次スケジュール生成フロー（設計上）

「スケジュール生成」は自動アルゴリズムではなく、**ユーザーがマトリクスセルに
`week1`…`week9`/`later` を手動入力**し、機械的に展開する方式:

1. `formatTimelineTop('timeline')`: calendar!A10/A12 から週ヘッダー（1行目、
   7列目〜）を生成し `weekDateList['weekN']` を構築。
2. `makeWorkSummary()`: design/manuscript/construction のサマリブロックから
   `(名称(数量), week, rest, operation)` の `WorkSummaryData` リストを作る。
3. `WorkSummaryArray.writeSummary('timeline')`: 週ごと合計を4行目・週列に、
   個別作業を5行目以降に書く。
4. `putScheduleChartToSummeryReverse()`: chart シート → 積み上げチャート画像
   → summary Doc の "Scheduling" 見出し下に配置。

### 6.3 集計パイプラインフロー（設計上）

§5.2 の通り。`reNewWorkStructure` が construction 読み込み → 全シート走査 →
work/design/lineart/misc 分析 → 総括 → reminder メールの一括再計算。

---

## 7. 非機能・運用仕様

### 7.1 実行方式

- **すべて手動実行**。`ScriptApp`（トリガー作成）は不使用、`onOpen` は
  コメントアウト。メニュー表示も `CreateMenu()` の手動実行が必要。
- ※推測: 2014年以前は時間主導トリガーで `workReminder` を定期実行していた
  可能性（コード上の痕跡なし。クラウドコンソール側で作成されていた想定）。
- Web アプリとしてもデプロイされていた（appsscript.json: `webapp:
  access=MYSELF, executeAs=USER_DEPLOYING`、エンドポイント `doGet`）。

### 7.2 タイムゾーン（不統一・要注意）

| 箇所 | 設定 | 問題 |
|---|---|---|
| project1 appsscript.json | America/Los_Angeles | 日本の運用とは不整合と推測（誤設定の可能性） |
| project2 appsscript.json | Asia/Tokyo | 日本運用と一致 |
| `comvTime` (myUtil.js:24) | `Utilities.formatDate(..., "JST", ...)` 固定 | プロジェクトTZと混在 |
| `WorkDataLoop.isActive` (workdata.js:280) | `getUTCDay()`（UTC曜日）と日本語曜日名を照合 | LA時間で実行すると曜日判定がずれる |
| `computeDate` | `new Date(y,m,d)`（ローカルTZ基準） | 夏時間跨ぎでずれるリスク |

### 7.3 セキュリティ

- 外部リソースIDが**コードにハードコード**（SS/Docs/Sites/Cloud SQL）。
- project2 は **Cloud SQL に root/空パスワードでJDBC接続**（data.js:3-7）、
  かつ `modemap = getModemap()`（data.js:62）が**スクリプト読み込み時に
  常時実行**される構造（接続失敗＝全機能停止）。
- メール宛先は外部 `library.sendmail` 内部に依存（こちらも不透明）。

### 7.4 使用 GAS API 一覧

| API | 使用箇所 | 状態 |
|---|---|---|
| SpreadsheetApp | 全面的（読み書き・数式・背景色・DataValidation・行列削除） | 現役 |
| DocumentApp | portfolio/analysis/reference/format/makeSchedule（agenda・summary・principle 文書） | 現役 |
| Charts | makeSchedule.js:56-68（積み上げ棒チャート→Blob→Doc挿入） | 現役経路 |
| Browser | inputBox/msgBox（task/tool/makeSchedule） | 現役 |
| HtmlService | html.js:3,86（Web App テンプレート） | ScriptDb 死滅のため経路として死滅 |
| Utilities | myUtil.js:24-25（formatDate） | 現役 |
| CalendarApp | reminder.js:91（読みのみ。イベント生成は dead） | 不使用系 |
| **SitesApp** | site.js:76,84,126 | **Google廃止（動作不可）** |
| **UiApp** | tool.js:73, reference.js:478 | **Google廃止（動作不可）** |
| **ScriptDb** | myUtil.js, html.js, mode.js | **Google廃止（動作不可）** |
| **Jdbc** | project2/data.js | 接続可否は環境依存（構文もV8非対応） |
| MailApp/GmailApp | 不使用（`library.sendmail` に委託） | 外部依存 |
| ScriptApp（トリガー） | 不使用 | ― |

---

## 8. 現状の稼働状況評価

### 8.1 経路別の判定

前提: すべての経路は外部ライブラリ `library` の存在を必要とする。

| 判定 | 経路 |
|---|---|
| **○ 現役（動く可能性が高い）** | `writeTaskAnalysis`（task analysis）、`showCellBackgroundColor`、`setModeValidation`、`reNewPortfolio2`（timeline 書込まで。agenda の Sites 更新は除く）、`makePrinciple`、`saveLog`、`convertSheetSort`、`deleteBlanks`、`modeConsistencyCheck`、view メニュー系 |
| **△ 一部壊れている** | `makeAgenda`（portfolio 集計は動くが Sites 更新で例外）、`putScheduleChartToSummeryReverse`（summary Doc の ID 取得が `summeryDocId` グローバル依存で未定義の可能性）、`publishSummary`（不使用系だが呼べるかは MYLIBsummary 依存） |
| **✕ エラー確定（未定義シンボル）** | `reNewWorkStructure`（`readScenarioData`）、`restCheckFormat`/`MYAPPtest`（`ProjectSetting`）、`formatTimelineTop`（グローバル `dayList` 未定義）、`calcurateAveragePageCost`（`modeDataArray`/`modeMapArray`）、`makeChartOfScenarioPageComposition`（`InitSetting`/`readScenarioData`/`ScenarioDataArray`）、`workReminder`（`ProjectCalendar`）、`showHtml`（'example.html' 不存在） |
| **✕ 廃止API** | `updateSiteOfAgenda/Speech/setSite`（SitesApp）、`lineartStripeGd`/`principleViewer`（UiApp）、`saveDbAgenda`/`doGet`（ScriptDb）、`modeDbTest`（ScriptDb） |
| **✕ 死項目（メニューに残存するが未定義）** | `scenariosSetPP`, `todoListUpdate`, `testDeleteSummry`, `scenarioNewEntry`, `applyScenarioDataToLineartSheet`, `createProject`, `applyWeek` |
| **✕ 明示的放棄** | `workReminder`, `TodoList`/`DocList`（todolist.js「abandoned 2014.5.5」）、analysis 系統の一部（`analysis.js:4-8`） |
| **✕ project2 全体** | `for each` 旧構文（V8 で構文エラー）＋JDBC 空パスワード＋ロード時即接続。現環境では実行不能の可能性が高い |

### 8.2 既知のバグ・不整合一覧

| # | 内容 | 箇所 |
|---|---|---|
| 1 | `ModeMap.prototype.all` の `thi.list3` がタイポ（`this`）で常に例外 | mode.js:173 |
| 2 | `WorkDataA` コンストラクタが `info==""` で TypeError（`obj` 未定義） | workdata.js:94-96 |
| 3 | `ReferenceArray.textById/urlById` が `urlId` を参照するが実体は `url` | reference.js:250-260 |
| 4 | `spliceItemInArray` の splice ループで要素欠損の可能性（`i` も暗黙グローバル） | myUtil.js:46-53 |
| 5 | `todayTotalTime` が `settingData.getTodayDayListRe()` を呼ぶがメソッド非存在 | workdata.js:325 |
| 6 | `agendaData.js` の `backgroundTable` が即 `return null`（到達不能） | agendaData.js:147 |
| 7 | menu.js:122,128 に浮遊する `convertSheetSort` 式文（無害だがゴミ） | menu.js:122,128 |
| 8 | 暗黙グローバル変数多数（`project`, `settingData`, `weekWorkA/C`, `dic`, `agendas`, `dayList`, `weekDateList`, `ImageList`, `modemap` 等）。非 strict で動いているが脆弱 | 各所 |
| 9 | 時間単位の3系統并存（0.1h / 分 / 分→h） | §4.4.5 |
| 10 | タイムゾーンの混在（LA設定 vs JST固定 vs UTC曜日） | §7.2 |
| 11 | `project` シートの原稿 ssID（旧形式）と現行原稿ブックID の不一致 | §4.1 |
| 12 | project2 の `summarize` は `line`/`effect`/`erotic_effect` 列を lineart シートが持たないため、実際の集計内訳は SQL マスタ側より小さく効く設計 | project2/data.js:85 |
| 13 | project1 `analysis` シートと project2 `analysis` シートは同名別物（concept 内の集計ハブ vs 原稿内の2列シート）。`scheduleReminder` はアクティブSSの analysis を読むため、原稿側で実行すると型不整合の可能性 | reminder.js:115 |
| 14 | concept.xlsx の集計数式の範囲参照が `{}` に変換ロス（Google→xlsx エクスポート由来と推測） | 各シート3行目 |

---

## 9. 移植・再実装方針の検討

### 9.1 要件の再定義（このツールがやりたかったこと）

コードから逆算した本質的な要件:

1. **「今やること」の集約**: 複数ブックに散らばる作業予定（時刻帯タグ）を
   1枚の timeline に集約表示する。
2. **残作業の見える化**: 工程マトリクスの未着手セルから、モード別の係数で
   残り工数を見積もり、design/lineart/misc 別に集計する。
3. **締切までの日数換算通知**: 残工数÷1日9時間で残り日数をメール通知する。
4. **外部PMツールとの連携**: LP 用タスク登録文字列の生成（色=タスク）。
5. **作業指針の配布**: principle ドキュメントをタグマッチングで agenda に添付。
6. **日次の見積ログ**: 見積 vs 実績の記録。

### 9.2 現役機能の抽出（推奨スコープ）

> **方針（2026-09-22 確定）**: 本プロジェクトの復元ターゲットは **project2**
> （modemap マスタ＋`writeAnalytics` パイプライン）とし、project1 は
> モード体系の理解のための参考资料とする。modemap の復元成果物は
> `restoration/` と `docs/MODEMAP_RESTORATION.md` 参照。

再実装する価値があると考えられる範囲（project1 側。参考）:

- **P0（中核）**: シート走査（WorkDataA/C）→ `agendas` → timeline 書込 →
  analysis 集計 → `scheduleReminder` メール。§6.1/§6.3 のパイプライン。
- **P1（有用）**: task analysis（LP文字列）、mode バリデーション、
  rest 数式整備、lineart ストライプ、convert ソート、週次チャート。
- **P2（再設計が必要）**: agenda 公開（Sites の代替として Web App を
  新規設計）、見積ログ、principle マッチング。
- **除外（捨てる）**: Sites/UiApp/ScriptDb 依存経路、死メニュー項目、
  workReminder/calendarForSummary/publishSummary 等の不使用系、project2 の
  JDBC 方式（§9.3 参照）。

### 9.3 技術的置き換え対応表

| 現状 | 再実装時の推奨 | 備考 |
|---|---|---|
| 外部ライブラリ `library` | **自前実装に置換**（getSheet/cellReverse/unique/sendmail 等は素朴に書ける） | 残る最大のブロッカー。ライブラリ本体も clasp で DL する選択肢はあるが、自前化を推奨 |
| 外部ライブラリ MYLIBhtml/MYLIBarray/MYLIBsummary | 自前化 or 削除（使用箇所は Sites 系のみで再設計なら不要） | |
| SitesApp 公開 | Web App（`HtmlService` 現行API）またはドキュメント出力に置換 | access 範囲は再検討 |
| ScriptDb | `PropertiesService` またはスプレッドシートへの直接保存 | |
| UiApp ダイアログ | `HtmlService` のダイアログ/サイドバー、あるいは単純なメニュー実行に置換 | |
| `Browser.inputBox` | そのまま or HtmlService フォーム | |
| project2 の Cloud SQL modemap | **スプレッドシート化して吸収**（schedule-init `mode` シートと統合） | JDBC+空パスワードは廃止。project2 の `writeAnalytics` は project1 の ModeMap 集計に統合可能（後継設計と推測されるため） |
| `for each` 構文 | 標準の `for...of` | V8 必須 |
| ハードコードID群 | 設定シート or `PropertiesService` 化 | 外部ブックは存在確認が前提 |
| タイムゾーン | **Asia/Tokyo に統一**（`getUTCDay` 使用箇所をローカル曜日に修正） | |
| 時間単位 | 分 or 0.1h のどちらかに統一 | |
| 暗黙グローバル | モジュール化・引数渡しに整理 | |
| `onOpen` コメントアウト | 復活させてメニューを自動表示 | |
| トリガーなし | 時間主導トリガーで reminder 定期実行を検討 | `ScriptApp.newTrigger` |

### 9.4 課題・リスク

1. **外部ブックの所在**: schedule-init / log / reference ブックと外部
   `library` はローカルに非所持。現存するか、内容を再構成できるか。
2. **スナップショットと現行の乖離**: xlsx はエクスポート時点のスナップショット。
   現行の Google 側ブック（特に project シート・mode シートのマスタ値）が正。
3. **運用実態の不明**: 2014年の放棄宣言以降、実際にどのメニューが使われて
   いたかはコードだけでは判別不能。**利用者へのヒアリングが前提**。
4. project2 の Cloud SQL（`project-211906:...:sh1-sql`）が現存するかは未確認。
   modemap データの移行先が必要。
5. `qc.paranoiacat.com`（QCツール）の現状。リンク生成の価値は依存。

---

## 10. 未解決事項・推測の一覧

| # | 項目 | 状態 |
|---|---|---|
| 1 | 外部ライブラリ `library`（`1EvLyg...`）の中身 | 未取得。project1 全経路の前提 |
| 2 | 未定義シンボル群（`readScenarioData`/`ScenarioData`/`ProjectCalendar` 等）が `library` 由来か削除済みコードか | 推測のみ。`library` の DL で判明する可能性 |
| 3 | `workReminder` の定期実行トリガーがクラウド側に存在していたか | 推測のみ（痕跡なし） |
| 4 | project シートの原稿 ssID（旧形式）と現行ID の不一致理由 | ブック再作成 or スナップショット古さ |
| 5 | 実運用で使っていた機能の範囲 | 利用者ヒアリングが必要 |
| 6 | concept.xlsx の数式 `{}` 化がエクスポートロスか | 推測（lineart/parts/manuscript では正常範囲が残存する事象との不整合） |
| 7 | project1 の TZ が America/Los_Angeles な理由 | 誤設定と推測 |
| 8 | project2 のライブラリ参照 v72（開発モード）の経緯 | 死に依存。かつての呼出名残と推測 |
| 9 | 外部ブック4冊＋Docs2本＋Sites の現存性 | 未確認 |

---

## 付録A. ファイル別インデックス（project1）

| ファイル | 役割 | 規模 |
|---|---|---|
| workdata.js | 作業データオブジェクト（WorkDataA/C/Loop, DataArray, TimelineArray） | 888行 |
| analysis.js | 集計パイプライン（reNewWorkStructure, make*Analysis, makeWorkSummary） | 832行 |
| reference.js | principle/参照資料のパース＆マッチング | 483行 |
| portfolio.js | メインエンジン（portfolio, makePortfolioData, ログ, agenda書込） | 381行 |
| menu.js | メニュー定義＋ビュー切替 | 175行 |
| makeSchedule.js | 週ヘッダー・チャート生成・日付入力 | 179行 |
| agendaData.js | agenda 集計＋principle マッチング | 159行 |
| mode.js | ModeMap（mode シート→時間比率） | 206行 |
| format.js | MYAPP 名前空間・数式整備・Doc 整形・週ヘッダー | 207行 |
| reminder.js | scheduleReminder メール 等 | 141行 |
| setting.js | Project / SettingData | 166行 |
| site.js | Sites 公開（廃止） | 128行 |
| task.js | task analysis / LP 連携 | 104行 |
| todolist.js | TODO 収集（放棄） | 115行 |
| tool.js | 整合チェック・ストライプ | 108行 |
| html.js + index.html | Web App（ScriptDb 経路＝死滅） | 94+146行 |
| myUtil.js | 汎用ユーティリティ | 108行 |
| validation.js | mode バリデーション | 51行 |
| convert.js | convert ソート | 92行 |
| deleteBlank.js | 余白削除 | 58行 |
| group.js | GroupMap | 31行 |
| appsscript.json | マニフェスト（V8, LA TZ, webapp, 4ライブラリ） | ― |

## 付録B. 付録: project2 関数一覧

| 関数 | 役割 |
|---|---|
| `createMenu` / `menuData` | "schedule" メニュー（task analysis → `writeAnalytics`） |
| `getObj` / `getDic` / `getDicArrayByCells` / `cellReverse` | シート→オブジェクト変換（project1 の library と重複実装） |
| `getModemapArray` / `getModemap` | Cloud SQL から mode 別時間マスタ取得（**グローバル実行**） |
| `getWorkTime` / `summarize` | 空白セル（未着手）の残時間集計 → 5系統に集約 |
| `getWorkAnalytics` / `constructAnalytics` / `writeAnalytics` | lineart を plot 別に集計 → analysis!A3:B へ書込 |
