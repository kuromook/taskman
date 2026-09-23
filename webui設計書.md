# WebUI設計書 — タスク管理ダッシュボード（静的HTML・閲覧専用）

- 作成日: 2026-09-23
- ステータス: **実装済み**（2026-09-23、Claude。ブラウザで3タブとも動作確認済み。
  実装時の差分は末尾「実装メモ」参照）
- 由来: `taskman analyze`（CLI）の出力をブラウザで見られるダッシュボードにする
- 方針: **サーバー常駐不要の静的HTML生成。入力・編集は対象外（閲覧専用）。
  将来Flask化して編集機能を足せる構造にしておく。**
  （サーバー方式 vs 静的HTML方式は利用者確認済み。静的HTMLを選択。理由:
  既存taskmanの「openpyxlのみ・最小構成」という方針を維持でき、
  サーバー起動・ポート管理の手間がなく、ファイルを開くだけで完結するため）

---

## 1. 目的・背景

現状 `python -m taskman analyze` はテキスト表のみ。plot×5群の数字を
一覧するにはCLI出力を読むしかなく、全体の進捗感や、カテゴリ横断での
偏りが直感的にわかりにくい。管理画面（ダッシュボード）としてブラウザで
可視化し、下記3つの見方を切り替えられるようにする。

- 全タスクを俯瞰する進捗（plotごとの進み具合）
- 各plotごとのタスク内容（現CLI出力の可視化版）
- 各タスク（5群カテゴリ）ごとの内容（plot横断での偏り）

## 2. スコープ

### 2.1 今回やること

- `python -m taskman dashboard <input.xlsx> [-o dashboard.html]` で
  単一HTMLファイルを生成するコマンドを追加
- 3タブのダッシュボード（詳細は §6）
- タブ切替・グラフ描画はすべてクライアントサイドJS（生成後は再計算・
  再読込なし。ブラウザで `dashboard.html` を開くだけで完結）

### 2.2 今回やらないこと（将来拡張）

| 項目 | 将来対応の想定 |
|---|---|
| 入力・編集（マスタCSV編集、セル状態変更等） | Flask化してPOSTを受ける |
| xlsxへの書き戻し | 同上 |
| サーバー常駐・リアルタイム更新 | Flask化し `/api/data` で都度再計算 |
| 認証・複数ユーザー | 個人利用前提のため対象外 |
| xlsxが更新された場合の自動反映 | 今回は都度 `dashboard` コマンドを再実行して再生成する運用 |

## 3. 全体構成

```
taskman/
├── analyze.py               # 既存 + total_time() 追加
├── master.py                 # 既存（変更なし）
├── sheet.py                   # 既存（変更なし）
├── cli.py                       # 既存 + dashboard サブコマンド追加
├── view_data.py               # NEW: 集計結果 → 画面用データ構造（純粋関数）
├── dashboard.py               # NEW: HTML生成（string.Templateで埋め込み）
└── templates/
    └── dashboard.html.tmpl    # NEW: HTMLひな形（CSS/JS/Chart.js込み）
```

依存追加: **なし**（Python標準ライブラリのみ。既存の openpyxl 以外は増やさない）。
チャート描画はブラウザ側で Chart.js（CDN参照）を使用 — Pythonの依存には
含まれない。

## 4. アーキテクチャ

```
$ python -m taskman dashboard spreadsheets/manuscript.xlsx -o dashboard.html

  1. master.load_master()        # 既存
  2. sheet.load_sheet()          # 既存
  3. analyze.analyze()   → remaining（既存）
  4. analyze.total_time() → full（NEW）
  5. view_data.build_dashboard_data(...) → dict（NEW、純粋関数、I/Oなし）
  6. dashboard.render(data, template_path) → HTML文字列（NEW）
  7. -o で指定したパスにファイル書き出し

$ open dashboard.html   # ブラウザで開く。以降は完全にクライアントサイド完結
```

コア（analyze.py / master.py / sheet.py）はI/O分離の純粋関数という既存方針
を維持。`view_data.py` も同様に純粋関数とし、Flask化する際は同じ関数を
`/api/data` のレスポンス生成にそのまま使い回せるようにする。

## 5. データ設計

### 5.1 analyze.py 拡張: `total_time()`

