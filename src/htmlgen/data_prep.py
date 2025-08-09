"""Data preparation utilities for HTML generation (extracted from builder)."""

from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd
from .normalize import normalize_price, get_category


def normalize_and_filter_prices(entries: List[dict], name: str) -> List[dict]:
    ok: List[dict] = []
    for e in entries:
        try:
            norm = normalize_price(e["price"], name)
            val = float(norm)
            if 0 < val < 5000:
                ok.append({"price": norm, "url": e["url"]})
        except Exception:  # pragma: no cover
            continue
    return ok


def compute_category_best(
    product_prices: Dict[str, List[dict]], products_meta: Dict[str, Dict]
) -> Tuple[Dict[str, Dict], Dict[str, List[dict]]]:
    category_best: Dict[str, Dict] = {}
    for name, entries in product_prices.items():
        valid_entries = normalize_and_filter_prices(entries, name)
        if not valid_entries:
            continue
        best = min(valid_entries, key=lambda x: float(x["price"]))
        meta = products_meta.get(name, {})
        cat = meta.get("category") or get_category(name, best["url"])
        if cat == "Upgrade Kit":
            product_prices[name] = valid_entries
            continue
        if cat not in category_best or float(best["price"]) < float(category_best[cat]["price"]):
            category_best[cat] = {"name": name, "price": best["price"], "url": best["url"]}
        product_prices[name] = valid_entries
    return category_best, product_prices


def extract_timestamps(history: pd.DataFrame) -> List[str]:
    # Accept several possible timestamp column names
    if "Timestamp_ISO" in history.columns:
        ts_col = history["Timestamp_ISO"]
    elif "Date" in history.columns:
        ts_col = history["Date"]
    elif "timestamp" in history.columns:  # fallback for raw DataFrame inputs
        ts_col = history["timestamp"]
    else:  # pragma: no cover - unexpected schema
        return []
    return sorted({str(ts) for ts in ts_col if isinstance(ts, str) and ts.strip() and ts != "nan"})


def build_min_series(category_best: Dict[str, Dict], history: pd.DataFrame):
    from dataclasses import dataclass

    @dataclass
    class ProductMinSeries:
        timestamps: List[str]
        prices: List[float]

    result: Dict[str, ProductMinSeries] = {}
    for cat, info in category_best.items():
        name = info["name"]
        ph = history[history["Product_Name"] == name]
        if "Timestamp_ISO" in ph.columns:
            ts_col = "Timestamp_ISO"
        elif "Date" in ph.columns:
            ts_col = "Date"
        elif "timestamp" in ph.columns:
            ts_col = "timestamp"
        else:  # pragma: no cover
            continue
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


def build_total_history(series, timeline: List[str]) -> List[dict]:
    mapped = {name: dict(zip(data.timestamps, data.prices)) for name, data in series.items()}
    absolute_best = {name: (min(p.values()) if p else 0) for name, p in mapped.items()}
    total_history: List[dict] = []
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


__all__ = [
    "compute_category_best",
    "extract_timestamps",
    "build_min_series",
    "build_total_history",
]
