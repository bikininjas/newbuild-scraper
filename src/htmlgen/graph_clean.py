"""
Chart.js graph rendering for price history.
"""

import json
from .normalize import normalize_price
from ..utils import format_french_date

# Constants
NO_CHANGE_LABEL = "No change"
NO_CHANGE_COLOR = "rgba(148, 163, 184, 0.1)"
PRICE_DOWN_LABEL = "Price down"
PRICE_UP_LABEL = "Price up"
DIV_CLOSE_TAG = "</div>"


def get_price_evolution_indicator(prices, color_scheme="slate"):
    """
    Returns (indicator_html, aria_label).
    color_scheme: 'slate' (for charts) or 'gray' (for tables).
    """
    if color_scheme == "slate":
        colors = {"no_change": "text-slate-400", "down": "text-green-400", "up": "text-red-400"}
    else:  # gray scheme
        colors = {"no_change": "text-gray-400", "down": "text-green-600", "up": "text-red-600"}

    if len(prices) < 2 or prices[-1] is None or prices[-2] is None:
        return (
            f'<span class="{colors["no_change"]}" aria-label="{NO_CHANGE_LABEL}">–</span>',
            NO_CHANGE_LABEL,
        )

    last, prev = prices[-1], prices[-2]
    if last < prev:
        return (
            f'<span class="{colors["down"]}" aria-label="{PRICE_DOWN_LABEL}">↓</span>',
            PRICE_DOWN_LABEL,
        )
    elif last > prev:
        return (
            f'<span class="{colors["up"]}" aria-label="{PRICE_UP_LABEL}">↑</span>',
            PRICE_UP_LABEL,
        )
    else:
        return (
            f'<span class="{colors["no_change"]}" aria-label="{NO_CHANGE_LABEL}">–</span>',
            NO_CHANGE_LABEL,
        )


def get_best_price_per_timestamp(product_history, ts_col, product_name):
    """Returns a list of (timestamp, best_price) with missing timestamps filled by last known price."""
    product_history = product_history.sort_values(by=ts_col)
    timestamps = product_history[ts_col].tolist()
    best_prices = []
    last_price = None

    for ts, group in product_history.groupby(ts_col):
        norm_prices = [
            float(normalize_price(p, product_name))
            for p in group["Price"]
            if p is not None and str(p).strip() != "" and str(p).lower() != "nan"
        ]
        valid_prices = [p for p in norm_prices if p > 0 and p < 5000]
        if valid_prices:
            min_price = min(valid_prices)
            last_price = min_price
        best_prices.append(last_price)

    return timestamps, best_prices


def render_price_history_graph_from_series(timestamps, prices, product_name):
    """Render a price history graph from given timestamps and prices."""
    indicator_html, _ = get_price_evolution_indicator(prices, "slate")

    # Format timestamps to French date style
    formatted_timestamps = [format_french_date(ts) for ts in timestamps]

    data = {
        "labels": formatted_timestamps,
        "datasets": [
            {
                "label": f"Historique - {product_name}",
                "data": prices,
                "fill": False,
                "borderColor": "#06b6d4",
                "backgroundColor": "#0891b2",
                "tension": 0.4,
                "borderWidth": 2,
            }
        ],
    }

    chart_config = {
        "type": "line",
        "data": data,
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": True, "labels": {"color": "#e2e8f0", "font": {"size": 11}}},
                "title": {
                    "display": True,
                    "text": f"Historique - {product_name}",
                    "color": "#06b6d4",
                    "font": {"size": 14, "weight": "bold"},
                },
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#94a3b8", "font": {"size": 9}},
                    "grid": {"color": NO_CHANGE_COLOR},
                },
                "y": {
                    "beginAtZero": True,
                    "ticks": {"color": "#94a3b8", "font": {"size": 9}},
                    "grid": {"color": NO_CHANGE_COLOR},
                },
            },
            "elements": {
                "point": {"hoverBackgroundColor": "#06b6d4"},
                "line": {"borderCapStyle": "round"},
            },
        },
    }

    chart_json = json.dumps(chart_config)
    canvas_id = f"chart-{abs(hash(product_name))}"

    html = f'<div class="flex items-center gap-2 mb-2"><span class="font-semibold text-slate-300">{product_name}</span>{indicator_html}</div>'
    html += '<div class="chart-bg p-4 rounded-xl">'
    html += f'<canvas id="{canvas_id}" class="w-full h-32" aria-label="Price history graph for {product_name}" role="img"></canvas>'
    html += DIV_CLOSE_TAG
    html += f'<script>new Chart(document.getElementById("{canvas_id}"), {chart_json});</script>'

    return html


