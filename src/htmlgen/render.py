"""
Product Recommendations (for easier user integration):

Mouse:
    - Logitech G G502 X LIGHTSPEED
    - Razer DeathAdder V3 Pro
    - Corsair M65 RGB Ultra

Keyboard:
    - Corsair K70 CORE RGB
    - Logitech G Pro X
    - Keychron K8 Pro

Power Supply:
    - MSI MAG A850GL PCIE5 850W
    - Corsair RM850x Shift
    - Seasonic Focus GX-850

Memory (DDR5):
    - Patriot Viper Venom RGB DDR5 64 Go (2x32 Go) 6000MT/s CL30
    - Kingston Fury Beast DDR5 64 Go (2x32 Go) 6000MT/s CL30
    - Corsair Vengeance DDR5 64 Go (2x32 Go) 6000MT/s CL30

NVMe PCIe 5 SSD:
    - Crucial P510 SSD 1To PCIe 5.0 x4 Gen5 NVMe M.2
    - Samsung 990 Pro PCIe 5.0 NVMe M.2
    - WD Black SN850X PCIe 5.0 NVMe M.2
"""

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
from utils import format_french_date_full


def price_to_float(x):
    s = str(x).replace(",", ".").replace("€", "").strip().replace(" ", "")
    if s in ["", "nan"]:
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan


# Add JS for switching components (vanilla JS, maximum compatibility)
def render_component_switch_js():
    return """<script>
    function switchComponent(category, productName) {
        // Store selection in localStorage for persistence
        var selections = JSON.parse(localStorage.getItem('componentSelections') || '{}');
        selections[category] = productName;
        localStorage.setItem('componentSelections', JSON.stringify(selections));
        // Reload page to update table (simple, compatible)
        location.reload();
    }
    </script>"""


def render_summary_table(
    category_products, history, selected_products=None, debug_info=None
):
    html = []
    html.append(render_component_switch_js())
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
    selections = selected_products or {}
    TD_EMPTY = '<td class="border-t border-slate-700/50 px-6 py-5"></td>'
    TD_CATEGORY = (
        '<td class="border-t border-slate-700/50 px-6 py-4 text-slate-300">{}</td>'
    )
    TD_PRODUCT = '<td class="border-t border-slate-700/50 px-6 py-4 text-slate-200 font-medium">{}</td>'
    TD_PRICE = '<td class="border-t border-slate-700/50 px-6 py-4 font-bold text-green-400 text-lg">{:.2f}€</td>'
    TD_SITE = '<td class="border-t border-slate-700/50 px-6 py-4"><a href="{}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors">{}</a></td>'
    TD_DATE = '<td class="border-t border-slate-700/50 px-6 py-4 text-sm text-slate-400">{}</td>'
    for cat, products in category_products.items():
        selected_name = selections.get(cat) if selections else products[0]["name"]
        selected = next(
            (p for p in products if p["name"] == selected_name), products[0]
        )
        name = selected["name"]
        price = float(selected["price"])
        url = selected["url"]
        total_price += price
        # Find all history entries for this product and URL
        history_entries = history[
            (history["Product_Name"] == name) & (history["URL"] == url)
        ]
        matched = history_entries.copy()
        matched["Price_float"] = matched["Price"].apply(price_to_float)
        matched = matched[np.isclose(matched["Price_float"], price, atol=0.01)]
        best_seen = "?"
        if not matched.empty:
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
        # site_label variable removed (was unused)
        row_html = "<tr class='hover:bg-slate-800/50 transition-colors duration-300'>"
        row_html += TD_CATEGORY.format(cat)
        row_html += TD_PRODUCT.format(
            "<select onchange=\"switchComponent('"
            + cat
            + "', this.value)\">"
            + "".join(
                [
                    '<option value="'
                    + p["name"]
                    + '"'
                    + (" selected" if p["name"] == name else "")
                    + ">"
                    + p["name"]
                    + "</option>"
                    for p in products
                ]
            )
            + "</select>"
        )
        row_html += TD_PRICE.format(price)
        row_html += TD_SITE.format(url, get_site_label(url))
        row_html += TD_DATE.format(best_seen)
        row_html += "</tr>"
        html.append(row_html)
        # Debug info row
        if debug_info and (cat, name) in debug_info:
            dbg = debug_info[(cat, name)]
            debug_html = "<tr class='debug-row'><td colspan='5'><div class='debug-info'><strong>Debug:</strong><ul>"
            debug_html += "<li>Raw scraped price: {}€</li>".format(
                dbg.get("raw_price", "?")
            )
            debug_html += "<li>Displayed price: {}€</li>".format(
                dbg.get("displayed_price", "?")
            )
            if dbg.get("discrepancy"):
                debug_html += (
                    "<li><span style='color:red;'>Discrepancy detected!</span></li>"
                )
            debug_html += "<li>Source: <a href='{}' target='_blank'>{}</a></li>".format(
                dbg.get("source_url", "#"), dbg.get("source_url", "#")
            )
            debug_html += "</ul></div></td></tr>"
            html.append(debug_html)
    html.append(
        "<tr class='bg-slate-900/80 font-bold border-t-2 border-cyan-500/30'>"
        + TD_CATEGORY.format("💰 Total")
        + TD_EMPTY
        + TD_PRICE.format(total_price)
        + TD_EMPTY
        + TD_EMPTY
        + "</tr>"
    )
    html.append("</tbody></table></div>")
    return "\n".join(html)


