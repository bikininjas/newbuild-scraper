"""
HTML rendering for summary table, product cards, and graphs.
"""

import sys
import os
import math
import pandas as pd
import numpy as np
from .normalize import normalize_price, get_category, get_site_label
from .graph import render_price_history_graph, render_price_history_graph_from_series
from ..utils import format_french_date_full


def render_summary_table(category_best, history):
    html = []
    total_price = 0
    html.append('<div class="overflow-x-auto mb-10">')
    html.append(
        '<table class="min-w-full glass-card rounded-xl shadow-2xl border border-slate-600 overflow-hidden">'
    )
    html.append(
        "<thead><tr>"
        '<th class="px-6 py-4 text-left text-sm font-semibold text-slate-200 bg-slate-900/70">Catégorie</th>'
        '<th class="px-6 py-4 text-left text-sm font-semibold text-slate-200 bg-slate-900/70">Produit</th>'
        '<th class="px-6 py-4 text-left text-sm font-semibold text-slate-200 bg-slate-900/70">Meilleur Prix</th>'
        '<th class="px-6 py-4 text-left text-sm font-semibold text-slate-200 bg-slate-900/70">Meilleur Site</th>'
        '<th class="px-6 py-4 text-left text-sm font-semibold text-slate-200 bg-slate-900/70">Vu Le</th>'
        "</tr></thead><tbody>"
    )
    
    for cat, info in category_best.items():
        name = info["name"]
        price = float(info["price"])
        url = info["url"]
        total_price += price
        # Find all history entries for this product and URL
        history_entries = history[
            (history["Product_Name"] == name) & (history["URL"] == url)
        ]
        # Match normalized price with a tolerance
        matched = history_entries.copy()
        matched["Price_float"] = matched["Price"].apply(
            lambda x: (
                float(x)
                if str(x).replace(",", ".").replace("€", "").strip().replace(" ", "")
                not in ["", "nan"]
                else np.nan
            )
        )
        matched = matched[np.isclose(matched["Price_float"], price, atol=0.01)]
        best_seen = "?"
        if not matched.empty:
            # Find the earliest timestamp for the best price
            if "Timestamp_ISO" in matched.columns:
                valid_rows = matched[
                    matched["Timestamp_ISO"].notnull()
                    & (matched["Timestamp_ISO"] != "")
                ]
                if not valid_rows.empty:
                    best_row = valid_rows.sort_values(by="Timestamp_ISO").iloc[0]
                    best_seen = format_french_date_full(str(best_row["Timestamp_ISO"]))
            elif "Date" in matched.columns:
                valid_rows = matched[
                    matched["Date"].notnull() & (matched["Date"] != "")
                ]
                if not valid_rows.empty:
                    best_row = valid_rows.sort_values(by="Date").iloc[0]
                    best_seen = format_french_date_full(str(best_row["Date"]))
        site_label = get_site_label(url)
        # Evolution indicator
        evolution_html = ""
        product_history = history[history["Product_Name"] == name]
        ts_col = (
            "Timestamp_ISO" if "Timestamp_ISO" in product_history.columns else "Date"
        )
        product_history = product_history.sort_values(by=ts_col)
        grouped = product_history.groupby(ts_col)
        best_prices = []
        for ts, group in grouped:
            norm_prices = [
                float(normalize_price(p, name))
                for p in group["Price"]
                if p is not None and str(p).strip() != "" and str(p).lower() != "nan"
            ]
            valid_prices = [p for p in norm_prices if p > 0 and p < 5000]
            if valid_prices:
                min_price = min(valid_prices)
                best_prices.append(min_price)
        if len(best_prices) >= 2:
            if best_prices[-1] < best_prices[-2]:
                evolution_html = (
                    '<span class="text-green-400 ml-2 font-semibold">↓</span>'
                )
            elif best_prices[-1] > best_prices[-2]:
                evolution_html = (
                    '<span class="text-red-400 ml-2 font-semibold">↑</span>'
                )
            else:
                evolution_html = '<span class="text-slate-400 ml-2">–</span>'
        html.append(
            f"<tr class='hover:bg-slate-800/50 transition-colors duration-300'>"
            f'<td class="border-t border-slate-700/50 px-6 py-4 text-slate-300">{cat}</td>'
            f'<td class="border-t border-slate-700/50 px-6 py-4 text-slate-200 font-medium">{name}</td>'
            f'<td class="border-t border-slate-700/50 px-6 py-4 font-bold text-green-400 text-lg">{price:.2f}€{evolution_html}</td>'
            f'<td class="border-t border-slate-700/50 px-6 py-4"><a href="{url}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors">{site_label}</a></td>'
            f'<td class="border-t border-slate-700/50 px-6 py-4 text-sm text-slate-400">{best_seen}</td>'
            f"</tr>"
        )
    html.append(
        f"<tr class='bg-slate-900/80 font-bold border-t-2 border-cyan-500/30'>"
        f'<td class="border-t border-slate-700/50 px-6 py-5 font-bold text-slate-100 text-lg">💰 Total</td>'
        f'<td class="border-t border-slate-700/50 px-6 py-5"></td>'
        f'<td class="border-t border-slate-700/50 px-6 py-5 font-bold text-2xl price-badge text-white rounded-lg px-4 py-2">{total_price:.2f}€</td>'
        f'<td class="border-t border-slate-700/50 px-6 py-5"></td>'
        f'<td class="border-t border-slate-700/50 px-6 py-5"></td>'
        f"</tr>"
    )
    html.append("</tbody></table></div>")
    return "\n".join(html)


