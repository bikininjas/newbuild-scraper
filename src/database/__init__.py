"""
Database module for the price scraper.
Handles both SQLite and CSV backends with automatic migration.
"""

from .manager import DatabaseManager
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
