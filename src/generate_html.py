def normalize_and_filter_prices(entries, name):
    valid_entries = []
    for entry in entries:
        try:
            norm_price = normalize_price(entry["price"], name)
            price_val = float(norm_price)
            if 0 < price_val < 5000:
                valid_entries.append({"price": norm_price, "url": entry["url"]})
        except Exception:
            continue
    return valid_entries

def get_category_best(product_prices):
    category_best = {}
    for name, entries in product_prices.items():
        valid_entries = normalize_and_filter_prices(entries, name)
        if not valid_entries:
            continue
        best = min(valid_entries, key=lambda x: float(x["price"]))
        cat = get_category(name, best["url"])
        if cat not in category_best or float(best["price"]) < float(category_best[cat]["price"]):
            category_best[cat] = {
                "name": name,
                "price": best["price"],
                "url": best["url"],
            }
        product_prices[name] = valid_entries
    return category_best, product_prices

def extract_timestamps(history):
    if "Timestamp_ISO" in history.columns:
        ts_col = history["Timestamp_ISO"]
    else:
        ts_col = history["Date"]
    return sorted({str(ts) for ts in ts_col if isinstance(ts, str) and ts.strip() and ts != "nan"})

def get_product_min_price_series(category_best, history, timestamps):
    product_min_prices = {}
    for cat, info in category_best.items():
        name = info["name"]
        product_history = history[history["Product_Name"] == name]
        ts_col_name = "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        product_history = product_history.sort_values(by=ts_col_name)
        prices = []
        ts_labels = []
        for ts, group in product_history.groupby(ts_col_name):
            valid_prices = [
                float(normalize_price(row["Price"], name))
                for _, row in group.iterrows()
                if 0 < float(normalize_price(row["Price"], name)) < 5000
            ]
            if valid_prices:
                min_price = min(valid_prices)
                prices.append(min_price)
                ts_labels.append(ts)
        product_min_prices[name] = {"timestamps": ts_labels, "prices": prices}
    return product_min_prices

def get_total_price_history(product_min_prices, timestamps):
    total_history = []
    absolute_best = {}
    for name, ts_price_dict in product_min_prices.items():
        prices = [p for p in ts_price_dict.values() if p is not None and p > 0]
        min_price = min(prices) if prices else 0
        absolute_best[name] = min_price
    for i, ts in enumerate(timestamps):
        total = 0
        for name, ts_price_dict in product_min_prices.items():
            if i == len(timestamps) - 1:
                total += absolute_best.get(name, 0)
            else:
                total += ts_price_dict.get(ts, 0) if ts_price_dict.get(ts, 0) is not None else 0
        total_history.append({"timestamp": ts, "total": round(total, 2)})
    return total_history, absolute_best

def _get_evolution_html(total_history):
    if len(total_history) >= 2:
        prev = total_history[-2]["total"]
        curr = total_history[-1]["total"]
        diff = round(curr - prev, 2)
        if diff == 0:
            return '<div class="text-center text-slate-500 font-semibold mb-2">No evolution</div>'
        elif diff < 0:
            return f'<div class="text-center text-green-600 font-semibold mb-2">▼ -{abs(diff):.2f}€ (moins cher)</div>'
        else:
            return f'<div class="text-center text-red-600 font-semibold mb-2">▲ +{diff:.2f}€ (plus cher)</div>'
    return ""

def _get_formatted_labels(total_history):
    from datetime import datetime
    MONTHS_FR = [
        "janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"
    ]
    def format_french_short(dtstr):
        try:
            if "T" in dtstr:
                dt = datetime.fromisoformat(dtstr.split(".")[0])
            else:
                dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
            month = MONTHS_FR[dt.month - 1]
            return f"{dt.day:02d} {month} {dt.year} - {dt.hour:02d}:{dt.minute:02d}"
        except Exception:
            return dtstr
    return [format_french_short(x["timestamp"]) for x in total_history]

def _get_product_graph_datasets(product_min_prices, total_history):
    colors = [
        "#0ea5e9", "#f59e42", "#e11d48", "#6366f1", "#16a34a",
        "#f43f5e", "#facc15", "#a3e635", "#14b8a6", "#f472b6"
    ]
    datasets = []
    for idx, (name, data) in enumerate(product_min_prices.items()):
        if data["timestamps"] and data["prices"]:
            datasets.append({
                "label": name,
                "data": data["prices"],
                "fill": False,
                "borderColor": colors[idx % len(colors)],
                "backgroundColor": colors[idx % len(colors)],
                "borderWidth": 1,
                "tension": 0.3,
                "pointRadius": 0,
                "hidden": False,
            })
    datasets.append({
        "label": "Total Price (€)",
        "data": [x["total"] for x in total_history],
        "fill": False,
        "borderColor": "#16a34a",
        "backgroundColor": "#bbf7d0",
        "borderWidth": 4,
        "tension": 0.3,
        "pointRadius": 2,
        "order": 1,
    })
    return datasets

