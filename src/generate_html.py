from htmlgen.data import load_products, load_history
from htmlgen.normalize import normalize_price, get_category, get_site_label
from htmlgen.render import render_summary_table, render_product_cards
from htmlgen.graph import render_all_price_graphs
import os


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

    # Find cheapest product per category
    category_best = {}
    for name, entries in product_prices.items():
        norm_entries = []
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            # Only add valid, non-nan prices
            try:
                price_val = float(norm_price)
                if price_val > 0 and not (isinstance(price_val, float) and (price_val != price_val)):
                    norm_entries.append({"price": norm_price, "url": entry["url"]})
            except Exception:
                continue

def generate_html(product_prices, history):
    # Find cheapest product per category
    category_best = {}
    for name, entries in product_prices.items():
        norm_entries = []
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            # Only add valid, non-nan prices
            try:
                price_val = float(norm_price)
                if price_val > 0 and not (isinstance(price_val, float) and (price_val != price_val)):
                    norm_entries.append({"price": norm_price, "url": entry["url"]})
            except Exception:
                continue
        if not norm_entries:
            continue
        best = min(norm_entries, key=lambda x: float(x["price"]))
        cat = get_category(name, best["url"])
        if cat not in category_best or float(best["price"]) < float(category_best[cat]["price"]):
            category_best[cat] = {"name": name, "price": best["price"], "url": best["url"]}
        product_prices[name] = norm_entries
    # Prepare total price history
    if "Timestamp_ISO" in history.columns:
        ts_col = history["Timestamp_ISO"]
    else:
        ts_col = history["Date"]
    # Normalize and deduplicate timestamps
    timestamps = sorted(set(str(ts) for ts in ts_col if isinstance(ts, str) and ts.strip() and ts != 'nan'))

    # For each product, build a running minimum price series by timestamp
    product_min_prices = {}
    for cat, info in category_best.items():
        name = info["name"]
        product_history = history[history["Product_Name"] == name]
        ts_col = "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        product_history = product_history.sort_values(by=ts_col)
        min_price = None
        min_prices_by_ts = {}
        absolute_min_price = None
        for ts in timestamps:
            rows = product_history[product_history[ts_col] == ts]
            valid_prices = [float(normalize_price(row["Price"], name)) for _, row in rows.iterrows() if 0 < float(normalize_price(row["Price"], name)) < 5000]
            if valid_prices:
                current_min = min(valid_prices)
                if min_price is None or current_min < min_price:
                    min_price = current_min
                if absolute_min_price is None or current_min < absolute_min_price:
                    absolute_min_price = current_min
            min_prices_by_ts[ts] = min_price if min_price is not None else None
        # Ensure last timestamp always uses absolute best price
        if timestamps:
            min_prices_by_ts[timestamps[-1]] = absolute_min_price if absolute_min_price is not None else 0
        product_min_prices[name] = min_prices_by_ts
    # Now sum running minimums for each product at each timestamp
    total_history = []
    # Compute absolute best price for each product
    absolute_best = {}
    for name in product_min_prices:
        # Find the minimum across all timestamps, ignoring None
        min_price = min([p for p in product_min_prices[name].values() if p is not None and p > 0], default=0)
        absolute_best[name] = min_price

    for i, ts in enumerate(timestamps):
        if i == len(timestamps) - 1:
            # Last timestamp: use absolute best price for each product
            total = sum(absolute_best[name] if absolute_best[name] is not None else 0 for name in product_min_prices)
        else:
            total = sum(product_min_prices[name][ts] if product_min_prices[name][ts] is not None else 0 for name in product_min_prices)
        total_history.append({"timestamp": ts, "total": round(total, 2)})

    # Render HTML
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
        '<div id="total-warning"></div>',
        '<div class="mt-8 mb-8"><h2 class="text-xl font-bold text-center text-cyan-700 mb-4">Total Price History</h2><canvas id="total_price_chart" height="120"></canvas>'
        # Inject Chart.js script for total price history
        f'<script>\n'
        f'const totalHistory = {total_history!r};\n'
        f'const ctx = document.getElementById("total_price_chart").getContext("2d");\n'
        f'new Chart(ctx, {{\n'
        f'  type: "line",\n'
        f'  data: {{\n'
        f'    labels: totalHistory.map(x => x.timestamp),\n'
        f'    datasets: [{{\n'
        f'      label: "Total Price (€)",\n'
        f'      data: totalHistory.map(x => x.total),\n'
        f'      borderColor: "#16a34a",\n'
        f'      backgroundColor: "#bbf7d0",\n'
        f'      fill: false\n'
        f'    }}]\n'
        f'  }},\n'
        f'  options: {{\n'
        f'    responsive: true,\n'
        f'    plugins: {{\n'
        f'      legend: {{ display: true }},\n'
        f'      title: {{ display: true, text: "Total Price History" }}\n'
        f'    }},\n'
        f'    scales: {{\n'
        f'      y: {{ beginAtZero: false }}\n'
        f'    }}\n'
        f'  }}\n'
        f'}});\n'
        f'</script></div>',
    ]
    html.append(render_summary_table(category_best, history))
    html.append(render_product_cards(product_prices, history))

    html.append("</body></html>")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"[generate_html.py] HTML file written to: {output_path}")

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