進捗％を出すには「残作業時間」に加え「満額の作業時間（そのplotが
0%着手のときの時間）」が要る。既存 `analyze()` は空白セルのみ加算するが、
`total_time()` は着手状態を問わず全対象セルを加算する。ロジックはほぼ
同一のため、内部ヘルパーを共通化する。

```python
def _accumulate(rows, categories, weights, *, only_blank: bool):
    """analyze() と total_time() の共通実装。
    only_blank=True  : 空白セルのみ加算（既存 analyze() の挙動）
    only_blank=False : 状態を問わず全対象セルを加算（total_time()）
    """
    result = {}
    skipped = {}
    for plot in unique_plots(rows):
        plot_rows = [r for r in rows if r.get("plot") == plot]
        acc = {cat: 0 for cat in categories}
        for row in plot_rows:
            mode_weights = weights.get(row.get("mode"))
            if mode_weights is None:
                key = (plot, row.get("mode"))
                skipped[key] = skipped.get(key, 0) + 1
                continue
            for cat in categories:
                if cat not in mode_weights:
                    continue
                if not only_blank or row.get(cat) in (None, ""):
                    acc[cat] += mode_weights[cat]
        result[plot] = summarize(acc)
    warnings = [f"plot '{p}': mode '{m}' がマスタに未定義の行を{c}件スキップ"
                for (p, m), c in skipped.items()]
    return result, warnings


def analyze(rows, categories, weights):
    return _accumulate(rows, categories, weights, only_blank=True)


def total_time(rows, categories, weights):
    result, _ = _accumulate(rows, categories, weights, only_blank=False)
    return result  # total側はwarningsをanalyze()と二重報告しない
```

（既存 `analyze()` の外部インタフェース・戻り値は変更しない。内部実装の
リファクタのみ。既存のCLI/テストがあれば影響しないことを実装時に確認）

### 5.2 view_data.py: `build_dashboard_data()`

```python
def build_dashboard_data(rows, categories, weights, *, input_file: str) -> dict:
    """画面表示用のJSONシリアライズ可能な dict を返す（純粋関数）。"""
```

出力スキーマ:

```jsonc
{
  "generated_at": "2026-09-23T10:00:00",
  "input_file": "manuscript.xlsx",
  "groups": ["sketch", "lineart", "object", "illustrate", "effect"],
  "plots": ["海難事故救出", "砕月暴走", "..."],   // 出現順
  "summary": {
    "total_remaining_h": 60.3,
    "total_full_h": 123.4,
    "progress_pct": 51.1                        // 1 - remaining/full
  },
  "overview": [                                   // タブ1用
    {"plot": "海難事故救出", "remaining_h": 4.9, "total_h": 10.2, "progress_pct": 52.0},
    "..."
  ],
  "by_plot": {                                    // タブ2用
    "海難事故救出": [
      {"group": "sketch", "remaining_h": 0.0, "total_h": 1.0, "progress_pct": 100.0},
      {"group": "object", "remaining_h": 1.9, "total_h": 2.5, "progress_pct": 24.0},
      "..."
    ]
  },
  "by_group": {                                   // タブ3用
    "object": [
      {"plot": "海難事故救出", "remaining_h": 1.9, "share_pct": 9.1},
      "..."
    ]
  },
  "warnings": ["plot 'xxx': mode 'yyy' がマスタに未定義の行を2件スキップ"]
}
```

- `progress_pct` は「時間ベース」（残時間 / 満額時間）で統一する
  （群ごとの重み付けはしない。カテゴリ数ベースにはしない）。
- `share_pct`（タブ3）は「そのカテゴリの全plot合計に対する、当該plotの
  残時間の割合」。
- `total_h` が 0（＝そのmode/カテゴリ組で満額も0）の場合、
  `progress_pct` は 100.0 とする（ゼロ除算回避。作業対象が無ければ
  進捗100%扱い）。

## 6. 画面設計（3タブ、円グラフ方式）

タブ切替はページ内のJSのみで行う（別ページに遷移しない）。

利用者の希望により、横棒グラフではなく**円グラフ／サイズ可変ドーナツ**を
採用する。ただし dataviz スキルの指針上、円・ドーナツは「近い値の比較」や
「plot横断の精密な大小比較」には不向き（`anti-patterns.md`: "A donut/pie for
comparing close values" → 代わりにbar/数値を推奨）なため、**すべてのタブで
残時間・割合の数値を直接ラベル or 表として必ず併記**し、円のサイズ・角度は
「ひと目の印象」を掴む用途に限定する（正確な比較は数値側で担保する）。