def _render_html(category_best, history, product_prices, product_min_prices, total_history):
    formatted_labels = _get_formatted_labels(total_history)
    product_graph_datasets = _get_product_graph_datasets(product_min_prices, total_history)
    chart_config = {
        "type": "line",
        "data": {"labels": formatted_labels, "datasets": product_graph_datasets},
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": True}, "title": {"display": True, "text": "Total Price History"}},
            "scales": {"y": {"beginAtZero": False}},
        },
    }
    chart_json = json.dumps(chart_config)
    evolution_html = _get_evolution_html(total_history)
    html = [
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>Product Price Tracker</title>",
        '  <script src="https://cdn.tailwindcss.com"></script>',
        '  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>',
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap" rel="stylesheet">',
        "  <style>body { font-family: 'Inter', sans-serif; } .main-content { width: 90vw; max-width: 1600px; margin: 0 auto; } @media (max-width: 900px) { .main-content { width: 98vw; } } canvas { max-height: 60px !important; height: 60px !important; } </style>",
        "</head>",
        '<body class="bg-slate-50 font-inter">',
        '<div class="main-content px-4 py-8">',
        '<h1 class="text-4xl font-extrabold text-center text-slate-900 mb-10">Product Price Tracker</h1>',
        evolution_html,
        '<div id="total-warning"></div>',
        '<div class="mt-8 mb-8"><h2 class="text-xl font-bold text-center text-cyan-700 mb-4">Historique du prix total</h2><canvas id="total_price_chart" height="60"></canvas>'
        f"<script>\n"
        f'const ctx = document.getElementById("total_price_chart").getContext("2d");\n'
        f"new Chart(ctx, {chart_json});\n"
        f"</script></div>",
    ]
    html.append(render_summary_table(category_best, history))
    # Monkey-patch render_product_cards to remove historical prices section
    def render_product_cards_no_history(product_prices, history, product_min_prices):
        # Use the original function but remove/hide historical prices section in the output
        # If the original function returns HTML as a string, we can filter out the section
        html_cards = render_product_cards(product_prices, history, product_min_prices)
        # Remove 'Historique des prix :' and everything after (if present)
        import re
        html_cards = re.sub(r'<h2[^>]*>Historique des prix.*?</table>', '', html_cards, flags=re.DOTALL)
        return html_cards
    html.append(render_product_cards_no_history(product_prices, history, product_min_prices))
    # Do NOT render historical prices section at all
    html.append("</body></html>")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"[generate_html.py] HTML file written to: {output_path}")
# Helper functions for generate_html
def _get_evolution_html(total_history):
    if len(total_history) >= 2:
        prev = total_history[-2]["total"]
        curr = total_history[-1]["total"]
        diff = round(curr - prev, 2)
        if diff == 0:
            return '<div class="text-center text-slate-500 font-semibold mb-2">No evolution</div>'
        elif diff < 0:
            return f'<div class="text-center text-green-600 font-semibold mb-2">▼ -{abs(diff):.2f}€ (moins cher)</div>'
        else:
            return f'<div class="text-center text-red-600 font-semibold mb-2">▲ +{diff:.2f}€ (plus cher)</div>'
    return ""

def _get_formatted_labels(total_history):
    from datetime import datetime
    def format_french_short(dtstr):
        try:
            if "T" in dtstr:
                dt = datetime.fromisoformat(dtstr.split(".")[0])
            else:
                dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y - %H:%M")
        except Exception:
            return dtstr
    return [format_french_short(x["timestamp"]) for x in total_history]

def _get_product_graph_datasets(product_min_prices, total_history):
    colors = [
        "#0ea5e9", "#f59e42", "#e11d48", "#6366f1", "#16a34a", "#f43f5e", "#facc15", "#a3e635", "#14b8a6", "#f472b6",
    ]
    datasets = []
    for idx, (name, data) in enumerate(product_min_prices.items()):
        if data["timestamps"] and data["prices"]:
            datasets.append({
                "label": name,
                "data": data["prices"],
                "fill": False,
                "borderColor": colors[idx % len(colors)],
                "backgroundColor": colors[idx % len(colors)],
                "borderWidth": 1,
                "tension": 0.3,
                "pointRadius": 0,
                "hidden": False,
            })
    datasets.append({
        "label": "Total Price (€)",
        "data": [x["total"] for x in total_history],
        "fill": False,
        "borderColor": "#16a34a",
        "backgroundColor": "#bbf7d0",
        "borderWidth": 4,
        "tension": 0.3,
        "pointRadius": 2,
        "order": 1,
    })
    return datasets

