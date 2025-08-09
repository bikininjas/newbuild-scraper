"""
Price-related helpers used by HTML rendering and tests.
"""

from .constants import EXCLUDED_CATEGORIES


def compute_summary_total(category_products, selections=None) -> float:
    """Compute the total price from category_products excluding EXCLUDED_CATEGORIES.

    Inputs:
    - category_products: dict[str, list[dict{name, price, url}]]
    - selections: optional dict[category -> product name]

    Returns: float rounded to 2 decimals
    """
    selections = selections or {}
    total = 0.0
    for cat, products in category_products.items():
        if not products:
            continue
        selected_name = selections.get(cat) if selections else products[0]["name"]
        selected = next((p for p in products if p["name"] == selected_name), products[0])
        raw_price = selected.get("price")
        if isinstance(raw_price, (int, float)):
            price = float(raw_price)
        else:
            s = str(raw_price).replace("€", "").replace(",", ".").replace(" ", "").strip()
            try:
                price = float(s)
            except Exception:  # pragma: no cover - fallback
                continue  # skip unparsable price
        if cat not in EXCLUDED_CATEGORIES:
            total += price
    return round(total, 2)