def render_product_cards(product_prices, history, product_min_prices):
    from .data import load_products

    DIV_END = "</div>"
    html = []
    html.append('<div class="grid gap-8">')

    # Load products data to get categories
    products_data = load_products("produits.csv")

    for name, entries in product_prices.items():
        # Get category for this product
        product_data = products_data.get(name, {})
        category = product_data.get("category", "Other")

        min_price_data = product_min_prices.get(name, {"timestamps": [], "prices": []})
        best = min(entries, key=lambda x: float(x["price"]))
        history_id = f"history-{abs(hash(name))}"
        html.append(
            '<div class="glass-card rounded-2xl shadow-2xl border border-slate-600 p-8 hover:shadow-cyan-500/10 transition-all duration-300">'
        )

        # Add special styling for Upgrade Kit items
        if category == "Upgrade Kit":
            html.append(
                '<div class="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 mb-4">'
                '<div class="flex items-center gap-2 text-yellow-400 font-semibold mb-2">'
                "⚠️ Kit d'Upgrade - Alternative</div>"
                '<div class="text-sm text-yellow-200/80">'
                "Ce kit est une alternative à l'achat des composants individuels. "
                "Il n'est pas inclus dans le calcul du prix total."
                "</div></div>"
            )

        html.append(
            f'<h2 class="text-2xl font-bold text-cyan-400 mb-4 flex items-center gap-2">🔥 {name}</h2>'
        )
        html.append(
            '<div class="mb-6">'
            f'<span class="inline-block price-badge text-white font-semibold px-6 py-3 rounded-xl shadow-lg">'
            f'💎 Meilleur prix: <span class="font-bold text-xl">{best["price"]}€</span> @ '
            f'<a href="{best["url"]}" target="_blank" class="underline hover:text-slate-200 transition-colors">{get_site_label(best["url"])}</a>'
            "</span></div>"
        )
        html.append('<ul class="mb-6 space-y-3">')
        for entry in entries:
            norm_price = normalize_price(entry["price"], name)
        html.append(
            '<li class="price-item p-4 rounded-xl transition-all duration-300">'
            f'<span class="font-bold text-green-400 text-lg">{norm_price}€</span> @ '
            f'<a href="{entry["url"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(entry["url"])}</a>'
            "</li>"
        )
        html.append("</ul>")
        html.append('<div class="mt-6">')
        html.append(
            render_price_history_graph_from_series(
                min_price_data["timestamps"], min_price_data["prices"], name
            )
        )
        html.append(DIV_END)
        history_entries = history[history["Product_Name"] == name]
        if not history_entries.empty:
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
                ts_fmt = format_french_date_full(str(timestamp))
                html.append(
                    f'<li class="history-item mb-2 p-3 rounded-xl transition-all duration-300">'
                    f'{ts_fmt}: <span class="font-bold text-green-400">{norm_price}€</span> @ '
                    f'<a href="{h["URL"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(h["URL"])}</a>'
                    "</li>"
                )
            html.append("</ul>")
            html.append(DIV_END)
        else:
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
        html.append(DIV_END)
    html.append(DIV_END)
    return "\n".join(html)


def group_products_by_category(products):
    """Group a list of product dicts by their 'category' field."""
    from collections import defaultdict

    grouped = defaultdict(list)
    for p in products:
        cat = p.get("category", "Other")
        grouped[cat].append(p)
    return dict(grouped)