### タブ1: 全タスクを俯瞰する進捗 — サイズ可変ドーナツのグリッド

- plotごとに1つの**ドーナツ（進捗リング）**を並べる（グリッドレイアウト）
- リングの**塗り具合 = 進捗％**（進捗％分だけ弧を塗る。トラックは同ランプの
  薄い色。`marks-and-anatomy.md`のMeter仕様に準拠）
- リングの**外径（サイズ）= 残時間の多さ**（§6.1のサイズスケール参照）。
  残時間が多いplotほど大きく、少ないplotほど小さく描画され、
  「どのplotがまだ重いか」がひと目でわかる
- 各リングの直下に **plot名・残時間(h)・進捗％** を直接テキスト表示
  （色や大きさだけに頼らない。dataviz skillの必須事項）
- 上部サマリ: 全体残時間合計・全体進捗％（`summary`）
- 既定ソート: 出現順。ボタンで「残時間が多い順」にも切替可能
- テーブルビューへの切替リンクも用意する（アクセシビリティ）

### タブ2: 各plotごとのタスク内容（現CLI出力の可視化版）— 円グラフ

- plot選択（左サイドリスト or ドロップダウン、出現順）
- 選択plotの5群（sketch/lineart/object/illustrate/effect）を**1つの円グラフ**
  で表示（part-to-whole、5segmentsなので dataviz skillの「donut/pieは
  ≤6segmentsまで」の目安内）
- 色は §6.3 の固定カテゴリカル色（sketch/lineart/object/illustrate/effect
  の順で固定、系列切替では色を変えない）
- 各スライスに直接ラベル（群名＋残時間h）。5枚全部ラベルすると密集するため、
  スライスが小さい場合はラベルを円の外に引き出し線で出すか、凡例＋数値表に
  落とす（`marks-and-anatomy.md`の「ラベルが収まらない場合」規則に準拠）
- 数値表（CLIのテキスト表と同じ内容: group / remaining_h / total_h）も併記
- 円のサイズはこのタブでは固定（1つのplotしか同時表示しないため、
  サイズ比較の意味がなく固定サイズで十分）

### タブ3: 各タスク（5群カテゴリ）ごとの内容 — 円グラフ

- カテゴリ（5群）選択タブ内タブ
- 選択カテゴリについて、**plotごとの残時間の内訳を1つの円グラフ**で表示
  （part-to-whole: そのカテゴリの全plot合計に対する各plotのシェア）
- 現状plot数は7で dataviz skillの目安上限（6segments）に
  近い。plot数が今後8以上に増えた場合は、小さいplotを「その他」に
  まとめるか、円グラフではなく横棒グラフにフォールバックする
  （§12未決定事項に記載）
- 各スライスに直接ラベル（plot名＋割合%＋残時間h）。密集時はタブ2と同じ
  ルールで引き出し線 or 数値表に落とす
- 円のサイズは固定（タブ2と同じ理由）

### 6.1 サイズ可変ドーナツのスケール式（タブ1）

**面積知覚に基づき、半径は残時間の平方根（sqrt）でスケールする**
（線形スケールだと「25倍の残時間」が「25倍の半径＝625倍の面積」に
見えてしまい誇張されすぎる。対数(log)は逆に圧縮しすぎて「1時間も25時間も
大差ないサイズ」に見えてしまい、"ひと目でイメージ"という目的に反する。
sqrtは面積が値に比例する、この用途の標準的な手法）。

```js
// domainMax: 「大きいplotの目安上限」。利用者ヒアリングより30h固定
//            （plotが大きくなりすぎたら分割される運用のため、実測最大値では
//            なく固定値を使う。→ 複数回の生成間でサイズの意味が変わらない）
const DOMAIN_MAX_H = 30;
const MIN_RADIUS = 28;  // px。5segmentsの凡例が最低限読める最小サイズ
const MAX_RADIUS = 90;  // px。グリッドに収まる上限

function ringRadius(remainingH) {
  const v = Math.min(Math.max(remainingH, 0), DOMAIN_MAX_H);
  const t = Math.sqrt(v / DOMAIN_MAX_H);           // 0..1、面積比例
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * t;
}
```

具体例（このスケール式での見え方）:

| 残時間 | 半径 | 備考 |
|---|---|---|
| 0h | 28px（MIN） | 完了plot。潰れて見えなくなることはない |
| 1h | 39px | 利用者が懸念した「小さすぎて見えない」ケース。
  MIN_RADIUSのフロアとsqrtにより十分視認できるサイズを確保 |
| 8h | 61px | |
| 25h | 85px | |
| 30h以上 | 90px（MAX） | 上限でクリップ（想定上限を超える巨大plotがあっても
  レイアウトが壊れない） |

- 1h→39px、25h→85pxで半径比は約2.2倍（面積比は約4.7倍）。実際の値の差
  （25倍）よりずっと穏やかだが、「どちらが重いか」は一目で判別でき、
  かつ1hのリングも潰れず情報（進捗リング・ラベル）を保持できる、という
  バランス点。
- `DOMAIN_MAX_H`（30h）は実測最大値ではなく固定値にしている。plotごとの
  実データ最大値で正規化すると、生成のたびに「同じ25hのplotでも隣に
  40hのplotがあるかないかでサイズが変わる」ことになり、複数回の
  ダッシュボード生成間でサイズの意味が一貫しなくなるため（実測分布が
  今後の運用で変わっても、絶対的な物差しとして固定するのが狙い）。

### 6.2 スライス角度の最小クリップ（タブ2・3）

タブ2（plotの5群内訳）・タブ3（カテゴリのplot横断内訳）は、群/plot間で
値の差が大きいと、小さい方のスライスが数度以下の細い破片になり、
色の判別もラベル配置もできなくなる。§6.1のリング半径と同じ考え方で、
**0より大きいが一定角度未満のスライスは最小角度まで底上げ**し、
残りのスライスから按分で差し引く（合計360°は維持）。

```js
const MIN_SLICE_DEG = 10; // これ未満は視認・ラベル配置ができないため底上げ

function clippedSliceAngles(values) {
  // values: number[]（>=0）。0のものはそのまま0°（非表示）で、
  // クリップの対象にしない（「存在しない」と「小さい」は区別する）。
  const total = values.reduce((a, b) => a + b, 0);
  if (total <= 0) return values.map(() => 0);

  const rawAngles = values.map(v => (v / total) * 360);
  const bumped = rawAngles.map((a, i) => values[i] > 0 && a < MIN_SLICE_DEG);
  const bumpedSum = rawAngles.reduce((s, a, i) => s + (bumped[i] ? MIN_SLICE_DEG : 0), 0);
  const restRawSum = rawAngles.reduce((s, a, i) => s + (bumped[i] ? 0 : a), 0);
  const restBudget = 360 - bumpedSum;

  return rawAngles.map((a, i) => {
    if (bumped[i]) return MIN_SLICE_DEG;
    if (restRawSum <= 0) return a;           // 全スライスがbumped対象など極端なケース
    return (a / restRawSum) * restBudget;
  });
}
```

- 値が正確に **0** の群/plotはスライス自体を作らない（0°のまま＝非表示）。
  クリップ対象は「0より大きいが小さすぎる」ものだけ（「存在しない」と
  「小さい」を混同しない）。
- タブ2は最大5スライス、タブ3は現状最大7スライスで、
  `MIN_SLICE_DEG=10°` としても底上げ合計は最大70°（7×10°）で
  360°に対して十分余裕があり、按分計算が破綻するケースはない。
- **底上げは見た目の可読性のためだけの処理であり、実際の比率を変えて
  しまう**（例: 実際は全体の1%しかない群が、見た目上は約3%相当の
  スライスに見える）。§6の方針どおり、スライスには必ず**実数値
  （残時間h・実際の割合%）を直接ラベル表示**し、見た目の角度と数値が
  食い違っても実数値の方が正である、と迷わずわかるようにする
  （dataviz skillの「サイズ・色だけに頼らず、常に数値へ到達できるように
  する」という原則に対応）。
- `MIN_SLICE_DEG`（10°）は§6.1の他の定数と同様、実装後の見た目次第で
  調整する前提の仮値とする（§12）。

### 6.3 カテゴリカル色（タブ2: 5segments固定パレット）

dataviz skillの検証済みデフォルトパレットからスロット1〜5を使用
（sketch→lineart→object→illustrate→effectの順で固定、系列の入れ替えなし）。

