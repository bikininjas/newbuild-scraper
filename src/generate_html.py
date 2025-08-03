def generate_html(product_prices, history):
    html = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>Product Price Tracker</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }",
        "    .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }",
        "    h1 { text-align: center; margin-bottom: 32px; }",
        "    .product { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 32px; }",
        "    .best { color: #2196f3; font-weight: bold; }",
        "    .prices, .history { margin: 12px 0 0 0; }",
        "    .prices li, .history li { margin-bottom: 4px; }",
        "    .site { font-size: 0.95em; color: #555; }",
        "    .price { font-weight: bold; }",
        "    .best-site { background: #e3f2fd; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-bottom: 8px; }",
        "    .history-title { margin-top: 18px; font-size: 1.05em; color: #666; }",
        "  </style>",
        "</head>",
        "<body>",
        '<div class="container">',
        "<h1>Product Price Tracker</h1>",
    ]
    for name, entries in product_prices.items():
        best = min(entries, key=lambda x: x["price"])
        html.append('<div class="product">')
        html.append(f"<h2>{name}</h2>")
        html.append(
            f'<div class="best-site">Best price: <span class="price">{best["price"]}€</span> <span class="site">@ <a href="{best["url"]}" target="_blank">{best["url"]}</a></span></div>'
        )
        html.append('<ul class="prices">')
        for entry in entries:
            html.append(
                f'<li><span class="price">{entry["price"]}€</span> <span class="site">@ <a href="{entry["url"]}" target="_blank">{entry["url"]}</a></span></li>'
            )
        html.append("</ul>")
        history_entries = history[history["Product_Name"] == name]
        if not history_entries.empty:
            html.append('<div class="history-title">Price history:</div>')
            html.append('<ul class="history">')
            for _, h in history_entries.iterrows():
                timestamp = (
                    h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
                )
                html.append(
                    f'<li>{timestamp}: <span class="price">{h["Price"]}€</span> <span class="site">@ <a href="{h["URL"]}" target="_blank">{h["URL"]}</a></span></li>'
                )
            html.append("</ul>")
        else:
            html.append('<div class="history-title">No price history yet.</div>')
        html.append("</div>")
    html.append("</div></body></html>")
    with open("output.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))
