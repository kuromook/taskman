"""CLI: python -m taskman analyze <input.xlsx> [--sheet lineart] [--master ...]

元GAS: data.js の constructAnalytics() / writeAnalytics() に相当。
書き戻し先が analysis シートではなく標準出力になっている点のみ異なる。
"""
from __future__ import annotations

import argparse
import sys

from .analyze import GROUP_ORDER, analyze
from .dashboard import render as render_dashboard
from .master import load_master, master_categories
from .sheet import load_sheet
from .view_data import build_dashboard_data

DEFAULT_MASTER = "restoration/modemap.csv"
DEFAULT_SHEET = "lineart"
DEFAULT_DASHBOARD_OUTPUT = "dashboard.html"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taskman", description="原稿ブック lineart の残作業時間を集計する"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="残作業時間を集計して表示する")
    p_analyze.add_argument("input", help="入力xlsx（原稿ブック形式）")
    p_analyze.add_argument(
        "--sheet", default=DEFAULT_SHEET, help=f"対象シート名（既定: {DEFAULT_SHEET}）"
    )
    p_analyze.add_argument(
        "--master", default=DEFAULT_MASTER, help=f"重みマスタCSV（既定: {DEFAULT_MASTER}）"
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_dashboard = sub.add_parser(
        "dashboard", help="静的HTMLダッシュボードを生成する"
    )
    p_dashboard.add_argument("input", help="入力xlsx（原稿ブック形式）")
    p_dashboard.add_argument(
        "--sheet", default=DEFAULT_SHEET, help=f"対象シート名（既定: {DEFAULT_SHEET}）"
    )
    p_dashboard.add_argument(
        "--master", default=DEFAULT_MASTER, help=f"重みマスタCSV（既定: {DEFAULT_MASTER}）"
    )
    p_dashboard.add_argument(
        "-o",
        "--output",
        default=DEFAULT_DASHBOARD_OUTPUT,
        help=f"出力HTMLファイルパス（既定: {DEFAULT_DASHBOARD_OUTPUT}）",
    )
    p_dashboard.set_defaults(func=cmd_dashboard)

    return parser


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        weights = load_master(args.master)
        rows, sheet_categories = load_sheet(args.input, sheet_name=args.sheet)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    categories = [c for c in sheet_categories if c in master_categories(weights)]
    result, warnings = analyze(rows, categories, weights)

    _print_table(result)

    if warnings:
        print(file=sys.stderr)
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)

    return 0


def _print_table(result: dict[str, dict[str, int]]) -> None:
    # (plot, group, hours) の出力行。0以下は出力しない。plot出現順×5群の固定順。
    lines: list[tuple[str, str, float]] = []
    for plot, groups in result.items():
        for group in GROUP_ORDER:
            minutes = groups.get(group, 0)
            hours = round(minutes / 60, 1)
            if hours > 0:
                lines.append((plot, group, hours))

    if not lines:
        print("(該当データなし)")
        return

    plot_w = max(len(p) for p, _, _ in lines)
    group_w = max(len(g) for _, g, _ in lines)
    plot_w = max(plot_w, len("plot"))
    group_w = max(group_w, len("category"))

    header = f"{'plot':<{plot_w}}  {'category':<{group_w}}  rest(h)"
    print(header)
    print("-" * len(header))
    for plot, group, hours in lines:
        print(f"{plot:<{plot_w}}  {group:<{group_w}}  {hours:>6.1f}")

    total = sum(h for _, _, h in lines)
    print("-" * len(header))
    print(f"{'total':<{plot_w + 2 + group_w}}  {total:>6.1f}")


def cmd_dashboard(args: argparse.Namespace) -> int:
    try:
        weights = load_master(args.master)
        rows, sheet_categories = load_sheet(args.input, sheet_name=args.sheet)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    categories = [c for c in sheet_categories if c in master_categories(weights)]
    data = build_dashboard_data(rows, categories, weights, input_file=args.input)
    html = render_dashboard(data)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"generated: {args.output}")
    if data["warnings"]:
        print(file=sys.stderr)
        for w in data["warnings"]:
            print(f"warning: {w}", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
