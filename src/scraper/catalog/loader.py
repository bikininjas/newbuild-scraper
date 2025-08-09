"""Load & sync products.json into database (non-destructive)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List
from database import DatabaseManager
from .validator import validate_products_payload
import logging

LOGGER = logging.getLogger(__name__)


def load_products_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"products json not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def _sync_products(db: DatabaseManager, products: List[Dict[str, Any]]) -> Tuple[int, int]:
    new_products = 0
    new_urls = 0
    existing_products = {p.name: p for p in db.get_products()}
    existing_urls_map = {
        name: {u.url for u in db.get_product_urls(name)} for name in existing_products
    }
    from sqlite3 import IntegrityError

    if db.config.database_type != "sqlite":
        LOGGER.warning("JSON sync currently only implemented for sqlite backend")
    with db._get_connection() as conn:  # type: ignore
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
                current_cat = existing_products[name].category
                if current_cat != category and category:
                    conn.execute("UPDATE products SET category=? WHERE name=?", (category, name))
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
                except IntegrityError:  # pragma: no cover
                    continue
        conn.commit()
    return new_products, new_urls


def import_from_json(db: DatabaseManager, path: str | Path) -> Tuple[int, int]:
    data = load_products_json(path)
    products = validate_products_payload(data)
    return _sync_products(db, products)


__all__ = ["import_from_json", "load_products_json"]
