"""Chart configuration helpers."""

from __future__ import annotations

from typing import List, Dict
from utils import format_french_date
import json


def build_chart_datasets(series: Dict[str, any], total_history: List[Dict], palette: List[str]):
    datasets = []
    for idx, (name, data) in enumerate(series.items()):
        if data.timestamps and data.prices:
            datasets.append(
                {
                    "label": name,
                    "data": data.prices,
                    "fill": False,
                    "borderColor": palette[idx % len(palette)],
                    "backgroundColor": palette[idx % len(palette)],
                    "borderWidth": 2,
                    "tension": 0.4,
                    "pointRadius": 0,
                    "hidden": False,
                }
            )
    datasets.append(
        {
            "label": "Prix Total (€)",
            "data": [x["total"] for x in total_history],
            "fill": False,
            "borderColor": "#10b981",
            "backgroundColor": "#059669",
            "borderWidth": 3,
            "tension": 0.4,
            "pointRadius": 3,
            "pointHoverRadius": 6,
            "order": 1,
        }
    )
    return datasets


def build_chart_config(series, total_history, palette):
    labels = [format_french_date(x["timestamp"]) for x in total_history]
    datasets = build_chart_datasets(series, total_history, palette)
    return {
        "type": "line",
        "data": {"labels": labels, "datasets": datasets},
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": True, "labels": {"color": "#e2e8f0", "font": {"size": 12}}},
                "title": {
                    "display": True,
                    "text": "Historique du prix total",
                    "color": "#06b6d4",
                    "font": {"size": 16, "weight": "bold"},
                },
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#94a3b8", "font": {"size": 10}},
                    "grid": {"color": "rgba(148, 163, 184, 0.1)"},
                },
                "y": {
                    "beginAtZero": False,
                    "ticks": {"color": "#94a3b8", "font": {"size": 10}},
                    "grid": {"color": "rgba(148, 163, 184, 0.1)"},
                },
            },
            "elements": {
                "point": {"hoverBackgroundColor": "#06b6d4"},
                "line": {"borderCapStyle": "round"},
            },
        },
    }


def chart_config_json(series, total_history, palette) -> str:
    return json.dumps(build_chart_config(series, total_history, palette))


__all__ = ["build_chart_config", "build_chart_datasets", "chart_config_json"]
