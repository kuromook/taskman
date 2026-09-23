# modemap DB 復元仕様

- 作成日: 2026-09-22
- 結論: **スキーマ（テーブル構成・カラム名・JOIN 関係）はコードに SQL 全文が
  残っているためほぼ確実に復元できる。行（モード名）は xlsx 実データから
  高確度で復元できる。値（重み）は失われたが、実測キャリブレーションで
  再生成する運用を想定する。**

---

## 1. 復元の根拠となるコード証拠

### 1.1 SQL 全文（project2/data.js:10-18）— 最重要証拠

```sql
SELECT mode, sketch,head, body, cloth, item, background, base, shadow, erotic,
       line, effect, erotic_effect, onomatopeia, front, back, dialog, mood
  FROM modemap.mode
  RIGHT JOIN sketch     ON modemap.mode.id = modemap.sketch.mode_id
  RIGHT JOIN lineart    ON modemap.mode.id = modemap.lineart.mode_id
  RIGHT JOIN object     ON modemap.mode.id = modemap.object.mode_id
  RIGHT JOIN illustrate ON modemap.mode.id = modemap.illustrate.mode_id
  RIGHT JOIN effect     ON modemap.mode.id = modemap.effect.mode_id;
```

これだけで以下が確定する:

- **DB 名**: `modemap`（Cloud SQL インスタンス `project-211906:asia-northeast1:sh1-sql`）
- **テーブル**: `mode`, `sketch`, `lineart`, `object`, `illustrate`, `effect` の6つ
- **カラム名**: SELECT 列の通り18列（mode + カテゴリ17列）
- **リレーション**: `mode.id` = 各詳細テーブルの `mode_id`（1:1）
- **カテゴリ列の所属テーブル**: `summarize()`（data.js:85-93）の集約式と照合すると一意に決まる（§2）

### 1.2 値の型・単位の証拠

| 証拠 | 箇所 | 導かれる仕様 |
|---|---|---|
| `parseInt(modeArray[i][j])` | data.js:54 | カテゴリ値は**整数** |
| `Number((item[key]/60).toFixed(1))` | data.js:120 | 単位は**分**（÷60→時間、小数1桁で出力） |
| `if (work[k] == '')` | data.js:73 | シート上の**空白セル=未着手**としてそのカテゴリの分を加算 |
| `rs.getString()` → parseInt | data.js:35,54 | 数値文字列でも動くが INT 型で十分 |

## 2. スキーマ復元

`restoration/modemap.sql` に DDL+シードを同梱。論理構造:

```
mode (id, mode) ──┬─ 1:1 ─ sketch     (mode_id, sketch)
                  ├─ 1:1 ─ lineart    (mode_id, head, body, cloth)
                  ├─ 1:1 ─ object     (mode_id, item, background)
                  ├─ 1:1 ─ illustrate (mode_id, base, shadow, erotic, line)
                  └─ 1:1 ─ effect     (mode_id, effect, erotic_effect,
                                            onomatopeia, front, back, dialog, mood)
```

`summarize()` の5系統への集約とテーブル分割が完全一致する
（sketch / lineart=head+body+cloth / object=item+background /
illustrate=base+shadow+erotic+line / effect=残り7列）。
これは原稿マンガの工程分類（下描き→ペン入れ→背景・小物→塗りベース・陰影→
効果類）をそのまま反映した設計。

## 3. カテゴリとシート列の対応（実際に集計に使われるもの）

project2 の `getWorkAnalytics()` は**原稿ブックの `lineart` シートのみ**を読む。
`getWorkTime()` は「DBカテゴリ名 = シート列名」で照合するため、
**シートに存在しないカテゴリは集計に一切寄与しない**（undefined=='' が false のため 0 加算）。

原稿 lineart シートの実列（F..V）と DB カテゴリの対応:

| DB カテゴリ | 原稿 lineart 列 | 集計対象? |
|---|---|---|
| sketch | sketch | ✅ |
| head | head | ✅ |
| body | body | ✅ |
| cloth | cloth | ✅ |
| item | item | ✅ |
| background | background | ✅ |
| base | base | ✅ |
| shadow | shadow | ✅ |
| erotic | erotic | ✅ |
| onomatopeia | onomatopeia | ✅ |
| front | front | ✅ |
| back | back | ✅ |
| dialog | dialog | ✅（※concept 側は `daialog` 表記ゆれ。project2 は原稿のみなので `dialog` が正） |
| mood | mood | ✅ |
| line | （該当列なし） | ❌ 常に0 |
| effect | （該当列なし） | ❌ 常に0 |
| erotic_effect | （該当列なし） | ❌ 常に0 |

