"""
Database models for the price scraper.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import sqlite3


@dataclass
class Product:
    """Product model."""

    id: Optional[int] = None
    name: str = ""
    category: str = "Other"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class URLEntry:
    """URL entry model."""

    id: Optional[int] = None
    product_id: Optional[int] = None
    url: str = ""
    site_name: str = ""
    active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "url": self.url,
            "site_name": self.site_name,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class PriceHistory:
    """Price history model."""

    id: Optional[int] = None
    product_id: Optional[int] = None
    url: str = ""
    price: float = 0.0
    scraped_at: Optional[datetime] = None
    site_name: str = ""
    vendor_name: Optional[str] = None  # For aggregators like Idealo
    vendor_url: Optional[str] = None  # Actual vendor URL if available
    is_marketplace: bool = False  # True if sold by marketplace vendor
    is_prime_eligible: bool = False  # True if Amazon Prime eligible
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "url": self.url,
            "price": self.price,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "site_name": self.site_name,
            "vendor_name": self.vendor_name,
            "vendor_url": self.vendor_url,
            "is_marketplace": self.is_marketplace,
            "is_prime_eligible": self.is_prime_eligible,
            "success": self.success,
        }


@dataclass
class CacheEntry:
    """Cache entry model."""

    id: Optional[int] = None
    url: str = ""
    last_scraped: Optional[datetime] = None
    cache_duration_hours: int = 6
    status: str = "success"  # "success", "failed", "blocked"
    attempts: int = 0
    next_retry: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "last_scraped": (
                self.last_scraped.isoformat() if self.last_scraped else None
            ),
            "cache_duration_hours": self.cache_duration_hours,
            "status": self.status,
            "attempts": self.attempts,
            "next_retry": self.next_retry.isoformat() if self.next_retry else None,
        }


# SQL Table Creation Queries
CREATE_TABLES_SQL = """
-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'Other',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- URLs table
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    url TEXT NOT NULL UNIQUE,
    site_name TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

-- Price history table
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    price REAL NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    site_name TEXT NOT NULL,
    vendor_name TEXT NULL,
    vendor_url TEXT NULL,
    is_marketplace BOOLEAN DEFAULT 0,
    is_prime_eligible BOOLEAN DEFAULT 0,
    success BOOLEAN DEFAULT 1,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

-- Cache table
CREATE TABLE IF NOT EXISTS cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_duration_hours INTEGER DEFAULT 6,
    status TEXT DEFAULT 'success',
    attempts INTEGER DEFAULT 0,
    next_retry TIMESTAMP NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_urls_product_id ON urls(product_id);
CREATE INDEX IF NOT EXISTS idx_urls_site_name ON urls(site_name);
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_scraped_at ON price_history(scraped_at);
CREATE INDEX IF NOT EXISTS idx_price_history_site_name ON price_history(site_name);
CREATE INDEX IF NOT EXISTS idx_price_history_vendor_name ON price_history(vendor_name);
CREATE INDEX IF NOT EXISTS idx_cache_url ON cache(url);
CREATE INDEX IF NOT EXISTS idx_cache_last_scraped ON cache(last_scraped);
CREATE INDEX IF NOT EXISTS idx_cache_status ON cache(status);
"""