| 群 | 役割 | 色（light） | 色（dark） |
|---|---|---|---|
| sketch | slot1 blue | `#2a78d6` | `#3987e5` |
| lineart | slot2 orange | `#eb6834` | `#d95926` |
| object | slot3 aqua | `#1baf7a` | `#199e70` |
| illustrate | slot4 yellow | `#eda100` | `#c98500` |
| effect | slot5 magenta | `#e87ba4` | `#d55181` |

円グラフは最後のスライスと最初のスライスが隣接する（輪が閉じる）ため、
通常のスタック/バー用の「隣接ペア検証」だけでは不十分と判断し、
`scripts/validate_palette.js` で**この閉じたリングの5ペア全部**
（sketch-lineart, lineart-object, object-illustrate, illustrate-effect,
**effect-sketch（輪の継ぎ目）**）を個別に検証済み:

- light/dark とも全ペアで CVD分離・正常視野floorともにPASS
- lightモードのみ、aqua/yellow/magentaの3色がサーフェス比3:1未満で
  WARN（"relief required"）→ **直接ラベル必須**（§6の方針どおりスライスに
  直接ラベルを出すため、この要件はもともと満たす設計）

## 7. HTML生成の実装方式

- `templates/dashboard.html.tmpl` は完成品のHTML（CSS・Chart.js読み込み・
  タブ切替JS込み）に、データ埋め込み用のプレースホルダ
  `__DASHBOARD_DATA_JSON__` を1箇所だけ持たせる。
- `dashboard.py` は `importlib.resources` でテンプレートを読み込み、
  `string.Template`（標準ライブラリ、新規依存なし）でプレースホルダを
  `json.dumps(data, ensure_ascii=False)` に置換する。
  ※ Jinja2 等のテンプレートエンジンは使わない（依存を増やさない方針）。
- チャートは Chart.js を **CDN参照**で読み込む（`<script src="https://cdn.jsdelivr.net/npm/chart.js">`）。
  オフライン環境で開く場合はグラフが表示されない点に注意
  （§12 未決定事項で確認）。
- **タブ1のサイズ可変ドーナツの実装方法**: Chart.jsの `doughnut` タイプ自体に
  「半径を値でスケールする」機能はないため、plotごとに**別々の
  `<canvas>`（別Chartインスタンス）**をグリッドに並べ、各canvasを内包する
  コンテナ要素の `width`/`height` を `ringRadius(remainingH)*2`（§6.1の式）
  で個別に設定する。Chart.jsはコンテナのサイズいっぱいにドーナツを
  描画するため、コンテナサイズ＝見た目のリング直径になる。カスタム
  canvas描画は不要、Chart.js標準機能の範囲で実現できる。

## 8. CLIコマンド仕様

```
python -m taskman dashboard <input.xlsx> [--sheet lineart] [--master restoration/modemap.csv] [-o dashboard.html]
```

| 引数/オプション | 既定値 | 説明 |
|---|---|---|
| `input.xlsx`（必須） | ― | 入力ブック |
| `--sheet` | `lineart` | 対象シート名 |
| `--master` | `restoration/modemap.csv` | 重みマスタCSV |
| `-o` / `--output` | `dashboard.html` | 出力HTMLファイルパス |

終了コード・エラー処理は既存 `analyze` サブコマンドと同一方針
（ファイル不存在・フォーマット不正 → 1＋stderr、正常終了 → 0）。

## 9. 実装手順

1. `analyze.py`: `_accumulate()` に共通化しつつ `total_time()` 追加
   （既存 `analyze()` の戻り値・挙動が変わらないことを確認）
2. `view_data.py`: `build_dashboard_data()`
3. `templates/dashboard.html.tmpl`: HTML/CSS枠＋タブUI＋Chart.js CDN読込
4. テンプレ内 `<script>`: タブ切替＋3種チャート描画（Chart.js）
5. `dashboard.py`: `render()`（string.Template置換）
6. `cli.py`: `dashboard` サブコマンド追加
7. 動作確認: `spreadsheets/manuscript.xlsx` で生成し、ブラウザで3タブとも
   表示・数値を確認（タブ2の数値が `analyze` コマンドの出力と一致すること）

## 10. 検証計画（テストコードは書かない方針、既存踏襲）

- 生成した `dashboard.html` をブラウザで開き、3タブとも表示されることを
  目視確認
