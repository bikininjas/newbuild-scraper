from scraper.html.data import load_history
from scraper.html.normalize import normalize_price, get_category, get_site_label
from scraper.html.render import render_summary_table, render_product_cards
from scraper.html.graph import render_all_price_graphs
from utils import format_french_date
from database import DatabaseManager, DatabaseConfig
from pathlib import Path
import os
import json


# PRODUCTS_CSV legacy removed (JSON + DB now authoritative)


def get_database_manager():
    """Get database manager instance based on configuration."""
    config_path = "database.conf"
    if Path(config_path).exists():
        db_config = DatabaseConfig.from_config_file(config_path)
    else:
        db_config = DatabaseConfig.from_env()

    return DatabaseManager(db_config), db_config


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
    products_data = {}
    try:
        db_manager, _ = get_database_manager()
        for product in db_manager.get_products():
            urls = db_manager.get_product_urls(product.name)
            products_data[product.name] = {
                "category": product.category,
                "urls": [u.url for u in urls],
            }
    except Exception:
        products_data = {}

    for name, entries in product_prices.items():
        valid_entries = normalize_and_filter_prices(entries, name)
        if not valid_entries:
            continue
        best = min(valid_entries, key=lambda x: float(x["price"]))

        # Get explicit category from CSV, fallback to heuristic
        product_data = products_data.get(name, {})
        cat = product_data.get("category", get_category(name, best["url"]))

        # Exclude "Upgrade Kit" from total price calculations
        if cat == "Upgrade Kit":
            product_prices[name] = valid_entries
            continue

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
            return '<div class="text-center text-slate-400 font-semibold mb-4 text-lg">📊 Aucune évolution</div>'
        elif diff < 0:
            return f'<div class="text-center text-green-400 font-semibold mb-4 text-lg">📈 ▼ -{abs(diff):.2f}€ (moins cher)</div>'
        else:
            return f'<div class="text-center text-red-400 font-semibold mb-4 text-lg">📉 ▲ +{diff:.2f}€ (plus cher)</div>'
    return ""


def _get_formatted_labels(total_history):
    return [format_french_date(x["timestamp"]) for x in total_history]


