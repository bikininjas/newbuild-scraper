"""JSON-based product import (replacement for CSV loader).

Responsibilities:
- Load products.json structure
- Validate schema minimally
- Import (sync) into existing SQLite DB without wiping data

JSON format (version 1):
{
  "version": 1,
  "products": [
    {"name": "Product A", "category": "CPU", "urls": ["https://..."]},
    ...
  ]
}
"""

from __future__ import annotations
import json, logging, re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from database import DatabaseManager

LOGGER = logging.getLogger(__name__)

RE_URL = re.compile(r"^https?://")


class ProductValidationError(Exception):
    pass


def load_products_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"products json not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def validate_products_payload(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        raise ProductValidationError("Root must be an object")
    if data.get("version") != 1:
        raise ProductValidationError("Unsupported or missing version (expected 1)")
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ProductValidationError("'products' must be a non-empty list")
    seen = set()
    normed: List[Dict[str, Any]] = []
    for idx, entry in enumerate(products):
        if not isinstance(entry, dict):
            raise ProductValidationError(f"Product at index {idx} is not an object")
        name = str(entry.get("name", "")).strip()
        category = str(entry.get("category", "Other")).strip() or "Other"
        urls = entry.get("urls")
        if not name:
            raise ProductValidationError(f"Product at index {idx} missing name")
        if name in seen:
            raise ProductValidationError(f"Duplicate product name: {name}")
        if not isinstance(urls, list) or not urls:
            raise ProductValidationError(f"Product '{name}' must have a non-empty 'urls' list")
        clean_urls = []
        for u in urls:
            su = str(u).strip()
            if not RE_URL.search(su):
                raise ProductValidationError(f"Product '{name}' has invalid url: {su}")
            clean_urls.append(su)
        normed.append({"name": name, "category": category, "urls": clean_urls})
        seen.add(name)
    return normed


def sync_products(db: DatabaseManager, products: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Insert products / urls that do not yet exist. Do not delete existing rows.
    Returns (new_products, new_urls)."""
    new_products = 0
    new_urls = 0
    # Build existing product->urls map
    existing_products = {p.name: p for p in db.get_products()}
    existing_urls_map = {
        name: {u.url for u in db.get_product_urls(name)} for name in existing_products
    }
    from sqlite3 import IntegrityError

    if db.config.database_type != "sqlite":
        LOGGER.warning("JSON sync currently only implemented for sqlite backend")
    # Direct SQL for efficiency
    with db._get_connection() as conn:  # type: ignore (private usage ok within same project)
        for prod in products:
            name = prod["name"]
            category = prod["category"]
            urls = prod["urls"]
            if name not in existing_products:
                conn.execute(
                    "INSERT INTO products (name, category) VALUES (?, ?)", (name, category)
                )
                new_products += 1
            else:
                # Optionally update category if changed
                current_cat = existing_products[name].category
                if current_cat != category and category:
                    conn.execute("UPDATE products SET category=? WHERE name=?", (category, name))
            # Get product id
            pid = conn.execute("SELECT id FROM products WHERE name=?", (name,)).fetchone()[0]
            for url in urls:
                if url in existing_urls_map.get(name, set()):
                    continue
                site_name = db._extract_site_name(url)  # type: ignore
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO urls (product_id, url, site_name, active) VALUES (?,?,?,1)",
                        (pid, url, site_name),
                    )
                    if url not in existing_urls_map.get(name, set()):
                        new_urls += 1
                except IntegrityError:
                    continue
        conn.commit()
    return new_products, new_urls


def import_from_json(db: DatabaseManager, path: str | Path) -> Tuple[int, int]:
    data = load_products_json(path)
    products = validate_products_payload(data)
    return sync_products(db, products)


__all__ = [
    "ProductValidationError",
    "load_products_json",
    "validate_products_payload",
    "sync_products",
    "import_from_json",
]
