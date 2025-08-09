"""High-level HTML single-file report builder extracted from generate_html.

Initial extraction; not yet integrated into CLI flow. Provides SingleFileHTMLBuilder.build()
that returns the complete HTML string so callers can write it wherever needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
import pandas as pd
from .normalize import normalize_price, get_category
from .render import render_summary_table, render_product_cards
from utils import format_french_date


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

    def normalize_and_filter_prices(self, entries: List[Dict], name: str) -> List[Dict]:
        ok: List[Dict] = []
        for e in entries:
            try:
                norm = normalize_price(e["price"], name)
                val = float(norm)
                if 0 < val < 5000:
                    ok.append({"price": norm, "url": e["url"]})
            except Exception:
                continue
        return ok

    def compute_category_best(
        self, product_prices: Dict[str, List[Dict]], products_meta: Dict[str, Dict]
    ) -> Tuple[Dict[str, Dict], Dict[str, List[Dict]]]:
        category_best: Dict[str, Dict] = {}
        for name, entries in product_prices.items():
            valid_entries = self.normalize_and_filter_prices(entries, name)
            if not valid_entries:
                continue
            best = min(valid_entries, key=lambda x: float(x["price"]))
            meta = products_meta.get(name, {})
            cat = meta.get("category") or get_category(name, best["url"])
            if cat == "Upgrade Kit":
                product_prices[name] = valid_entries
                continue
            if cat not in category_best or float(best["price"]) < float(
                category_best[cat]["price"]
            ):
                category_best[cat] = {"name": name, "price": best["price"], "url": best["url"]}
            product_prices[name] = valid_entries
        return category_best, product_prices

    def extract_timestamps(self, history: pd.DataFrame) -> List[str]:
        ts_col = history["Timestamp_ISO"] if "Timestamp_ISO" in history.columns else history["Date"]
        return sorted(
            {str(ts) for ts in ts_col if isinstance(ts, str) and ts.strip() and ts != "nan"}
        )

    def build_min_series(
        self, category_best: Dict[str, Dict], history: pd.DataFrame
    ) -> Dict[str, ProductMinSeries]:
        result: Dict[str, ProductMinSeries] = {}
        for cat, info in category_best.items():
            name = info["name"]
            ph = history[history["Product_Name"] == name]
            ts_col = "Timestamp_ISO" if "Timestamp_ISO" in ph.columns else "Date"
            ph = ph.sort_values(by=ts_col)
            prices: List[float] = []
            ts_labels: List[str] = []
            for ts, group in ph.groupby(ts_col):
                vals = [
                    float(normalize_price(r.Price, name))
                    for _, r in group.iterrows()
                    if 0 < float(normalize_price(r.Price, name)) < 5000
                ]
                if vals:
                    prices.append(min(vals))
                    ts_labels.append(ts)
            result[name] = ProductMinSeries(ts_labels, prices)
        return result

    def build_total_history(
        self, series: Dict[str, ProductMinSeries], timeline: List[str]
    ) -> List[Dict]:
        mapped = {name: dict(zip(data.timestamps, data.prices)) for name, data in series.items()}
        absolute_best = {name: (min(p.values()) if p else 0) for name, p in mapped.items()}
        total_history: List[Dict] = []
        for i, ts in enumerate(timeline):
            total = 0.0
            for name, ts_prices in mapped.items():
                if i == len(timeline) - 1:
                    total += absolute_best.get(name, 0)
                else:
                    val = ts_prices.get(ts)
                    if val is not None:
                        total += val
            total_history.append({"timestamp": ts, "total": round(total, 2)})
        return total_history

    def _chart_datasets(self, series: Dict[str, ProductMinSeries], total_history: List[Dict]):
        datasets = []
        for idx, (name, data) in enumerate(series.items()):
            if data.timestamps and data.prices:
                datasets.append(
                    {
                        "label": name,
                        "data": data.prices,
                        "fill": False,
                        "borderColor": self.COLOR_PALETTE[idx % len(self.COLOR_PALETTE)],
                        "backgroundColor": self.COLOR_PALETTE[idx % len(self.COLOR_PALETTE)],
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
        category_best, normalized_prices = self.compute_category_best(product_prices, products_meta)
        timeline = self.extract_timestamps(history)
        series = self.build_min_series(category_best, history)
        total_history = self.build_total_history(series, timeline)
        datasets = self._chart_datasets(series, total_history)
        formatted_labels = [format_french_date(x["timestamp"]) for x in total_history]
        chart_config = {
            "type": "line",
            "data": {"labels": formatted_labels, "datasets": datasets},
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
        evo_html = self._evolution_html(total_history)
        name_category = {}
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
            evo_html,
            '<div id="total-warning"></div>',
            '<div class="chart-container mt-8 mb-8"><h2 class="text-2xl font-bold text-center text-cyan-400 mb-6">Historique du prix total</h2><canvas id="total_price_chart" height="150"></canvas>'
            f"<script>const ctx=document.getElementById('total_price_chart').getContext('2d'); new Chart(ctx, {chart_json});</script></div>",
        ]
        html_parts.append(
            render_summary_table(self._build_category_products(normalized_prices), history)
        )
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

    def _build_category_products(self, product_prices: Dict[str, List[Dict]]):
        from collections import defaultdict

        category_products = defaultdict(list)
        for name, entries in product_prices.items():
            for e in entries:
                category_products["Other"].append(
                    {"name": name, "price": e["price"], "url": e["url"]}
                )
        for cat in category_products:
            category_products[cat].sort(key=lambda x: float(x["price"]))
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