def _render_html(category_best, history, product_prices, product_min_prices, total_history):
    formatted_labels = _get_formatted_labels(total_history)
    product_graph_datasets = _get_product_graph_datasets(product_min_prices, total_history)
    chart_config = {
        "type": "line",
        "data": {"labels": formatted_labels, "datasets": product_graph_datasets},
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": True}, "title": {"display": True, "text": "Total Price History"}},
            "scales": {"y": {"beginAtZero": False}},
        },
    }
    chart_json = json.dumps(chart_config)
    evolution_html = _get_evolution_html(total_history)
    html = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>Product Price Tracker</title>",
        '  <script src="https://cdn.tailwindcss.com"></script>',
        '  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>',
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap" rel="stylesheet">',
        "  <style>body { font-family: 'Inter', sans-serif; } .main-content { width: 90vw; max-width: 1600px; margin: 0 auto; } @media (max-width: 900px) { .main-content { width: 98vw; } }</style>",
        "</head>",
        '<body class="bg-slate-50 font-inter">',
        '<div class="main-content px-4 py-8">',
        '<h1 class="text-4xl font-extrabold text-center text-slate-900 mb-10">Product Price Tracker</h1>',
        evolution_html,
        '<div id="total-warning"></div>',
        '<div class="mt-8 mb-8"><h2 class="text-xl font-bold text-center text-cyan-700 mb-4">Total Price History</h2><canvas id="total_price_chart" height="120"></canvas>'
        f"<script>\n"
        f'const ctx = document.getElementById("total_price_chart").getContext("2d");\n'
        f"new Chart(ctx, {chart_json});\n"
        f"</script></div>",
    ]
    html.append(render_summary_table(category_best, history))
    html.append(render_product_cards(product_prices, history, product_min_prices))
    html.append("</body></html>")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"[generate_html.py] HTML file written to: {output_path}")
from htmlgen.data import load_products, load_history
from htmlgen.normalize import normalize_price, get_category, get_site_label
from htmlgen.render import render_summary_table, render_product_cards
from htmlgen.graph import render_all_price_graphs
import os
import json


def build_product_prices(products, history):
    product_prices = {}
    for name, urls in products.items():
        entries = []
        for url in urls:
            rows = history[(history["Product_Name"] == name) & (history["URL"] == url)]
            if not rows.empty:
                if "Timestamp_ISO" in rows:
                    rows = rows.sort_values(by="Timestamp_ISO", ascending=False)
                else:
                    rows = rows.sort_values(by="Date", ascending=False)
                latest = rows.iloc[0]
                try:
                    price_val = float(latest["Price"])
                    if 0 < price_val < 5000:
                        entries.append({"price": latest["Price"], "url": url})
                except Exception:
                    continue
        if entries:
            product_prices[name] = entries
    return product_prices

def generate_html(product_prices, history):
    # Ensure all helpers are defined before use
    category_best, product_prices = get_category_best(product_prices)
    timestamps = extract_timestamps(history)
    product_min_prices = get_product_min_price_series(category_best, history, timestamps)
    total_history, _ = get_total_price_history(
        {name: dict(zip(data["timestamps"], data["prices"])) for name, data in product_min_prices.items()},
        timestamps,
    )
    _render_html(category_best, history, product_prices, product_min_prices, total_history)
    # ...existing code...


def main():
    products = load_products("produits.csv")
    history = load_history("historique_prix.csv")
    # Build product_prices: for each product, collect latest price per URL
    product_prices = {}
    for name, urls in products.items():
        entries = []
        for url in urls:
            rows = history[(history["Product_Name"] == name) & (history["URL"] == url)]
            if not rows.empty:
                if "Timestamp_ISO" in rows:
                    rows = rows.sort_values(by="Timestamp_ISO", ascending=False)
                else:
                    rows = rows.sort_values(by="Date", ascending=False)
                latest = rows.iloc[0]
                # Filter out outlier/invalid prices (e.g., > 5000)
                try:
                    price_val = float(latest["Price"])
                    if 0 < price_val < 5000:
                        entries.append({"price": latest["Price"], "url": url})
                except Exception:
                    continue
        if entries:
            product_prices[name] = entries
    generate_html(product_prices, history)


if __name__ == "__main__":
    main()
