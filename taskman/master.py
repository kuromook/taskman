"""重みマスタ（CSV）の読み込み。

元GAS: data.js の getModemapArray() / getModemap()（Cloud SQL JDBC）に相当。
JDBC → CSV に置き換えた以外は同一のデータ構造（{mode: {category: minutes}}）。
"""
from __future__ import annotations

import csv
from pathlib import Path

Weights = dict[str, dict[str, int]]


def load_master(path: str | Path) -> Weights:
    """restoration/modemap.csv 形式のマスタを読み込む。

    1行目ヘッダ: mode, <category>...
    2行目以降: mode名, 各カテゴリの重み（分・整数）。空セルはそのモードに
    そのカテゴリが存在しないものとして扱う（キーを持たせない）。
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"master CSV が見つかりません: {path}")

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "mode" not in reader.fieldnames:
            raise ValueError(f"master CSV に 'mode' 列がありません: {path}")
        categories = [c for c in reader.fieldnames if c and c != "mode"]

        weights: Weights = {}
        for lineno, row in enumerate(reader, start=2):
            mode = (row.get("mode") or "").strip()
            if not mode:
                continue
            cat_weights: dict[str, int] = {}
            for cat in categories:
                raw = row.get(cat)
                if raw is None or raw.strip() == "":
                    continue
                try:
                    cat_weights[cat] = int(raw)
                except ValueError as e:
                    raise ValueError(
                        f"master CSV {lineno}行目: mode='{mode}' の "
                        f"カテゴリ '{cat}' が整数ではありません: {raw!r}"
                    ) from e
            weights[mode] = cat_weights

    return weights


def master_categories(weights: Weights) -> set[str]:
    """マスタに登場する全カテゴリ名（全モードの和集合）。"""
    cats: set[str] = set()
    for cat_weights in weights.values():
        cats.update(cat_weights.keys())
    return cats
