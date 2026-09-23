"""静的ダッシュボードHTMLの生成。

webui設計書.md §7: テンプレートに埋め込みJSONを差し込むだけの単純な
実装。テンプレート内のJS（Chart.jsのテンプレートリテラル等）に `$` が
多用されるため、string.Template ではなく素朴な文字列置換
（一意なプレースホルダ `__DASHBOARD_DATA_JSON__`）を使う
（string.Templateは `$` を全文スキャンして展開してしまい、JS側の
`${...}` と衝突するため）。
"""
from __future__ import annotations

import importlib.resources
import json

PLACEHOLDER = "__DASHBOARD_DATA_JSON__"


def render(data: dict) -> str:
    """ダッシュボードデータからHTML文字列を生成する（純粋関数）。"""
    template = (
        importlib.resources.files("taskman")
        .joinpath("templates", "dashboard.html.tmpl")
        .read_text(encoding="utf-8")
    )
    if PLACEHOLDER not in template:
        raise ValueError(f"テンプレートにプレースホルダ {PLACEHOLDER} が見つかりません")

    json_str = json.dumps(data, ensure_ascii=False, indent=None)
    return template.replace(PLACEHOLDER, json_str)
