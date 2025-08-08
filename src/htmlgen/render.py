"""
HTML rendering for summary table, product cards, and graphs.
"""

import sys
import os
import math
import json
import html
import pandas as pd
import numpy as np
from .normalize import normalize_price, get_category, get_site_label
from .constants import EXCLUDED_CATEGORIES
from .graph import render_price_history_graph, render_price_history_graph_from_series
from .price_utils import compute_summary_total
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
    excluded_js = json.dumps(sorted(EXCLUDED_CATEGORIES))
    return f"""
<script id="excluded-categories" type="application/json">{excluded_js}</script>
<script>
    // Categories excluded from total computation (safely parsed from JSON script tag)
    try {{
        var exScript = document.getElementById('excluded-categories');
        window.EXCLUDED_CATEGORIES = JSON.parse(exScript.textContent || '[]');
    }} catch (e) {{
        window.EXCLUDED_CATEGORIES = [];
    }}

    function formatPrice(num) {{
        var n = Number(num);
        if (!isFinite(n)) return '?';
        return n.toFixed(2) + '€';
    }}

    function computeTotal() {{
        var total = 0;
        var rows = document.querySelectorAll('#summary-table tbody tr');
        rows.forEach(function(row) {{
            var cat = row.getAttribute('data-category');
            if (!cat) return; // skip header/total or malformed
            if (Array.isArray(window.EXCLUDED_CATEGORIES) && window.EXCLUDED_CATEGORIES.indexOf(cat) !== -1) return;
            var sel = row.querySelector('select[data-category]');
            if (!sel) return;
            var opt = sel.options[sel.selectedIndex];
            var price = parseFloat(opt && opt.dataset ? opt.dataset.price : 'NaN');
            if (!isNaN(price)) total += price;
        }});
        var el = document.getElementById('total-price-value');
        if (el) el.textContent = formatPrice(total);
    }}

    function switchComponent(category, selectEl) {{
        // Persist selection
        try {{
            var selections = JSON.parse(localStorage.getItem('componentSelections') || '{{}}');
            selections[category] = selectEl.value;
            localStorage.setItem('componentSelections', JSON.stringify(selections));
        }} catch (e) {{ /* ignore */ }}

        // Update row cells from selected option's data-* attributes
        var opt = selectEl.options[selectEl.selectedIndex];
        var row = selectEl.closest('tr');
        if (row && opt && opt.dataset) {{
            var tds = row.querySelectorAll('td');
            // price cell is index 2, site index 3, date index 4
            var price = parseFloat(opt.dataset.price);
            if (tds[2]) tds[2].textContent = formatPrice(price);
            if (tds[3]) {{
                var a = tds[3].querySelector('a');
                if (a) {{ a.href = opt.dataset.url || '#'; a.textContent = opt.dataset.site || a.textContent; }}
            }}
            if (tds[4]) tds[4].textContent = opt.dataset.date || '?';
        }}
        // Recompute total
        computeTotal();
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        // Apply stored selections without reloading
        var selections = {{}};
        try {{ selections = JSON.parse(localStorage.getItem('componentSelections') || '{{}}'); }} catch(e) {{ selections = {{}}; }}
        document.querySelectorAll('select[data-category]').forEach(function(sel) {{
            var cat = sel.getAttribute('data-category');
            var saved = selections && selections[cat];
            if (saved) {{
                for (var i = 0; i < sel.options.length; i++) {{
                    if (sel.options[i].value === saved) {{ sel.selectedIndex = i; break; }}
                }}
                switchComponent(cat, sel);
            }}
        }});
        // Ensure total reflects current selections
        computeTotal();
    }});
</script>
"""