def _get_product_graph_datasets(product_min_prices, total_history):
    colors = [
        "#06b6d4",
        "#f59e42",
        "#ef4444",
        "#8b5cf6",
        "#10b981",
        "#f43f5e",
        "#eab308",
        "#84cc16",
        "#14b8a6",
        "#ec4899",
    ]
    datasets = []
    for idx, (name, data) in enumerate(product_min_prices.items()):
        if data["timestamps"] and data["prices"]:
            datasets.append(
                {
                    "label": name,
                    "data": data["prices"],
                    "fill": False,
                    "borderColor": colors[idx % len(colors)],
                    "backgroundColor": colors[idx % len(colors)],
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


def _render_html(category_products, history, product_prices, product_min_prices, total_history):
    formatted_labels = _get_formatted_labels(total_history)
    product_graph_datasets = _get_product_graph_datasets(product_min_prices, total_history)
    chart_config = {
        "type": "line",
        "data": {"labels": formatted_labels, "datasets": product_graph_datasets},
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "display": True,
                    "labels": {"color": "#e2e8f0", "font": {"size": 12}},
                },
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
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
        "  <style>",
        "    body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }",
        "    .main-content { width: 90vw; max-width: 1600px; margin: 0 auto; }",
        "    @media (max-width: 900px) { .main-content { width: 98vw; } }",
        "    canvas { background-color: rgba(15, 23, 42, 0.95) !important; border-radius: 8px; }",
        "    .chart-bg canvas { max-height: 180px !important; height: 180px !important; }",
        "    .hidden { display: none; }",
        "    .glass-card { background: rgba(15, 23, 42, 0.95) !important; backdrop-filter: blur(16px); border: 1px solid rgba(51, 65, 85, 0.4); }",
        "    .price-badge { background: linear-gradient(135deg, #059669 0%, #10b981 100%); }",
        "    .toggle-btn { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); transition: all 0.3s ease; }",
        "    .toggle-btn:hover { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); transform: translateY(-1px); }",
        "    .chart-container { background: rgba(15, 23, 42, 0.95) !important; border-radius: 16px; padding: 24px; border: 1px solid rgba(51, 65, 85, 0.3); }",
        "    .gradient-text { background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }",
        "    .price-item { background: rgba(15, 23, 42, 0.9) !important; border: 1px solid rgba(51, 65, 85, 0.4); }",
        "    .price-item:hover { background: rgba(30, 41, 59, 0.9) !important; border-color: rgba(56, 189, 248, 0.3); }",
        "    .history-item { background: rgba(15, 23, 42, 0.8) !important; border: 1px solid rgba(51, 65, 85, 0.3); }",
        "    .history-item:hover { background: rgba(30, 41, 59, 0.8) !important; }",
        "    .chart-bg { background: rgba(15, 23, 42, 0.98) !important; border: 1px solid rgba(51, 65, 85, 0.3); }",
        "    * { box-sizing: border-box; }",
        "    html, body { background: #0f172a !important; }",
        "    table { background: rgba(15, 23, 42, 0.95) !important; }",
        "    thead tr { background: rgba(30, 41, 59, 0.9) !important; }",
        "    tbody tr { background: rgba(15, 23, 42, 0.8) !important; }",
        "    tbody tr:hover { background: rgba(30, 41, 59, 0.8) !important; }",
        "    th, td { border-color: rgba(51, 65, 85, 0.4) !important; }",
        "    select { background: rgba(15, 23, 42, 0.95) !important; color: #e2e8f0 !important; border: 1px solid rgba(51, 65, 85, 0.4) !important; border-radius: 8px; padding: 8px 12px; font-size: 14px; }",
        "    select:focus { outline: none; border-color: rgba(56, 189, 248, 0.5) !important; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1); }",
        "    select option { background: rgba(15, 23, 42, 0.95) !important; color: #e2e8f0 !important; }",
        "  </style>",
        "</head>",
        '<body class="bg-slate-900 font-inter min-h-screen">',
        '<div class="main-content px-4 py-8">',
        '<h1 class="text-5xl font-extrabold text-center gradient-text mb-12 tracking-tight">Product Price Tracker</h1>',
        evolution_html,
        '<div id="total-warning"></div>',
        '<div class="chart-container mt-8 mb-8"><h2 class="text-2xl font-bold text-center text-cyan-400 mb-6">Historique du prix total</h2><canvas id="total_price_chart" height="150"></canvas>'
        f"<script>\n"
        f'const ctx = document.getElementById("total_price_chart").getContext("2d");\n'
        f"new Chart(ctx, {chart_json});\n"
        f"</script></div>",
    ]
    html.append(render_summary_table(category_products, history))
    # Build name->category map for cards
    name_category = {}
    for cat, plist in category_products.items():
        for p in plist:
            name_category[p["name"]] = {"category": cat}
    # Call render_product_cards - historical prices are now toggleable with buttons
    html.append(
        render_product_cards(
            product_prices,
            history,
            product_min_prices,
            products_meta=name_category,
        )
    )

    # Inline JavaScript for toggle functionality to keep a single self-contained HTML
    html.append(
        """
<script>
// Toggle visibility of price history sections (inlined)
function toggleHistory(historyId) {
    const historyDiv = document.getElementById(historyId);
    const icon = document.getElementById("icon-" + historyId);
    const button = icon ? icon.parentElement : null;
    if (!historyDiv) return;
    if (historyDiv.classList.contains("hidden")) {
        historyDiv.classList.remove("hidden");
        if (icon) icon.style.transform = "rotate(180deg)";
        if (button) {
            const textNode = Array.from(button.childNodes).find(n => n.nodeType === 3 && n.textContent.includes("Afficher"));
            if (textNode) textNode.textContent = "Masquer l'historique des prix";
        }
    } else {
        historyDiv.classList.add("hidden");
        if (icon) icon.style.transform = "rotate(0deg)";
        if (button) {
            const textNode = Array.from(button.childNodes).find(n => n.nodeType === 3 && n.textContent.includes("Masquer"));
            if (textNode) textNode.textContent = "Afficher l'historique des prix";
        }
    }
}
</script>
"""
    )

    html.append("</body></html>")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"[generate_html.py] HTML file written to: {output_path}")