※ `line` / `effect` / `erotic_effect` は concept ブックの color シート列
（`effect`, `erotic effect`）に対応する設計で、**カラー工程も見積もれる
汎用マスタとして設計されていた**ことが分かる（実装は lineart のみ）。
`speaking`, `nombre`, `place black rectangle` などのシート列は DB に無く、
集計対象外だった。

## 4. 行（モード名）の復元

xlsx 実データの C 列（mode列）から実在が確認できる値:

| mode 名 | 出所 | 備考 |
|---|---|---|
| `standard` | 原稿 lineart（18ページ） | ★ project2 復元に必須 |
| `battle` | 原稿 lineart（17ページ） | ★ project2 復元に必須 |
| `erotic` | concept lineart | concept 系 |
| `csp` | concept color | concept 系 |
| `coverpage` | 原稿 color | カラー工程用 |
| `coverhalf` | 原稿 color | カラー工程用 |

注意: `character` / `main-character` / `model` は parts シートの値だが、
これは project1 が使う schedule-init 側のモード体系と混同する恐れがある。
project2 が処理する lineart シートには出現しないため、modemap には
含めなくてよい（含めても無害）。

シード値の確度: `standard`/`battle` の存在は確実。concept 系・カラー系の
モードが同じ DB に同居していたかは推測（カテゴリ設計から同居が自然）。

## 5. 値（重み）の復元方針 — キャリブレーション

値は失われたが、以下の運用で再生成する:

1. **初期値**: `restoration/modemap.sql` の仮置き値（standard 1ページ ≒ 6.5時間
   想定の基準雛形）を入れる。`battle` は効果・背景系を加重した差分例。
2. **実測キャリブレーション**:
   - 実際に数ページ作業し、各カテゴリの実作業時間（分）を計測
   - `UPDATE sketch SET sketch=78 WHERE mode_id=(SELECT id FROM mode WHERE mode='standard');` 等で反映
   - 1ページ全体の合計が実感と合うか（出力の `estimated` 見て調整）
3. **検証**: `writeAnalytics` 相当を実行し、analysis シート出力
   （`plot カテゴリ名 / 残り時間(h)`）が現実的な残工数になるか確認。
   アンカー例: スナップショットの実出力に「大学 sketch 1.3」があり、
   1.3h=78分が plot「大学」内の sketch 未着手の合計値として整合する
   （ページ数×単価分）。
4. 収束したら `restoration/modemap.csv`（SELECT 結果と同形のフラットCSV）にも
   反映しておく（ローカル実装のデータ源として使える）。

## 6. project2 復元の実装方針（選択肢）

現行コードはそのままでは動かない（`for each` 構文・JDBC 空パスワード・
グローバル即接続）。復元にあたっての方向性:

| 案 | 構成 | メリット | デメリット |
|---|---|---|---|
| A. GAS 復元（JDBC再築） | Cloud SQL(またはローカルMySQL) + modemap.sql 適用 + data.js 現代化 | 元の設計に最も近い | DB運用コスト。GASからJDBCは Cloud SQL 以外不可でコスト高 |
| B. GAS 復元（スプレッドシート化）★推奨 | マスタを `modemap` シート化（modemap.csv 流用）+ data.js 書き換え | インフラ不要。編集がGUIで直観的。作者の他マスタも全部スプレッドシート運用だったことと整合 | スキーマ制約なし（運用ルールで担保） |
| C. ローカル復元（Python） | xlsx + modemap.csv を読み analysis 出力をxlsx/CLIで生成 | Google非依存・永続化しやすい | スプレッドシート入力運用との相性 |

- project2 の処理（「lineart 読み込み → 空白セルに重み乗算 → plot別集計 →
  analysis 書き出し」）は約100行で再実装可能。`for each` は標準ループ、
  グローバル即接続は遅延初期化に置き換える。
- 方式決定後、`restoration/` 配下に復元版コードを置く。

## 7. 未解決事項

| # | 項目 |
|---|---|
| 1 | 実際の重み値（実測キャリブレーションで再生成） |
| 2 | concept 系モード（csp/erotic/coverpage/coverhalf）が modemap に同居していたか |
| 3 | 復元版の実装方式（§6 の選択） |
| 4 | Cloud SQL インスタンス自体の現存（復元の必要がないなら確認不要） |