def render_product_cards(
    product_prices, history, product_min_prices
):
    html = []
    html.append('<div class="grid gap-8">')
    for name, entries in product_prices.items():
        min_price_data = product_min_prices.get(name, {"timestamps": [], "prices": []})
        best = min(entries, key=lambda x: float(x["price"]))
        # Create a unique ID for this product's history section
        history_id = f"history-{abs(hash(name))}"

        html.append(
            '<div class="glass-card rounded-2xl shadow-2xl border border-slate-600 p-8 hover:shadow-cyan-500/10 transition-all duration-300">'
        )
        html.append(
            f'<h2 class="text-2xl font-bold text-cyan-400 mb-4 flex items-center gap-2">🔥 {name}</h2>'
        )
        html.append(
            f'<div class="mb-6"><span class="inline-block price-badge text-white font-semibold px-6 py-3 rounded-xl shadow-lg">💎 Meilleur prix: <span class="font-bold text-xl">{best["price"]}€</span> @ <a href="{best["url"]}" target="_blank" class="underline hover:text-slate-200 transition-colors">{get_site_label(best["url"])}</a></span></div>'
        )
        html.append('<ul class="mb-6 space-y-3">')
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
            html.append(
                f'<li class="price-item p-4 rounded-xl transition-all duration-300"><span class="font-bold text-green-400 text-lg">{norm_price}€</span> @ <a href="{entry["url"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(entry["url"])}</a></li>'
            )
        html.append("</ul>")
        # Always add product price graph, even if there are no data points
        html.append('<div class="mt-6">')
        
        html.append(
            render_price_history_graph_from_series(
                min_price_data["timestamps"], min_price_data["prices"], name
            )
        )
        html.append("</div>")

        # Always include historical prices section but make it toggleable
        history_entries = history[history["Product_Name"] == name]
        if not history_entries.empty:
            # Add toggle button for historical prices
            html.append(
                f'<button onclick="toggleHistory(\'{history_id}\')" class="toggle-btn mb-4 px-6 py-3 text-white text-sm font-medium rounded-xl transition-all duration-300 flex items-center gap-3 shadow-lg hover:shadow-xl">'
            )
            html.append(
                '<svg class="w-5 h-5 transition-transform duration-300" id="icon-'
                + history_id
                + '" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            )
            html.append(
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>'
            )
            html.append("</svg>")
            html.append("📊 Afficher l'historique des prix")
            html.append("</button>")

            # Historical prices section - hidden by default
            html.append(f'<div id="{history_id}" class="historical-prices hidden">')
            html.append(
                '<div class="font-semibold text-slate-300 mb-3 text-lg flex items-center gap-2">📈 Historique des prix :</div>'
            )
            html.append('<ul class="text-sm text-slate-400 space-y-3">')
            for _, h in history_entries.iterrows():
                timestamp = (
                    h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
                )
                if (
                    timestamp is None
                    or (isinstance(timestamp, float) and math.isnan(timestamp))
                    or (
                        isinstance(timestamp, str)
                        and (
                            timestamp.strip() == ""
                            or timestamp.strip().lower() == "nan"
                        )
                    )
                ):
                    continue
                norm_price = normalize_price(h["Price"], name)
                if norm_price is None or (
                    isinstance(norm_price, float) and math.isnan(norm_price)
                ):
                    continue
                
                # Use shared French date formatting function
                ts_fmt = format_french_date_full(str(timestamp))
                html.append(
                    f'<li class="history-item mb-2 p-3 rounded-xl transition-all duration-300">{ts_fmt}: <span class="font-bold text-green-400">{norm_price}€</span> @ <a href="{h["URL"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(h["URL"])}</a></li>'
                )
            html.append("</ul>")
            html.append("</div>")  # End historical prices section
        else:
            # Still show button even if no history, but disabled
            html.append(
                '<button disabled class="mb-4 px-6 py-3 bg-slate-800/70 text-slate-500 text-sm rounded-xl cursor-not-allowed flex items-center gap-3 opacity-60 border border-slate-700/50">'
            )
            html.append(
                '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            )
            html.append(
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>'
            )
            html.append("</svg>")
            html.append("❌ Aucun historique disponible")
            html.append("</button>")
        html.append("</div>")
    html.append("</div>")
    return "\n".join(html)