- タブ2の残時間の数値が `python -m taskman analyze` の出力と一致
- warningがある場合に画面のどこかに表示されることを確認
- xlsx未更新のまま複数回生成しても同じ内容が出ることを確認（再現性）

## 11. 将来拡張への備え（設計上の決定事項）

| 決定 | 理由 |
|---|---|
| `view_data.py` はI/O完全分離の純粋関数 | Flask化時に `/api/data` へそのまま転用できる |
| HTML/CSS/JSは1テンプレートに集約 | Flask化時もテンプレートエンジンをJinja2に
  差し替えるだけで、タブUI・チャート描画JSはほぼ無改修で流用できる |
| データはHTMLに1回埋め込み、以降クライアント完結 | Flask化時は
  埋め込みJSONを `fetch('/api/data')` に差し替えるだけで済む構造にする |

## 12. 未決定事項（レビューで確認したい点）

1. 進捗％の定義（時間ベース: 残時間/満額時間）で問題ないか
2. Chart.js は CDN参照（オフラインでは非表示）でよいか、それとも
   完全オフライン動作のためにローカル同梱（JSファイルを`static/`に置く）
   にするか
3. warningsの表示場所（画面上部バナー？ページ下部の別セクション？）
4. concept側ブック（開始行が異なる）への対応は今回のスコープ外のままでよいか
   （`--sheet`はあるが `--data-start-row` 未実装のため、現状は対応不可）
5. §6.1 のサイズスケール定数（`DOMAIN_MAX_H=30h`, `MIN_RADIUS=28px`,
   `MAX_RADIUS=90px`）は仮決めの値。実際にグリッド表示したときの見え方
   次第で調整する前提でよいか（実装後、実データでの見た目を見てから
   微調整する想定）
6. タブ3の円グラフはplot数7が実質的な上限に近い（dataviz skillの目安
   ≤6segments）。plot数が今後8以上に増えた場合の対応（「その他」に
   まとめる／横棒グラフにフォールバック）は今回未実装のままでよいか、
   閾値判定だけ先に入れておくか

## 実装メモ（2026-09-23、Claude）

未決定事項（§12）はレビュー確認を待たず、以下の通り実装時に判断した
（いずれも後から変更しやすい局所的な選択のため）:

1. 進捗％定義: 設計どおり時間ベースで実装
2. Chart.js: CDN参照のまま（jsdelivr、v4.4.4を固定）。オフラインでは
   グラフ非表示になる点は変更なし
3. warningsの表示場所: ページ上部、`<details>`（折りたたみ）バナー。
   件数だけ常時見え、クリックで内訳展開
4. conceptブック対応: 今回スコープ外のまま（未実装）
5. サイズ定数（DOMAIN_MAX_H/MIN_RADIUS/MAX_RADIUS/MIN_SLICE_DEG）:
   設計書の仮値のまま実装。実データで表示確認済み（§9参照）、体感で
   違和感はなかったため今回は調整なし
6. タブ3の8件超フォールバック: `BYGROUP_MAX_SLICES=8`で実装（8件目以降を
   残時間の小さい順に「その他」へ集約）。現状plot数7のため未発動だが、
   ロジックは実装済み

**設計からの実装上の変更点（1点）**: §7で「string.Templateでプレースホルダ
置換」としていたが、実装ではJS側でテンプレートリテラル（`` `${x}` ``）を
多用しており、string.Templateは`$`を全文スキャンして展開するため衝突する
危険があった。そのため**素朴な文字列置換**（`str.replace()`、一意な
プレースホルダ`__DASHBOARD_DATA_JSON__`）に変更。標準ライブラリのみで
完結する点・依存追加なしという方針は変わらない。

**動作確認**: `python -m taskman dashboard spreadsheets/manuscript.xlsx -o
dashboard.html` で生成し、claude-in-chromeでブラウザ表示を確認（file://は
拡張機能の制約で開けなかったため、`python -m http.server`で一時的に配信）。
3タブとも表示・データ内容とも正常（タブ1のリングサイズが残時間に応じて
可視的に変化、タブ2/3の円グラフとクリップ処理、警告バナーの折りたたみ、
色（light/darkとも検証済みパレット）を目視確認）。生成物 `dashboard.html`
は再生成可能なビルド出力のため `.gitignore` に追加（コミット対象外）。
