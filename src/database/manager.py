"""SQLite-only database manager (CSV support removed)."""

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from contextlib import contextmanager

from .config import DatabaseConfig
from .models import Product, PriceHistory, URLEntry, CacheEntry, CREATE_TABLES_SQL


class DatabaseManager:
    """Database manager (SQLite only)."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.logger = logging.getLogger(__name__)
        # Initialize database immediately
        self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite database and create tables."""
        with self._get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
        self.logger.info(f"SQLite database initialized at {self.config.sqlite_path}")

    @contextmanager
    def _get_connection(self):
        """Get SQLite database connection with proper error handling."""
        if self.config.database_type != "sqlite":
            raise ValueError("SQLite connection requested but database_type is not 'sqlite'")

        conn = sqlite3.connect(self.config.sqlite_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _extract_site_name(self, url: str) -> str:
        """Extract site name from URL."""
        sites = {
            "amazon.fr": "Amazon",
            "idealo.fr": "Idealo",
            "ldlc.com": "LDLC",
            "topachat.com": "TopAchat",
            "materiel.net": "Materiel.net",
            "pccomponentes.fr": "PC Componentes",
            "grosbill.com": "Grosbill",
            "alternate.fr": "Alternate",
            "bpm-power.com": "BPM Power",
        }

        for domain, name in sites.items():
            if domain in url:
                return name

        return "Unknown"

    # Product management methods
    def get_products(self) -> List[Product]:
        """Get all products."""
        return self._get_products_sqlite()

    def _get_products_sqlite(self) -> List[Product]:
        """Get products from SQLite."""
        products = []
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, category, created_at, updated_at FROM products ORDER BY name"
            ).fetchall()

            for row in rows:
                products.append(
                    Product(
                        id=row["id"],
                        name=row["name"],
                        category=row["category"],
                        created_at=(
                            datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                        ),
                        updated_at=(
                            datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
                        ),
                    )
                )

        return products

    def get_product_urls(self, product_name: str) -> List[URLEntry]:
        """Get URLs for a specific product."""
        return self._get_product_urls_sqlite(product_name)

    def _get_product_urls_sqlite(self, product_name: str) -> List[URLEntry]:
        """Get product URLs from SQLite."""
        urls = []
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT u.id, u.product_id, u.url, u.site_name, u.active, u.created_at
                   FROM urls u
                   JOIN products p ON u.product_id = p.id
                   WHERE p.name = ? AND u.active = 1
                   ORDER BY u.site_name""",
                (product_name,),
            ).fetchall()

            for row in rows:
                urls.append(
                    URLEntry(
                        id=row["id"],
                        product_id=row["product_id"],
                        url=row["url"],
                        site_name=row["site_name"],
                        active=bool(row["active"]),
                        created_at=(
                            datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                        ),
                    )
                )

        return urls

    # Price history methods
    def add_price_entry(
        self,
        product_name: str,
        url: str,
        price: float,
        scraped_at: Optional[datetime] = None,
        vendor_name: Optional[str] = None,
        vendor_url: Optional[str] = None,
        is_marketplace: bool = False,
        is_prime_eligible: bool = False,
    ) -> bool:
        """Add a price entry."""
        return self._add_price_entry_sqlite(
            product_name,
            url,
            price,
            scraped_at,
            vendor_name,
            vendor_url,
            is_marketplace,
            is_prime_eligible,
        )

    def _add_price_entry_sqlite(
        self,
        product_name: str,
        url: str,
        price: float,
        scraped_at: Optional[datetime] = None,
        vendor_name: Optional[str] = None,
        vendor_url: Optional[str] = None,
        is_marketplace: bool = False,
        is_prime_eligible: bool = False,
    ) -> bool:
        """Add price entry to SQLite."""
        if scraped_at is None:
            scraped_at = datetime.now()

        with self._get_connection() as conn:
            # Get product ID
            product_result = conn.execute(
                "SELECT id FROM products WHERE name = ?", (product_name,)
            ).fetchone()

            if not product_result:
                self.logger.warning(f"Product not found: {product_name}")
                return False

            product_id = product_result[0]
            site_name = self._extract_site_name(url)

            # Insert price entry
            conn.execute(
                """INSERT INTO price_history 
                   (product_id, url, price, scraped_at, site_name, vendor_name, vendor_url, is_marketplace, is_prime_eligible) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    product_id,
                    url,
                    price,
                    scraped_at,
                    site_name,
                    vendor_name,
                    vendor_url,
                    is_marketplace,
                    is_prime_eligible,
                ),
            )
            conn.commit()

        return True

    def get_price_history(self, product_name: Optional[str] = None) -> pd.DataFrame:
        """Get price history, optionally filtered by product."""
        return self._get_price_history_sqlite(product_name)

    def _get_price_history_sqlite(self, product_name: Optional[str] = None) -> pd.DataFrame:
        """Get price history from SQLite."""
        with self._get_connection() as conn:
            if product_name:
                query = """
                    SELECT 
                        DATE(ph.scraped_at) as Date,
                        p.name as Product_Name,
                        ph.url as URL,
                        ph.price as Price,
                        ph.scraped_at as Timestamp_ISO
                    FROM price_history ph
                    JOIN products p ON ph.product_id = p.id
                    WHERE p.name = ?
                    ORDER BY ph.scraped_at
                """
                df = pd.read_sql_query(query, conn, params=(product_name,))
            else:
                query = """
                    SELECT 
                        DATE(ph.scraped_at) as Date,
                        p.name as Product_Name,
                        ph.url as URL,
                        ph.price as Price,
                        ph.scraped_at as Timestamp_ISO
                    FROM price_history ph
                    JOIN products p ON ph.product_id = p.id
                    ORDER BY ph.scraped_at
                """
                df = pd.read_sql_query(query, conn)

        return df

    # Caching methods (SQLite only)
    def is_url_cached(self, url: str) -> bool:
        """Check if URL is cached and still valid."""
        with self._get_connection() as conn:
            result = conn.execute(
                """SELECT last_scraped, cache_duration_hours, status, next_retry
                   FROM cache WHERE url = ?""",
                (url,),
            ).fetchone()

            if not result:
                return False

            last_scraped = datetime.fromisoformat(result["last_scraped"])
            cache_duration = timedelta(hours=result["cache_duration_hours"])
            status = result["status"]
            next_retry = result["next_retry"]

            # For successful cache entries
            if status == "success":
                return datetime.now() < (last_scraped + cache_duration)

            # For failed entries, check retry time
            if status == "failed" and next_retry:
                return datetime.now() < datetime.fromisoformat(next_retry)

            return False

    def update_cache(self, url: str, success: bool = True, next_retry: Optional[datetime] = None):
        """Update cache entry for URL."""
        with self._get_connection() as conn:
            # Get existing cache entry
            existing = conn.execute("SELECT attempts FROM cache WHERE url = ?", (url,)).fetchone()
            attempts = (existing["attempts"] if existing else 0) + 1

            status = "success" if success else "failed"
            cache_duration = (
                self.config.cache_duration_hours
                if success
                else self.config.failed_cache_duration_hours
            )

            if not success and not next_retry:
                # Exponential backoff: 1h, 2h, 4h, 8h, 24h max
                backoff_hours = min(2 ** (attempts - 1), 24)
                next_retry = datetime.now() + timedelta(hours=backoff_hours)

            conn.execute(
                """INSERT OR REPLACE INTO cache 
                   (url, last_scraped, cache_duration_hours, status, attempts, next_retry)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    url,
                    datetime.now(),
                    cache_duration,
                    status,
                    attempts,
                    next_retry.isoformat() if next_retry else None,
                ),
            )
            conn.commit()

    def get_products_needing_scrape(self, max_age_hours: int = 48) -> List[Tuple[str, str]]:
        """Get products that need scraping (no entries in last N hours)."""
        return self._get_products_needing_scrape_sqlite(max_age_hours)

    def _get_products_needing_scrape_sqlite(self, max_age_hours: int) -> List[Tuple[str, str]]:
        """Get products needing scrape from SQLite."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with self._get_connection() as conn:
            # Get products with no recent price entries
            query = """
                SELECT DISTINCT p.name, u.url
                FROM products p
                JOIN urls u ON p.id = u.product_id
                WHERE u.active = 1
                AND NOT EXISTS (
                    SELECT 1 FROM price_history ph 
                    WHERE ph.product_id = p.id 
                    AND ph.url = u.url 
                    AND ph.scraped_at > ?
                )
                ORDER BY p.name, u.site_name
            """

            rows = conn.execute(query, (cutoff_time,)).fetchall()
            return [(row["name"], row["url"]) for row in rows]

    # Export methods for backward compatibility
    def export_to_csv(self):  # Legacy no-op
        self.logger.info("export_to_csv called - CSV support removed (no-op)")

    # Product issues tracking methods
    def log_product_issue(
        self,
        product_id: int,
        url: str,
        issue_type: str,
        expected_name: str = None,
        actual_name: str = None,
        error_message: str = None,
        http_status_code: int = None,
    ):
        """Log a product issue to the database."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO product_issues 
                (product_id, url, issue_type, expected_name, actual_name, error_message, http_status_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    product_id,
                    url,
                    issue_type,
                    expected_name,
                    actual_name,
                    error_message,
                    http_status_code,
                ),
            )

        self.logger.info(f"Logged {issue_type} issue for product {product_id}: {url}")

    def get_product_issues(self, resolved: bool = None) -> List[dict]:
        """Get product issues from the database."""
        with self._get_connection() as conn:
            if resolved is None:
                query = """
                    SELECT pi.*, p.name as product_name, p.category
                    FROM product_issues pi
                    JOIN products p ON pi.product_id = p.id
                    ORDER BY pi.detected_at DESC
                """
                rows = conn.execute(query).fetchall()
            else:
                query = """
                    SELECT pi.*, p.name as product_name, p.category
                    FROM product_issues pi
                    JOIN products p ON pi.product_id = p.id
                    WHERE pi.resolved = ?
                    ORDER BY pi.detected_at DESC
                """
                rows = conn.execute(query, (1 if resolved else 0,)).fetchall()

            return [dict(row) for row in rows]

    def resolve_product_issue(self, issue_id: int):
        """Mark a product issue as resolved."""
        with self._get_connection() as conn:
            conn.execute("UPDATE product_issues SET resolved = 1 WHERE id = ?", (issue_id,))

        self.logger.info(f"Marked issue {issue_id} as resolved")

    def get_product_by_url(self, url: str) -> Optional[Product]:
        """Get product information by URL."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT p.id, p.name, p.category, p.created_at, p.updated_at
                FROM products p
                JOIN urls u ON p.id = u.product_id
                WHERE u.url = ?
            """,
                (url,),
            ).fetchone()

            if row:
                return Product(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    created_at=(
                        datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                    ),
                    updated_at=(
                        datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
                    ),
                )
            return None

    def deactivate_product_url(self, url: str, reason: str = "problematic"):
        """Deactivate a specific URL due to issues."""
        with self._get_connection() as conn:
            result = conn.execute("UPDATE urls SET active = 0 WHERE url = ?", (url,))
            if result.rowcount > 0:
                conn.commit()  # Explicit commit
                self.logger.info(f"Deactivated URL due to {reason}: {url}")
            return result.rowcount > 0

    def remove_product_completely(self, product_id: int, reason: str = "critical issues"):
        """Remove a product completely from the database (cascade delete)."""
        if self.config.database_type != "sqlite":
            return

        with self._get_connection() as conn:
            # Enable foreign keys for proper cascade delete
            conn.execute("PRAGMA foreign_keys = ON")

            # Get product name for logging
            product_row = conn.execute(
                "SELECT name FROM products WHERE id = ?", (product_id,)
            ).fetchone()

            if product_row:
                product_name = product_row["name"]

                # Delete product (cascades to urls, price_history)
                conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

                # Mark related issues as resolved
                conn.execute(
                    "UPDATE product_issues SET resolved = 1 WHERE product_id = ?",
                    (product_id,),
                )

                # Explicit commit to ensure changes are saved
                conn.commit()

                self.logger.info(
                    f"Removed product '{product_name}' (ID: {product_id}) due to {reason}"
                )
                return True
            return False

    def auto_handle_critical_issues(self, auto_remove: bool = True):
        """Automatically handle critical product issues."""
        issues = self.get_product_issues(resolved=False)
        critical_issues = [i for i in issues if i["issue_type"] in ["404_error", "name_mismatch"]]

        handled_count = 0

        for issue in critical_issues:
            product_id = issue["product_id"]
            url = issue["url"]
            issue_type = issue["issue_type"]

            if issue_type == "404_error" and auto_remove:
                # Remove products with 404 errors completely
                if self.remove_product_completely(product_id, "404 error"):
                    handled_count += 1
            elif issue_type == "name_mismatch":
                # Deactivate URLs with name mismatches (don't remove product completely)
                if self.deactivate_product_url(url, "name mismatch"):
                    # Mark this specific issue as resolved
                    self.resolve_product_issue(issue["id"])
                    handled_count += 1

        if handled_count > 0:
            self.logger.info(f"Auto-handled {handled_count} critical product issues")

        return handled_count
