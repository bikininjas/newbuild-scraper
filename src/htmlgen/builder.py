"""High-level HTML single-file report builder extracted from generate_html.

Initial extraction; not yet integrated into CLI flow. Provides SingleFileHTMLBuilder.build()
that returns the complete HTML string so callers can write it wherever needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import pandas as pd
from .render import (
    render_summary_table,
    render_product_cards,
    render_upgrade_kits_table,
)
from .data_prep import (
    compute_category_best,
    extract_timestamps,
    build_min_series,
    build_total_history,
)
from .chart_config import chart_config_json
from .constants import EXCLUDED_CATEGORIES


@dataclass
class ProductMinSeries:
    timestamps: List[str]
    prices: List[float]


class SingleFileHTMLBuilder:
    COLOR_PALETTE = [
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

    # Data prep logic is now in htmlgen.data_prep

    def _evolution_html(self, total_history: List[Dict]) -> str:
        if len(total_history) < 2:
            return ""
        prev = total_history[-2]["total"]
        curr = total_history[-1]["total"]
        diff = round(curr - prev, 2)
        if diff == 0:
            return '<div class="text-center text-slate-400 font-semibold mb-4 text-lg">📊 Aucune évolution</div>'
        if diff < 0:
            return f'<div class="text-center text-green-400 font-semibold mb-4 text-lg">📈 ▼ -{abs(diff):.2f}€ (moins cher)</div>'
        return f'<div class="text-center text-red-400 font-semibold mb-4 text-lg">📉 ▲ +{diff:.2f}€ (plus cher)</div>'

    def build(
        self,
        product_prices: Dict[str, List[Dict]],
        history: pd.DataFrame,
        products_meta: Dict[str, Dict],
    ) -> str:
        # Fallback: ensure every product present by reconstructing last known prices from history
        try:
            if history is not None and not history.empty:
                for name, meta in products_meta.items():
                    if name not in product_prices or not product_prices.get(name):
                        ph = history[history["Product_Name"] == name]
                        if ph.empty:
                            continue
                        latest_entries = []
                        # Choose the most recent timestamp column available
                        ts_col = None
                        for c in ["Timestamp_ISO", "Date", "timestamp"]:
                            if c in ph.columns:
                                ts_col = c
                                break
                        if ts_col is not None:
                            ph = ph.sort_values(by=ts_col)
                        for url, g in ph.groupby("URL"):
                            last_row = g.iloc[-1]
                            latest_entries.append({"price": last_row["Price"], "url": url})
                        if latest_entries:
                            product_prices[name] = latest_entries
        except Exception:
            # Non-fatal: continue with whatever data we have
            pass
        # ----- Normal build pipeline -----
        category_best, normalized_prices = compute_category_best(product_prices, products_meta)
        timeline = extract_timestamps(history)
        series = build_min_series(category_best, history)
        total_history = build_total_history(series, timeline)
        chart_json = chart_config_json(series, total_history, self.COLOR_PALETTE)

        evo_html = self._evolution_html(total_history)
        name_category: Dict[str, Dict] = {}
        for cat, info in category_best.items():
            name_category[info["name"]] = {"category": cat}
        for name, meta in products_meta.items():
            if name not in name_category:
                name_category[name] = {"category": meta.get("category", "Other")}

        html_parts = [
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
            "    .chart-container { background: rgba(15, 23, 42, 0.95) !important; border-radius: 16px; padding: 20px; border: 1px solid rgba(51, 65, 85, 0.3); }",
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
            evo_html,
            '<div id="total-warning"></div>',
            '<div class="chart-container mt-8 mb-8 max-w-5xl mx-auto"><h2 class="text-2xl font-bold text-center text-cyan-400 mb-4">Historique du prix total</h2><canvas id="total_price_chart" height="120"></canvas>'
            f"<script>const ctx=document.getElementById('total_price_chart').getContext('2d'); new Chart(ctx, {chart_json});</script></div>",
        ]

        # Build category products excluding explicitly excluded categories (e.g. Upgrade Kit)
        category_products_all = self._build_category_products(normalized_prices, name_category)
        category_products = {
            k: v for k, v in category_products_all.items() if k not in EXCLUDED_CATEGORIES
        }
        html_parts.append(render_summary_table(category_products, history))

        # Upgrade Kits: build separate multi-line price history graph if present
        upgrade_kits = [
            name for name, meta in name_category.items() if meta.get("category") == "Upgrade Kit"
        ]
        if upgrade_kits:
            # Compact table first (not part of totals)
            html_parts.append(render_upgrade_kits_table(upgrade_kits, normalized_prices, history))
            upgrade_chart_html = self._render_upgrade_kits_section(upgrade_kits, history)
            if upgrade_chart_html:
                html_parts.append(upgrade_chart_html)
        html_parts.append(
            render_product_cards(
                normalized_prices,
                history,
                {
                    name: {"timestamps": s.timestamps, "prices": s.prices}
                    for name, s in series.items()
                },
                products_meta=name_category,
            )
        )
        html_parts.append(self._toggle_history_js())
        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def _render_upgrade_kits_section(self, upgrade_kits: List[str], history: pd.DataFrame) -> str:
        """Render a dedicated chart for upgrade kit products (excluded from main total/table)."""
        if history is None or history.empty:
            return ""
        # Collect min price per timestamp for each upgrade kit
        # Determine timestamp column
        ts_col = None
        for c in ["Timestamp_ISO", "Date", "timestamp"]:
            if c in history.columns:
                ts_col = c
                break
        if ts_col is None:
            return ""
        kit_series = {}
        palette = self.COLOR_PALETTE * 3  # extend if many kits
        for kit in upgrade_kits:
            ph = history[history["Product_Name"] == kit]
            if ph.empty:
                continue
            ph = ph.sort_values(by=ts_col)
            prices_map = {}
            for ts, g in ph.groupby(ts_col):
                vals = []
                for _, r in g.iterrows():
                    raw = r.Price
                    if isinstance(raw, str):
                        raw = raw.replace("€", "").replace(",", ".").replace(" ", "").strip()
                    try:
                        f = float(raw)
                        if 0 < f < 10000:
                            vals.append(f)
                    except Exception:  # pragma: no cover
                        continue
                if vals:
                    prices_map[str(ts)] = min(vals)
            if prices_map:
                kit_series[kit] = prices_map
        if not kit_series:
            return ""
        # Unified sorted timestamps
        all_ts = sorted({ts for pm in kit_series.values() for ts in pm.keys()})
        datasets = []
        for idx, (kit, pm) in enumerate(kit_series.items()):
            data_points = [pm.get(ts, None) for ts in all_ts]
            # If only a single timestamp, ensure the point is visible
            pt_radius = 3 if len([d for d in data_points if d is not None]) <= 1 else 0
            color = palette[idx]
            datasets.append(
                {
                    "label": kit,
                    "data": data_points,
                    "fill": False,
                    "borderColor": color,
                    "backgroundColor": color,
                    "borderWidth": 2,
                    "tension": 0.4,
                    "pointRadius": pt_radius,
                    "pointHoverRadius": max(pt_radius, 4),
                }
            )
        import json

        chart_conf = {
            "type": "line",
            "data": {"labels": all_ts, "datasets": datasets},
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {
                        "display": True,
                        "labels": {"color": "#e2e8f0", "font": {"size": 12}},
                    },
                    "title": {
                        "display": True,
                        "text": "Upgrade Kits - Historique des prix",
                        "color": "#fbbf24",
                        "font": {"size": 16, "weight": "bold"},
                    },
                },
                "scales": {
                    "x": {
                        "ticks": {"color": "#94a3b8", "font": {"size": 10}},
                        "grid": {"color": "rgba(148,163,184,0.1)"},
                    },
                    "y": {
                        "beginAtZero": False,
                        "ticks": {"color": "#94a3b8", "font": {"size": 10}},
                        "grid": {"color": "rgba(148,163,184,0.1)"},
                    },
                },
                "elements": {"point": {"hoverBackgroundColor": "#fbbf24"}},
            },
        }
        return (
            '<div class="chart-container mt-12 mb-12">'
            '<h2 class="text-2xl font-bold text-center text-yellow-400 mb-6">Upgrade Kits (séparés)</h2>'
            '<canvas id="upgrade_kits_chart" height="160"></canvas>'
            f"<script>new Chart(document.getElementById('upgrade_kits_chart').getContext('2d'), {json.dumps(chart_conf)});</script>"
            "</div>"
        )

    def _build_category_products(
        self, product_prices: Dict[str, List[Dict]], name_category: Dict[str, Dict]
    ):
        from collections import defaultdict

        category_products = defaultdict(list)
        for name, entries in product_prices.items():
            cat = name_category.get(name, {}).get("category", "Other") if name_category else "Other"
            for e in entries:
                category_products[cat].append({"name": name, "price": e["price"], "url": e["url"]})

        # Robust sort: handle prices that might still carry a trailing euro sign or spacing
        def _price_to_float(val):
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                s = val.replace("€", "").replace(",", ".").replace(" ", "").strip()
                try:
                    return float(s)
                except Exception:  # pragma: no cover - fallback path
                    return float("inf")  # push unparsable prices to the end
            return float("inf")

        for cat in category_products:
            category_products[cat].sort(key=lambda x: _price_to_float(x["price"]))
        return category_products

    def _toggle_history_js(self) -> str:
        return """
<script>
function toggleHistory(historyId){
 const d=document.getElementById(historyId); if(!d) return; const icon=document.getElementById('icon-'+historyId); const btn=icon?icon.parentElement:null;
 if(d.classList.contains('hidden')){d.classList.remove('hidden'); if(icon) icon.style.transform='rotate(180deg)'; if(btn){const tn=[...btn.childNodes].find(n=>n.nodeType===3&&n.textContent.includes('Afficher')); if(tn) tn.textContent=\"Masquer l'historique des prix\";}}
 else {d.classList.add('hidden'); if(icon) icon.style.transform='rotate(0deg)'; if(btn){const tn=[...btn.childNodes].find(n=>n.nodeType===3&&n.textContent.includes('Masquer')); if(tn) tn.textContent=\"Afficher l'historique des prix\";}}
}
</script>
"""


__all__ = ["SingleFileHTMLBuilder"]