def _find_best_seen_date(history: pd.DataFrame, name: str, url: str, price: float) -> str:
    """Return formatted first-seen date matching the given product/url/price or '?' if none."""
    history_entries = history[(history["Product_Name"] == name) & (history["URL"] == url)]
    if history_entries.empty:
        return "?"
    matched = history_entries.copy()
    matched["Price_float"] = matched["Price"].apply(price_to_float)
    matched = matched[np.isclose(matched["Price_float"], price, atol=0.01)]
    if matched.empty:
        return "?"
    if "Timestamp_ISO" in matched.columns:
        valid_rows = matched[matched["Timestamp_ISO"].notnull() & (matched["Timestamp_ISO"] != "")]
        if not valid_rows.empty:
            best_row = valid_rows.sort_values(by="Timestamp_ISO").iloc[0]
            return format_french_date_full(str(best_row["Timestamp_ISO"]))
    if "Date" in matched.columns:
        valid_rows = matched[matched["Date"].notnull() & (matched["Date"] != "")]
        if not valid_rows.empty:
            best_row = valid_rows.sort_values(by="Date").iloc[0]
            return format_french_date_full(str(best_row["Date"]))
    return "?"


def _render_select_for_products(cat: str, products: list, selected_name: str) -> str:
    options = []
    for p in products:
        sel = " selected" if p["name"] == selected_name else ""
        price = float(p["price"]) if isinstance(p["price"], (int, float, str)) else p["price"]
        # HTML escape user data to prevent XSS
        escaped_name = html.escape(str(p["name"]))
        escaped_url = html.escape(str(p["url"]))
        date = p.get("best_seen", "?")
        site = p.get("site_label", get_site_label(p["url"]))
        escaped_site = html.escape(str(site))

        options.append(
            f'<option value="{escaped_name}" data-price="{price}" data-url="{escaped_url}" data-date="{date}" data-site="{escaped_site}"{sel}>{escaped_name}</option>'
        )
    escaped_cat = html.escape(str(cat))
    return (
        f'<select data-category="{escaped_cat}" onchange="switchComponent(\'{escaped_cat}\', this)">'
        + "".join(options)
        + "</select>"
    )


def _render_summary_row(
    cat: str,
    products: list,
    selected: dict,
    history: pd.DataFrame,
    td_category: str,
    td_product: str,
    td_price: str,
    td_site: str,
    td_date: str,
) -> str:
    name = selected["name"]
    price = float(selected["price"])
    url = selected["url"]
    best_seen = _find_best_seen_date(history, name, url, price)
    # Build enriched options with date and site for client-side switching
    enriched_products = []
    for p in products:
        p_best_seen = _find_best_seen_date(history, p["name"], p["url"], float(p["price"]))
        enriched = dict(p)
        enriched["best_seen"] = p_best_seen
        enriched["site_label"] = get_site_label(p["url"])
        enriched_products.append(enriched)

    row_html = (
        f"<tr data-category='{cat}' class='hover:bg-slate-800/50 transition-colors duration-300'>"
    )
    row_html += td_category.format(cat)
    row_html += td_product.format(_render_select_for_products(cat, enriched_products, name))
    row_html += td_price.format(price)
    row_html += td_site.format(url, get_site_label(url))
    row_html += td_date.format(best_seen)
    row_html += "</tr>"
    return row_html


