def render_price_history_graph(history, product_name):
    import json
    from .normalize import normalize_price
    product_history = history[history["Product_Name"] == product_name]
    ts_col = "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
    product_history = product_history.sort_values(by=ts_col)
    # For each timestamp, get the lowest price
    best_prices = []
    labels = []
    for ts, group in product_history.groupby(ts_col):
        try:
            norm_prices = [float(normalize_price(p, product_name)) for p in group["Price"]]
            min_price = min(norm_prices)
            best_prices.append(min_price)
            labels.append(ts)
        except Exception:
            continue
    prices = best_prices
    data = {
        "labels": labels,
        "datasets": [
            {
                "label": f"Price History for {product_name}",
                "data": prices,
                "fill": False,
                "borderColor": "#0ea5e9",
                "backgroundColor": "#bae6fd",
                "tension": 0.2,
            }
        ]
    }
    chart_config = {
        "type": "line",
        "data": data,
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": True},
                "title": {"display": True, "text": f"Price History for {product_name}"}
            },
            "scales": {
                "y": {"beginAtZero": True}
            }
        }
    }
    chart_json = json.dumps(chart_config)
    canvas_id = f"chart-{abs(hash(product_name))}"
    html = f'<canvas id="{canvas_id}" class="w-full h-64"></canvas>'
    html += f'<script>new Chart(document.getElementById("{canvas_id}"), {chart_json});</script>'
    return html
"""
Chart.js graph rendering for price history.
"""

import json
from .normalize import normalize_price


def render_all_price_graphs(product_prices, history):
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
        labels = product_history[
            "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        ].tolist()
        prices = [normalize_price(p) for p in product_history["Price"]]
        data = {
            "labels": labels,
            "datasets": [
                {
                    "label": f"Price History for {name}",
                    "data": prices,
                    "fill": False,
                    "borderColor": "#0ea5e9",
                    "backgroundColor": "#bae6fd",
                    "tension": 0.2,
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
            f'<div class="mb-10"><h3 class="text-xl font-bold mb-2">{name}</h3><canvas id="{canvas_id}" class="w-full h-64"></canvas>'
        )
        html.append(
            f'<script>new Chart(document.getElementById("{canvas_id}"), {chart_json});</script></div>'
        )
    html.append("</div>")
    return "\n".join(html)