def render_price_history_graph(history, product_name):
    """Render a price history graph for a specific product from history data."""
    ts_col = "Timestamp_ISO" if "Timestamp_ISO" in history.columns else "Date"
    product_history = history[history["Product_Name"] == product_name]
    timestamps, best_prices = get_best_price_per_timestamp(product_history, ts_col, product_name)

    # Interpolate missing prices by repeating last known value
    prices = [
        p if p is not None else (prices[i - 1] if i > 0 else None)
        for i, p in enumerate(best_prices)
    ]

    # Evolution indicator
    indicator_html, _ = get_price_evolution_indicator(prices, "gray")

    data = {
        "labels": timestamps,
        "datasets": [
            {
                "label": f"Price History for {product_name}",
                "data": prices,
                "fill": False,
                "borderColor": "#0ea5e9",
                "backgroundColor": "#bae6fd",
                "tension": 0.3,
            }
        ],
    }

    chart_config = {
        "type": "line",
        "data": data,
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": True},
                "title": {"display": True, "text": f"Price History for {product_name}"},
            },
            "scales": {"y": {"beginAtZero": True}},
        },
    }

    chart_json = json.dumps(chart_config)
    canvas_id = f"chart-{abs(hash(product_name))}"

    html = f'<div class="flex items-center gap-2 mb-2"><span class="font-semibold">{product_name}</span>{indicator_html}</div>'
    html += f'<canvas id="{canvas_id}" class="w-full h-32" aria-label="Price history graph for {product_name}" role="img"></canvas>'
    html += f'<script>new Chart(document.getElementById("{canvas_id}"), {chart_json});</script>'

    return html


def render_all_price_graphs(product_prices, history):
    """Render all price history graphs for multiple products."""
    html = []
    html.append('<div class="mt-12">')
    html.append(
        '<h2 class="text-2xl font-bold text-center text-cyan-700 mb-6">Best Price History Graphs</h2>'
    )

    for name, entries in product_prices.items():
        product_history = history[history["Product_Name"] == name]
        product_history = product_history.sort_values(
            by="Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        )
        ts_col = "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        timestamps, best_prices = get_best_price_per_timestamp(product_history, ts_col, name)

        prices = [
            p if p is not None else (prices[i - 1] if i > 0 else None)
            for i, p in enumerate(best_prices)
        ]

        indicator_html, _ = get_price_evolution_indicator(prices, "gray")

        data = {
            "labels": timestamps,
            "datasets": [
                {
                    "label": f"Price History for {name}",
                    "data": prices,
                    "fill": False,
                    "borderColor": "#0ea5e9",
                    "backgroundColor": "#bae6fd",
                    "tension": 0.3,
                }
            ],
        }

        chart_config = {
            "type": "line",
            "data": data,
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {"display": True},
                    "title": {"display": True, "text": f"Price History for {name}"},
                },
                "scales": {"y": {"beginAtZero": True}},
            },
        }

        chart_json = json.dumps(chart_config)
        canvas_id = f"chart-{abs(hash(name))}"

        html.append(
            f'<div class="mb-10"><div class="flex items-center gap-2 mb-2"><h3 class="text-xl font-bold">{name}</h3>{indicator_html}</div><canvas id="{canvas_id}" class="w-full h-32" aria-label="Price history graph for {name}" role="img"></canvas>'
        )
        html.append(
            f'<script>new Chart(document.getElementById("{canvas_id}"), {chart_json});</script></div>'
        )

    html.append(DIV_CLOSE_TAG)
    return "\n".join(html)
