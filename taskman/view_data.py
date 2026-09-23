"""集計結果 → ダッシュボード画面用データ構造（純粋関数、I/Oなし）。

Flask化した場合はここで作る dict をそのまま /api/data のレスポンスに
転用できるように設計する（webui設計書.md §11）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from .analyze import GROUP_ORDER, Result, analyze, total_time
from .master import Weights
from .sheet import Row


def _pct(remaining: float, total: float) -> float:
    """進捗％（時間ベース: 1 - remaining/total）。totalが0なら100%扱い。"""
    if total <= 0:
        return 100.0
    return round((1 - remaining / total) * 100, 1)


def build_dashboard_data(
    rows: list[Row],
    categories: list[str],
    weights: Weights,
    *,
    input_file: str,
) -> dict:
    """画面表示用のJSONシリアライズ可能な dict を返す。

    webui設計書.md §5.2 のスキーマに対応する。
    """
    remaining, warnings = analyze(rows, categories, weights)
    full = total_time(rows, categories, weights)

    plots = list(remaining.keys())  # 出現順

    def plot_remaining_h(plot: str) -> float:
        return round(sum(remaining[plot].values()) / 60, 1)

    def plot_total_h(plot: str) -> float:
        return round(sum(full[plot].values()) / 60, 1)

    overview = [
        {
            "plot": plot,
            "remaining_h": plot_remaining_h(plot),
            "total_h": plot_total_h(plot),
            "progress_pct": _pct(plot_remaining_h(plot), plot_total_h(plot)),
        }
        for plot in plots
    ]

    by_plot: dict[str, list[dict]] = {}
    for plot in plots:
        rows_for_plot = []
        for group in GROUP_ORDER:
            r_h = round(remaining[plot].get(group, 0) / 60, 1)
            t_h = round(full[plot].get(group, 0) / 60, 1)
            rows_for_plot.append(
                {
                    "group": group,
                    "remaining_h": r_h,
                    "total_h": t_h,
                    "progress_pct": _pct(r_h, t_h),
                }
            )
        by_plot[plot] = rows_for_plot

    by_group: dict[str, list[dict]] = {}
    for group in GROUP_ORDER:
        group_total = sum(remaining[plot].get(group, 0) for plot in plots)
        rows_for_group = []
        for plot in plots:
            minutes = remaining[plot].get(group, 0)
            r_h = round(minutes / 60, 1)
            share = round(minutes / group_total * 100, 1) if group_total > 0 else 0.0
            rows_for_group.append({"plot": plot, "remaining_h": r_h, "share_pct": share})
        by_group[group] = rows_for_group

    total_remaining_h = round(sum(sum(v.values()) for v in remaining.values()) / 60, 1)
    total_full_h = round(sum(sum(v.values()) for v in full.values()) / 60, 1)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "input_file": input_file,
        "groups": list(GROUP_ORDER),
        "plots": plots,
        "summary": {
            "total_remaining_h": total_remaining_h,
            "total_full_h": total_full_h,
            "progress_pct": _pct(total_remaining_h, total_full_h),
        },
        "overview": overview,
        "by_plot": by_plot,
        "by_group": by_group,
        "warnings": warnings,
    }
