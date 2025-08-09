"""Repository layer abstractions (thin wrappers over DatabaseManager).

This allows higher layers to depend on intention-revealing functions instead of
raw manager methods. Expand gradually.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
from .sqlite import DatabaseManager

# Product read model helpers


def list_products(db: DatabaseManager):
    return db.get_products()


def list_product_urls(db: DatabaseManager, product_name: str):
    return db.get_product_urls(product_name)


# Price history


def record_price(
    db: DatabaseManager,
    product_name: str,
    url: str,
    price: float,
    **meta,
) -> bool:
    return db.add_price_entry(product_name=product_name, url=url, price=price, **meta)


def price_history(db: DatabaseManager, product_name: Optional[str] = None):
    return db.get_price_history(product_name)


# Issues


def unresolved_issues(db: DatabaseManager):
    return db.get_product_issues(resolved=False)


def resolve_issue(db: DatabaseManager, issue_id: int):
    return db.resolve_product_issue(issue_id)


# Maintenance utilities


def auto_handle_critical(db: DatabaseManager, auto_remove: bool = True):
    return db.auto_handle_critical_issues(auto_remove=auto_remove)


# Issue creation / lookup


def log_issue(
    db: DatabaseManager,
    product_id: int,
    url: str,
    issue_type: str,
    **meta,
):
    return db.log_product_issue(product_id=product_id, url=url, issue_type=issue_type, **meta)


def product_by_url(db: DatabaseManager, url: str):
    return db.get_product_by_url(url)


# Scrape planning
def products_needing_scrape(db: DatabaseManager, max_age_hours: int = 48) -> List[Tuple[str, str]]:
    """Return list of (product_name, url) pairs requiring a new scrape.

    Delegates to DatabaseManager.get_products_needing_scrape.
    """
    return db.get_products_needing_scrape(max_age_hours=max_age_hours)
