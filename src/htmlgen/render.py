"""
HTML rendering for summary table, product cards, and graphs.
"""

import math
from .normalize import normalize_price, get_category, get_site_label


def render_summary_table(category_best, history):
    html = []
    total_price = 0
    html.append('<div class="overflow-x-auto mb-10">')
    html.append(
        '<table class="min-w-full bg-white rounded-xl shadow border border-slate-200">'
    )
    html.append(
        "<thead><tr>"
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Category</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Product</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Best Price</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Best Site</th>'
        '<th class="px-4 py-3 text-left text-xs font-semibold text-slate-700">Best Price Seen On</th>'
        "</tr></thead><tbody>"
    )
    import numpy as np
    from datetime import datetime
    def format_french_date(dtstr):
        # Try to parse ISO or fallback to raw string
        try:
            if "T" in dtstr:
                dt = datetime.fromisoformat(dtstr.split(".")[0])
            else:
                dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
            months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            month = months[dt.month - 1]
            return f"{dt.day} {month} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"
        except Exception:
            return dtstr
    for cat, info in category_best.items():
        name = info["name"]
        price = float(info["price"])
        url = info["url"]
        total_price += price
        # Find all history entries for this product and URL
        history_entries = history[(history["Product_Name"] == name) & (history["URL"] == url)]
        # Match normalized price with a tolerance
        matched = history_entries.copy()
        matched["Price_float"] = matched["Price"].apply(lambda x: float(x) if str(x).replace(",", ".").replace("€", "").strip().replace(" ", "") not in ["", "nan"] else np.nan)
        matched = matched[np.isclose(matched["Price_float"], price, atol=0.01)]
        best_seen = "?"
        if not matched.empty:
            # Find the earliest timestamp for the best price
            if "Timestamp_ISO" in matched.columns:
                valid_rows = matched[matched["Timestamp_ISO"].notnull() & (matched["Timestamp_ISO"] != "")]
                if not valid_rows.empty:
                    best_row = valid_rows.sort_values(by="Timestamp_ISO").iloc[0]
                    best_seen = format_french_date(str(best_row["Timestamp_ISO"]))
            elif "Date" in matched.columns:
                valid_rows = matched[matched["Date"].notnull() & (matched["Date"] != "")]
                if not valid_rows.empty:
                    best_row = valid_rows.sort_values(by="Date").iloc[0]
                    best_seen = format_french_date(str(best_row["Date"]))
        site_label = get_site_label(url)
        html.append(
            f"<tr>"
            f'<td class="border-t px-4 py-2 text-slate-800">{cat}</td>'
            f'<td class="border-t px-4 py-2 text-slate-800">{name}</td>'
            f'<td class="border-t px-4 py-2 font-bold text-green-600">{price}€</td>'
            f'<td class="border-t px-4 py-2"><a href="{url}" target="_blank" class="text-cyan-700 underline">{site_label}</a></td>'
            f'<td class="border-t px-4 py-2 text-xs text-slate-500">{best_seen}</td>'
            f"</tr>"
        )
    html.append(
        f"<tr>"
        f'<td class="border-t px-4 py-2 font-bold text-slate-900">Total</td>'
        f'<td class="border-t px-4 py-2"></td>'
        f'<td class="border-t px-4 py-2 font-bold text-green-700">{total_price:.2f}€</td>'
        f'<td class="border-t px-4 py-2"></td>'
        f'<td class="border-t px-4 py-2"></td>'
        f"</tr>"
    )
    html.append("</tbody></table></div>")
    return "\n".join(html)


def render_product_cards(product_prices, history):
    from .graph import render_price_history_graph
    html = []
    html.append('<div class="grid gap-8">')
    for name, entries in product_prices.items():
        best = min(entries, key=lambda x: float(x["price"]))
        html.append('<div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">')
        html.append(f'<h2 class="text-2xl font-bold text-cyan-700 mb-4">{name}</h2>')
        html.append(f'<div class="mb-6"><span class="inline-block bg-cyan-50 text-cyan-700 font-semibold px-4 py-2 rounded-lg shadow">Best price: <span class="font-bold">{best["price"]}€</span> @ <a href="{best["url"]}" target="_blank" class="underline">{best["url"]}</a></span></div>')
        html.append('<ul class="mb-6">')
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            html.append(f'<li class="mb-2"><span class="font-bold text-green-600">{norm_price}€</span> @ <a href="{entry["url"]}" target="_blank" class="text-cyan-700 underline">{entry["url"]}</a></li>')
        html.append("</ul>")
        # Add product price graph alongside the card
        html.append('<div class="mt-6">')
        html.append(render_price_history_graph(history, name))
        html.append('</div>')
        history_entries = history[history["Product_Name"] == name]
        if not history_entries.empty:
            html.append('<div class="font-semibold text-slate-700 mb-2">Historique des prix :</div>')
            html.append('<ul class="text-sm text-slate-600">')
            for _, h in history_entries.iterrows():
                timestamp = h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
                if (
                    timestamp is None
                    or (isinstance(timestamp, float) and math.isnan(timestamp))
                    or (isinstance(timestamp, str) and (timestamp.strip() == "" or timestamp.strip().lower() == "nan"))
                ):
                    continue
                norm_price = normalize_price(h["Price"], name)
                if norm_price is None or (isinstance(norm_price, float) and math.isnan(norm_price)):
                    continue
                from datetime import datetime
                def format_french_date(dtstr):
                    try:
                        if "T" in dtstr:
                            dt = datetime.fromisoformat(dtstr.split(".")[0])
                        else:
                            dt = datetime.strptime(dtstr, "%Y-%m-%d %H:%M:%S")
                        months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                        month = months[dt.month - 1]
                        return f"{dt.day} {month} {dt.year}, {dt.hour:02d}:{dt.minute:02d}"
                    except Exception:
                        return dtstr
                ts_fmt = format_french_date(str(timestamp))
                html.append(f'<li class="mb-1">{ts_fmt}: <span class="font-bold text-green-600">{norm_price}€</span> @ <a href="{h["URL"]}" target="_blank" class="text-cyan-700 underline">{h["URL"]}</a></li>')
            html.append("</ul>")
        else:
            html.append('<div class="font-semibold text-slate-700 mb-2">No price history yet.</div>')
        html.append("</div>")
    html.append("</div>")
    return "\n".join(html)