def _get_latest_price_for_url(history, name, url):
    """
    Extract the latest valid price for a specific product and URL.
    Parameters:
        history (pandas.DataFrame): DataFrame containing price history data.
        name (str): The name of the product.
        url (str): The URL of the product.
    Returns:
        dict or None: Returns a dictionary with keys 'price' and 'url' if a valid price is found.
        Returns None if no valid price entry exists for the given product and URL.
    """
    rows = history[(history["Product_Name"] == name) & (history["URL"] == url)]
    if rows.empty:
        return None

    # Sort by timestamp (use Timestamp_ISO if available, otherwise Date)
    timestamp_col = "Timestamp_ISO" if "Timestamp_ISO" in rows.columns else "Date"
    rows = rows.sort_values(by=timestamp_col, ascending=False)
    latest = rows.iloc[0]

    # Validate price
    try:
        price_val = float(latest["Price"])
        if 0 < price_val < 5000:  # Filter outliers
            return {"price": latest["Price"], "url": url}
    except (ValueError, TypeError):
        pass

    return None


def build_product_prices(products, history):
    """Build product prices dictionary from products and history data."""
    product_prices = {}

    for name, product_data in products.items():
        urls = product_data["urls"]
        entries = []
        for url in urls:
            price_entry = _get_latest_price_for_url(history, name, url)
            if price_entry:
                entries.append(price_entry)

        if entries:
            product_prices[name] = entries

    return product_prices


def _build_category_products_with_explicit_categories(product_prices):
    """Build category_products with a placeholder category 'Other'.
    Real categories are applied via get_category_best + downstream mapping.
    """
    from collections import defaultdict

    category_products = defaultdict(list)
    for name, entries in product_prices.items():
        for entry in entries:
            category_products["Other"].append(
                {"name": name, "price": entry["price"], "url": entry["url"]}
            )
    for cat in category_products:
        category_products[cat].sort(key=lambda x: float(x["price"]))
    return category_products


def _remove_duplicates_within_categories(category_products):
    """Remove duplicate products within each category, keeping the cheapest."""
    for cat in category_products:
        # Group by product name and keep the cheapest
        product_groups = {}
        for product in category_products[cat]:
            name = product["name"]
            if name not in product_groups or float(product["price"]) < float(
                product_groups[name]["price"]
            ):
                product_groups[name] = product

        # Convert back to list, sorted by price
        category_products[cat] = sorted(product_groups.values(), key=lambda x: float(x["price"]))

    return category_products


def generate_html(product_prices, history):
    # Ensure all helpers are defined before use
    # Get best product per category and normalized product_prices
    category_best, product_prices = get_category_best(product_prices)
    timestamps = extract_timestamps(history)
    product_min_prices = get_product_min_price_series(category_best, history, timestamps)
    total_history, _ = get_total_price_history(
        {
            name: dict(zip(data["timestamps"], data["prices"]))
            for name, data in product_min_prices.items()
        },
        timestamps,
    )

    # Build category_products: category → list of product dicts (sorted by price)
    category_products = _build_category_products_with_explicit_categories(product_prices)
    category_products = _remove_duplicates_within_categories(category_products)

    _render_html(category_products, history, product_prices, product_min_prices, total_history)


def main():
    """Main function to orchestrate HTML generation from scraped data.
    Uses products from DB only (JSON import happens earlier in main scraper)."""
    # Reconstruct product_prices from DB + latest exported history CSV if exists
    db_manager, _ = get_database_manager()
    history = (
        load_history("historique_prix.csv")
        if Path("historique_prix.csv").exists()
        else db_manager.get_price_history()
    )
    # Build mapping name->urls from DB
    products = {}
    for product in db_manager.get_products():
        urls = [u.url for u in db_manager.get_product_urls(product.name)]
        products[product.name] = {"urls": urls, "category": product.category}
    product_prices = build_product_prices(products, history)
    generate_html(product_prices, history)


if __name__ == "__main__":
    main()
