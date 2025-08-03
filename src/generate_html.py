def generate_html(product_prices, history):
    # --- Price normalization ---
    def normalize_price(price, name=None):
        try:
            p = float(price)
        except Exception:
            return price
        # Heuristic: if price > 2000 and product is not a GPU, CPU, or Upgrade Kit, it's probably off by 100
        if p > 2000:
            if name:
                name_l = name.lower()
                if not any(x in name_l for x in ["gpu", "graphics", "carte graphique", "cpu", "ryzen", "processeur", "upgrade kit", "kit"]):
                    p = p / 100
            else:
                p = p / 100
        return f"{p:.2f}"
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
        '  <style>body { font-family: \'Inter\', sans-serif; }</style>',
        "</head>",
        '<body class="bg-slate-50 font-inter">',
        '<div class="max-w-4xl mx-auto px-4 py-8">',
        '<h1 class="text-4xl font-extrabold text-center text-slate-900 mb-10">Product Price Tracker</h1>',
        '<div id="total-warning"></div>',
    ]
    # --- Prepare total price history ---
    total_history = []
    # For each unique timestamp, sum the best price for each product
    if "Timestamp_ISO" in history.columns:
        ts_col = history["Timestamp_ISO"]
    else:
        ts_col = history["Date"]
    timestamps = sorted(set(str(ts) for ts in ts_col if isinstance(ts, str) and ts.strip() and ts != 'nan'))
    for ts in timestamps:
        total = 0
        for name, entries in product_prices.items():
            # Find best price for this product at this timestamp
            rows = history[(history["Product_Name"] == name) & ((history["Timestamp_ISO"] == ts) if "Timestamp_ISO" in history.columns else (history["Date"] == ts))]
            if not rows.empty:
                best_row = rows.sort_values(by="Price").iloc[0]
                norm_price = float(normalize_price(best_row["Price"], name))
                total += norm_price
        total_history.append({"timestamp": ts, "total": total})
    # --- Prepare JS data for price graphs ---
    product_graph_data = {}
    for name, entries in product_prices.items():
        # Get all history for this product
        h_entries = history[history["Product_Name"] == name]
        graph_points = []
        for _, h in h_entries.iterrows():
            ts = h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
            norm_price = float(normalize_price(h["Price"], name))
            graph_points.append({"timestamp": ts, "price": norm_price})
        product_graph_data[name] = graph_points

    # --- Category mapping ---
    def get_category(name, url):
        name_l = name.lower()
        # Cooler must be checked before CPU to avoid misclassification
        if any(x in name_l for x in ["cooler", "spirit", "air", "ventirad", "thermalright"]):
            return "Cooler"
        if any(x in name_l for x in ["cpu", "ryzen", "intel", "amd processor", "processeur", "9800x3d", "9800 x3d"]):
            return "CPU"
        if any(x in name_l for x in ["radeon", "geforce", "rtx", "gpu", "graphics", "carte graphique", "pulse radeon"]):
            return "GPU"
        if any(x in name_l for x in ["ram", "ddr", "memory", "mémoire"]):
            return "RAM"
        if any(x in name_l for x in ["ssd", "nvme", "m.2", "disque"]):
            return "SSD"
        if any(x in name_l for x in ["motherboard", "carte mère", "b850", "atx", "tuf gaming", "asus"]):
            return "Motherboard"
        if any(x in name_l for x in ["alimentation", "psu", "power supply", "a850gl"]):
            return "PSU"
        if any(x in name_l for x in ["keyboard", "clavier", "k70", "corsair"]):
            return "Keyboard"
        if any(x in name_l for x in ["mouse", "souris", "g502", "logitech"]):
            return "Mouse"
        if any(x in name_l for x in ["kit", "upgrade"]):
            return "Upgrade Kit"
        return "Other"

    def get_site_label(url):
        if "amazon." in url:
            return "Amazon"
        if "ldlc." in url:
            return "LDLC"
        if "idealo." in url:
            return "Idealo"
        if "grosbill." in url:
            return "Grosbill"
        if "materiel.net" in url:
            return "Materiel.net"
        if "topachat." in url:
            return "TopAchat"
        if "alternate." in url:
            return "Alternate"
        if "bpm-power." in url:
            return "BPM Power"
        if "pccomponentes." in url:
            return "PCComponentes"
        if "caseking." in url:
            return "Caseking"
        return url.split("//")[-1].split("/")[0]

    # --- Find cheapest product per category ---
    category_best = {}
    for name, entries in product_prices.items():
        # Normalize all prices in entries
        norm_entries = []
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            norm_entries.append({"price": norm_price, "url": entry["url"]})
        best = min(norm_entries, key=lambda x: float(x["price"]))
        cat = get_category(name, best["url"])
        if cat not in category_best or float(best["price"]) < float(category_best[cat]["price"]):
            category_best[cat] = {"name": name, "price": best["price"], "url": best["url"]}
        # Replace entries with normalized for rendering below
        product_prices[name] = norm_entries

    # --- Add summary table ---
    html.append('<div class="overflow-x-auto mb-10">')
    html.append('<table class="min-w-full bg-white rounded-xl shadow border border-slate-200">')
    html.append('<thead><tr>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Category</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Product</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Best Price</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Best Site</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Last Seen</th>'
        '</tr></thead><tbody>')
    total_price = 0
    for cat, info in category_best.items():
        name = info["name"]
        price = info["price"]
        url = info["url"]
        total_price += float(price)
        # Find latest timestamp for best price
        history_entries = history[(history["Product_Name"] == name) & (history["Price"] == price) & (history["URL"] == url)]
        last_seen = "?"
        if not history_entries.empty:
            if "Timestamp_ISO" in history_entries.columns:
                latest_row = history_entries.sort_values(by="Timestamp_ISO", ascending=False).iloc[0]
                last_seen = latest_row["Timestamp_ISO"]
            elif "Date" in history_entries.columns:
                latest_row = history_entries.sort_values(by="Date", ascending=False).iloc[0]
                last_seen = latest_row["Date"]
        site_label = get_site_label(url)
        html.append(f'<tr>'
            f'<td class="border-t px-4 py-2 text-slate-800">{cat}</td>'
            f'<td class="border-t px-4 py-2 text-slate-800">{name}</td>'
            f'<td class="border-t px-4 py-2 font-bold text-green-600">{price}€</td>'
            f'<td class="border-t px-4 py-2"><a href="{url}" target="_blank" class="text-cyan-700 underline">{site_label}</a></td>'
            f'<td class="border-t px-4 py-2 text-xs text-slate-500">{last_seen}</td>'
            f'</tr>')
    # Add total row
    html.append(f'<tr>'
        f'<td class="border-t px-4 py-2 font-bold text-slate-900">Total</td>'
        f'<td class="border-t px-4 py-2"></td>'
        f'<td class="border-t px-4 py-2 font-bold text-green-700">{total_price:.2f}€</td>'
        f'<td class="border-t px-4 py-2"></td>'
        f'<td class="border-t px-4 py-2"></td>'
        f'</tr>')
    html.append('</tbody></table></div>')

    # --- Product cards grid ---
    html.append('<div class="grid gap-8">')
    for name, entries in product_prices.items():
        best = min(entries, key=lambda x: x["price"])
        html.append('<div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">')
        html.append(f'<h2 class="text-2xl font-bold text-cyan-700 mb-4">{name}</h2>')
        html.append(
            f'<div class="mb-6"><span class="inline-block bg-cyan-50 text-cyan-700 font-semibold px-4 py-2 rounded-lg shadow">Best price: <span class="font-bold">{best["price"]}€</span> @ <a href="{best["url"]}" target="_blank" class="underline">{best["url"]}</a></span></div>'
        )
        html.append('<ul class="mb-6">')
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            html.append(
                f'<li class="mb-2"><span class="font-bold text-green-600">{norm_price}€</span> @ <a href="{entry["url"]}" target="_blank" class="text-cyan-700 underline">{entry["url"]}</a></li>'
            )
        html.append("</ul>")
        history_entries = history[history["Product_Name"] == name]
        if not history_entries.empty:
            html.append('<div class="font-semibold text-slate-700 mb-2">Price history:</div>')
            html.append('<ul class="text-sm text-slate-600">')
            for _, h in history_entries.iterrows():
                timestamp = (
                    h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
                )
                norm_price = normalize_price(h["Price"], name)
                html.append(
                    f'<li class="mb-1">{timestamp}: <span class="font-bold text-green-600">{norm_price}€</span> @ <a href="{h["URL"]}" target="_blank" class="text-cyan-700 underline">{h["URL"]}</a></li>'
                )
            html.append("</ul>")
        else:
            html.append('<div class="font-semibold text-slate-700 mb-2">No price history yet.</div>')
        html.append("</div>")
    html.append("</div>")
    # --- Add price history graphs ---
    html.append('<div class="mt-12">')
    html.append('<h2 class="text-2xl font-bold text-center text-cyan-700 mb-6">Best Price History Graphs</h2>')
    for name, points in product_graph_data.items():
        canvas_id = f"chart_{abs(hash(name))}"  # unique id
        html.append(f'<div class="mb-10"><h3 class="text-xl font-bold mb-2">{name}</h3><canvas id="{canvas_id}" height="120"></canvas></div>')
    html.append('</div>')
    # --- Add JS for graphs and total warning ---
    html.append('<script>')
    # JS: total price history and warning
    html.append('const totalHistory = ' + str([{"timestamp": t["timestamp"], "total": round(t["total"],2)} for t in total_history]) + ';')
    html.append('let warningDiv = document.getElementById("total-warning");')
    html.append('if (totalHistory.length > 1) {')
    html.append('  let prev = totalHistory[totalHistory.length-2].total;')
    html.append('  let curr = totalHistory[totalHistory.length-1].total;')
    html.append('  if (curr > prev) warningDiv.innerHTML = `<div class=\"bg-red-100 text-red-700 font-bold px-4 py-2 rounded mb-6 text-center\">⚠️ Total price increased by ${(curr-prev).toFixed(2)}€ (from ${prev}€ to ${curr}€)</div>`;')
    html.append('  else if (curr < prev) warningDiv.innerHTML = `<div class=\"bg-green-100 text-green-700 font-bold px-4 py-2 rounded mb-6 text-center\">✅ Total price decreased by ${(prev-curr).toFixed(2)}€ (from ${prev}€ to ${curr}€)</div>`;')
    html.append('}')
    # JS: product price graphs
    for name, points in product_graph_data.items():
        canvas_id = f"chart_{abs(hash(name))}"
        labels = [p["timestamp"] for p in points]
        prices = [p["price"] for p in points]
        html.append(f'new Chart(document.getElementById("{canvas_id}"), {{type: "line", data: {{labels: {labels}, datasets: [{{label: "Best Price (€)", data: {prices}, borderColor: "#06b6d4", backgroundColor: "#e0f2fe", fill: false}}]}}, options: {{scales: {{y: {{beginAtZero: false}}}}}}}});')
    html.append('</script>')
    html.append("</body></html>")
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"[generate_html.py] HTML file written to: {output_path}")


if __name__ == "__main__":
    import pandas as pd
    import csv
    # Load product list
    products = {}
    with open("produits.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Product_Name"].strip()
            url = row["URL"].strip()
            products.setdefault(name, []).append(url)

    # Load price history
    history = pd.read_csv("historique_prix.csv", encoding="utf-8")

    # Build product_prices: for each product, collect latest price per URL
    product_prices = {}
    for name, urls in products.items():
        entries = []
        for url in urls:
            # Find all history rows for this product and URL
            rows = history[(history["Product_Name"] == name) & (history["URL"] == url)]
            if not rows.empty:
                # Use the latest entry (by Timestamp_ISO if present, else Date)
                if "Timestamp_ISO" in rows:
                    rows = rows.sort_values(by="Timestamp_ISO", ascending=False)
                else:
                    rows = rows.sort_values(by="Date", ascending=False)
                latest = rows.iloc[0]
                entries.append({"price": latest["Price"], "url": url})
        if entries:
            product_prices[name] = entries

    generate_html(product_prices, history)
