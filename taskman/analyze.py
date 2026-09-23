"""残作業時間の集計ロジック（純粋関数、I/Oなし）。

元GAS: data.js の getWorkTime() / summarize() / getWorkAnalytics() を
ベースにしつつ、意図的に1点だけ挙動を変えている（下記参照）。

data.js の実際の挙動と、本モジュールとの差分:
  - 元コード（`getWorkTime`）は `dict = modemap[workdata[0]['mode']]` —
    その plot に属する行のうち **シート上で最初に出現した行の mode だけ**
    で重みテーブルを1つ選び、plot 内の全行に同一の重みを適用していた。
    実データでも 1つの plot 内で mode が行ごとに異なるケース（standard/
    battle混在）が実際に存在し、この元の挙動だと2行目以降の mode 値が
    無視されてしまう。これはページ単位で mode が変わりうる工程管理
    ツールとしては妥当でない（2014年当時、plot内でmodeが混在する
    ケースが想定されていなかった実装上の見落としと判断）。
    → **本モジュールは行ごとに自分の mode で重みを引く**よう意図的に
    変更している（ユーザー確認・承認済みの差分）。
  - 元コードは未定義モードでも例外を投げない（JSの `for...in undefined` は
    無害）。結果は NaN になり、出力フィルタ（`value > 0`）で静かに消える。
    本モジュールはそれを「警告してその行をスキップ」という、
    観測可能な形に変えている（意図的な差分）。
  - 空白セル（未着手）の判定は `work[k] == ''`。xlsx を openpyxl で読むと
    空セルは None になるため、None と '' の両方を「空白」として扱う。
  - plot は同一シート内で非連続に再出現しうるため、行のグルーピングは
    「plot名で全行をフィルタ」する（連続ブロックの分割ではない）。
"""
from __future__ import annotations

from .master import Weights
from .sheet import Row

GROUP_ORDER = ("sketch", "lineart", "object", "illustrate", "effect")

# data.js summarize() と同一の5群集約
GROUP_MAP: dict[str, tuple[str, ...]] = {
    "sketch": ("sketch",),
    "lineart": ("head", "body", "cloth"),
    "object": ("item", "background"),
    "illustrate": ("base", "shadow", "erotic", "line"),
    "effect": ("effect", "erotic_effect", "onomatopeia", "front", "back", "dialog", "mood"),
}

Result = dict[str, dict[str, int]]


def unique_plots(rows: list[Row]) -> list[str]:
    """出現順・重複除去した plot 名のリスト（空 plot は除外）。"""
    seen: set[str] = set()
    order: list[str] = []
    for row in rows:
        plot = row.get("plot")
        if plot in (None, ""):
            continue
        if plot not in seen:
            seen.add(plot)
            order.append(plot)  # type: ignore[arg-type]
    return order


def summarize(acc: dict[str, int]) -> dict[str, int]:
    return {group: sum(acc.get(cat, 0) for cat in cats) for group, cats in GROUP_MAP.items()}


def analyze(
    rows: list[Row], categories: list[str], weights: Weights
) -> tuple[Result, list[str]]:
    """plot ごとの残作業時間（分・5群）を集計する。

    Args:
        rows: シートの全行（メタ列＋カテゴリ列の dict）
        categories: 集計対象カテゴリ（シートヘッダ ∩ マスタの全カテゴリ、
            呼び出し側で算出済みのもの）
        weights: {mode: {category: minutes}}

    Returns:
        (result, warnings)
        result: {plot: {group: minutes}}（分単位、5群）
        warnings: 処理中に検出した警告メッセージのリスト
    """
    result: Result = {}
    skipped: dict[tuple[str, object], int] = {}  # (plot, mode) -> スキップ行数

    for plot in unique_plots(rows):
        plot_rows = [r for r in rows if r.get("plot") == plot]

        acc = {cat: 0 for cat in categories}
        for row in plot_rows:
            mode = row.get("mode")
            mode_weights = weights.get(mode)  # type: ignore[arg-type]
            if mode_weights is None:
                key = (plot, mode)
                skipped[key] = skipped.get(key, 0) + 1
                continue
            for cat in categories:
                if cat in mode_weights and row.get(cat) in (None, ""):
                    acc[cat] += mode_weights[cat]

        result[plot] = summarize(acc)

    warnings = [
        f"plot '{plot}': mode '{mode}' がマスタに未定義の行を{count}件スキップ"
        for (plot, mode), count in skipped.items()
    ]

    return result, warnings