def render_summary_table(category_products, history, selected_products=None, debug_info=None):
    html = []
    html.append(render_component_switch_js())
    # We'll compute the total at the end using compute_summary_total
    html.append('<div class="overflow-x-auto mb-10">')
    html.append(
        '<table id="summary-table" class="min-w-full glass-card rounded-xl shadow-2xl border border-slate-600 overflow-hidden">'
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
    TD_CATEGORY = '<td class="border-t border-slate-700/50 px-6 py-4 text-slate-300">{}</td>'
    TD_PRODUCT = (
        '<td class="border-t border-slate-700/50 px-6 py-4 text-slate-200 font-medium">{}</td>'
    )
    TD_PRICE = '<td class="border-t border-slate-700/50 px-6 py-4 font-bold text-green-400 text-lg">{:.2f}€</td>'
    TD_SITE = '<td class="border-t border-slate-700/50 px-6 py-4"><a href="{}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors">{}</a></td>'
    TD_DATE = '<td class="border-t border-slate-700/50 px-6 py-4 text-sm text-slate-400">{}</td>'
    for cat, products in category_products.items():
        selected_name = selections.get(cat) if selections else products[0]["name"]
        selected = next((p for p in products if p["name"] == selected_name), products[0])
        html.append(
            _render_summary_row(
                cat,
                products,
                selected,
                history,
                TD_CATEGORY,
                TD_PRODUCT,
                TD_PRICE,
                TD_SITE,
                TD_DATE,
            )
        )
        # Debug info row
        sel_name = selected.get("name")
        if debug_info and (cat, sel_name) in debug_info:
            dbg = debug_info[(cat, sel_name)]
            debug_html = "<tr class='debug-row'><td colspan='5'><div class='debug-info'><strong>Debug:</strong><ul>"
            debug_html += "<li>Raw scraped price: {}€</li>".format(dbg.get("raw_price", "?"))
            debug_html += "<li>Displayed price: {}€</li>".format(dbg.get("displayed_price", "?"))
            if dbg.get("discrepancy"):
                debug_html += "<li><span style='color:red;'>Discrepancy detected!</span></li>"
            debug_html += "<li>Source: <a href='{}' target='_blank'>{}</a></li>".format(
                dbg.get("source_url", "#"), dbg.get("source_url", "#")
            )
            debug_html += "</ul></div></td></tr>"
            html.append(debug_html)
    total_price = compute_summary_total(category_products, selections)
    # Price TD for total includes a stable id for JS updates
    TD_PRICE_TOTAL = '<td id="total-price-value" class="border-t border-slate-700/50 px-6 py-4 font-bold text-green-400 text-lg">{:.2f}€</td>'
    html.append(
        "<tr id='total-row' class='bg-slate-900/80 font-bold border-t-2 border-cyan-500/30'>"
        + TD_CATEGORY.format("💰 Total")
        + TD_EMPTY
        + TD_PRICE_TOTAL.format(total_price)
        + TD_EMPTY
        + TD_EMPTY
        + "</tr>"
    )
    html.append("</tbody></table></div>")
    # Clarify that some categories are excluded from the total
    if EXCLUDED_CATEGORIES:
        html.append(
            '<div class="text-sm text-yellow-300/80 mt-2">\n'
            + " ".join(
                [
                    f"⚠️ {cat} non inclus dans le total (alternative aux composants)."
                    for cat in sorted(EXCLUDED_CATEGORIES)
                ]
            )
            + "</div>"
        )
    return "\n".join(html)


def _should_skip_timestamp(timestamp) -> bool:
    if (
        timestamp is None
        or (isinstance(timestamp, float) and math.isnan(timestamp))
        or (
            isinstance(timestamp, str)
            and (timestamp.strip() == "" or timestamp.strip().lower() == "nan")
        )
    ):
        return True
    return False


def _render_price_list(entries, name: str) -> str:
    items = []
    for entry in entries:
        norm_price = normalize_price(entry["price"], name)
        items.append(
            '<li class="price-item p-4 rounded-xl transition-all duration-300">'
            f'<span class="font-bold text-green-400 text-lg">{norm_price}€</span> @ '
            f'<a href="{entry["url"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(entry["url"])}</a>'
            "</li>"
        )
    return '<ul class="mb-6 space-y-3">' + "".join(items) + "</ul>"


def _render_history_list(history_entries: pd.DataFrame, name: str) -> str:
    lis = []
    for _, h in history_entries.iterrows():
        timestamp = h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
        if _should_skip_timestamp(timestamp):
            continue
        norm_price = normalize_price(h["Price"], name)
        if norm_price is None or (isinstance(norm_price, float) and math.isnan(norm_price)):
            continue
        ts_fmt = format_french_date_full(str(timestamp))
        lis.append(
            f'<li class="history-item mb-2 p-3 rounded-xl transition-all duration-300">{ts_fmt}: '
            f'<span class="font-bold text-green-400">{norm_price}€</span> @ '
            f'<a href="{h["URL"]}" target="_blank" class="text-cyan-400 hover:text-cyan-300 underline transition-colors ml-2">{get_site_label(h["URL"])}</a>'
            "</li>"
        )
    return '<ul class="text-sm text-slate-400 space-y-3">' + "".join(lis) + "</ul>"


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
        html.append(_render_price_list(entries, name))
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
            html.append(_render_history_list(history_entries, name))
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
