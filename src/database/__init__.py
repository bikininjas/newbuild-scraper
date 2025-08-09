"""Legacy database package.

Deprecated: DatabaseManager now lives in scraper.persistence.sqlite.
This module re-exports it for backward compatibility. New code should
import from `scraper.persistence.sqlite` instead of `database`.
"""

from scraper.persistence.sqlite import DatabaseManager  # type: ignore F401
from .models import Product, PriceHistory, URLEntry, CacheEntry
from .config import DatabaseConfig

__all__ = [
    "DatabaseManager",
    "Product",
    "PriceHistory",
    "URLEntry",
    "CacheEntry",
    "DatabaseConfig",
]
