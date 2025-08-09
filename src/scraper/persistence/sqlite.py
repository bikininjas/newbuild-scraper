"""SQLite persistence layer (migrated from database.manager)."""

from __future__ import annotations
import sqlite3, logging
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional, List, Tuple
import pandas as pd

from database.config import DatabaseConfig  # uses config only (no DatabaseManager)
from database import models as _models  # avoid importing DatabaseManager from shim
from database.models import Product, PriceHistory, URLEntry, CacheEntry, CREATE_TABLES_SQL


class DatabaseManager:  # Retain name for compatibility
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.logger = logging.getLogger(__name__)
        self._init_sqlite()

    def _init_sqlite(self):
        with self._get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
        self.logger.info(f"SQLite database initialized at {self.config.sqlite_path}")

    @contextmanager
    def _get_connection(self):
        if self.config.database_type != "sqlite":
            raise ValueError("SQLite requested but database_type != sqlite")
        conn = sqlite3.connect(self.config.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # --- site helpers --- #
    def _extract_site_name(self, url: str) -> str:
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

    # --- product queries --- #
    def get_products(self) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, category, created_at, updated_at FROM products ORDER BY name"
            ).fetchall()
            products: List[Product] = []
            for r in rows:
                products.append(
                    Product(
                        id=r["id"],
                        name=r["name"],
                        category=r["category"],
                        created_at=(
                            datetime.fromisoformat(r["created_at"]) if r["created_at"] else None
                        ),
                        updated_at=(
                            datetime.fromisoformat(r["updated_at"]) if r["updated_at"] else None
                        ),
                    )
                )
            return products

    def get_product_urls(self, product_name: str) -> List[URLEntry]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT u.id, u.product_id, u.url, u.site_name, u.active, u.created_at
                   FROM urls u JOIN products p ON u.product_id = p.id
                   WHERE p.name = ? AND u.active = 1 ORDER BY u.site_name""",
                (product_name,),
            ).fetchall()
            result: List[URLEntry] = []
            for r in rows:
                result.append(
                    URLEntry(
                        id=r["id"],
                        product_id=r["product_id"],
                        url=r["url"],
                        site_name=r["site_name"],
                        active=bool(r["active"]),
                        created_at=(
                            datetime.fromisoformat(r["created_at"]) if r["created_at"] else None
                        ),
                    )
                )
            return result

    # --- price history --- #
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
        if scraped_at is None:
            scraped_at = datetime.now()
        with self._get_connection() as conn:
            product_row = conn.execute(
                "SELECT id FROM products WHERE name=?", (product_name,)
            ).fetchone()
            if not product_row:
                self.logger.warning(f"Product not found: {product_name}")
                return False
            product_id = product_row[0]
            site_name = self._extract_site_name(url)
            conn.execute(
                """INSERT INTO price_history
                   (product_id, url, price, scraped_at, site_name, vendor_name, vendor_url, is_marketplace, is_prime_eligible)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
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
        with self._get_connection() as conn:
            if product_name:
                q = """
                SELECT DATE(ph.scraped_at) as Date, p.name as Product_Name, ph.url as URL, ph.price as Price, ph.scraped_at as Timestamp_ISO
                FROM price_history ph JOIN products p ON ph.product_id = p.id
                WHERE p.name = ? ORDER BY ph.scraped_at"""
                return pd.read_sql_query(q, conn, params=(product_name,))
            q = """
            SELECT DATE(ph.scraped_at) as Date, p.name as Product_Name, ph.url as URL, ph.price as Price, ph.scraped_at as Timestamp_ISO
            FROM price_history ph JOIN products p ON ph.product_id = p.id ORDER BY ph.scraped_at"""
            return pd.read_sql_query(q, conn)

    # --- cache --- #
    def is_url_cached(self, url: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT last_scraped, cache_duration_hours, status, next_retry FROM cache WHERE url=?",
                (url,),
            ).fetchone()
            if not row:
                return False
            last_scraped = datetime.fromisoformat(row["last_scraped"])  # type: ignore
            cache_duration = timedelta(hours=row["cache_duration_hours"])  # type: ignore
            status = row["status"]
            next_retry = row["next_retry"]
            if status == "success":
                return datetime.now() < last_scraped + cache_duration
            if status == "failed" and next_retry:
                return datetime.now() < datetime.fromisoformat(next_retry)
            return False

    def update_cache(self, url: str, success: bool = True, next_retry: Optional[datetime] = None):
        with self._get_connection() as conn:
            existing = conn.execute("SELECT attempts FROM cache WHERE url=?", (url,)).fetchone()
            attempts = (existing["attempts"] if existing else 0) + 1  # type: ignore
            status = "success" if success else "failed"
            cache_duration = (
                self.config.cache_duration_hours
                if success
                else self.config.failed_cache_duration_hours
            )
            if not success and not next_retry:
                backoff_hours = min(2 ** (attempts - 1), 24)
                next_retry = datetime.now() + timedelta(hours=backoff_hours)
            conn.execute(
                """INSERT OR REPLACE INTO cache
                (url, last_scraped, cache_duration_hours, status, attempts, next_retry)
                VALUES (?,?,?,?,?,?)""",
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
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT DISTINCT p.name, u.url FROM products p JOIN urls u ON p.id=u.product_id
                WHERE u.active=1 AND NOT EXISTS (
                    SELECT 1 FROM price_history ph WHERE ph.product_id=p.id AND ph.url=u.url AND ph.scraped_at > ?
                ) ORDER BY p.name, u.site_name""",
                (cutoff,),
            ).fetchall()
            return [(r["name"], r["url"]) for r in rows]

    # product issues subset (minimal needed for current usage)
    def get_product_issues(self, resolved: bool | None = None):
        with self._get_connection() as conn:
            if resolved is None:
                q = """SELECT pi.*, p.name as product_name, p.category FROM product_issues pi JOIN products p ON pi.product_id=p.id ORDER BY pi.detected_at DESC"""
                rows = conn.execute(q).fetchall()
            else:
                q = """SELECT pi.*, p.name as product_name, p.category FROM product_issues pi JOIN products p ON pi.product_id=p.id WHERE pi.resolved=? ORDER BY pi.detected_at DESC"""
                rows = conn.execute(q, (1 if resolved else 0,)).fetchall()
            return [dict(r) for r in rows]

    # --- issue logging & lookup (ported from legacy manager) --- #
    def log_product_issue(
        self,
        product_id: int,
        url: str,
        issue_type: str,
        expected_name: str | None = None,
        actual_name: str | None = None,
        error_message: str | None = None,
        http_status_code: int | None = None,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO product_issues
                (product_id, url, issue_type, expected_name, actual_name, error_message, http_status_code)
                VALUES (?,?,?,?,?,?,?)
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
            conn.commit()
        self.logger.info(f"Logged {issue_type} issue for product {product_id}: {url}")

    def get_product_by_url(self, url: str) -> Optional[Product]:
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
            if not row:
                return None
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

    def resolve_product_issue(self, issue_id: int):
        with self._get_connection() as conn:
            conn.execute("UPDATE product_issues SET resolved=1 WHERE id=?", (issue_id,))
            conn.commit()

    def deactivate_product_url(self, url: str, reason: str = "problematic"):
        with self._get_connection() as conn:
            res = conn.execute("UPDATE urls SET active=0 WHERE url=?", (url,))
            if res.rowcount:
                conn.commit()
                self.logger.info(f"Deactivated URL due to {reason}: {url}")
                return True
            return False

    def remove_product_completely(self, product_id: int, reason: str = "critical issues"):
        with self._get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            row = conn.execute("SELECT name FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                return False
            name = row["name"]
            conn.execute("DELETE FROM products WHERE id=?", (product_id,))
            conn.execute("UPDATE product_issues SET resolved=1 WHERE product_id=?", (product_id,))
            conn.commit()
            self.logger.info(f"Removed product '{name}' (ID: {product_id}) due to {reason}")
            return True

    def auto_handle_critical_issues(self, auto_remove: bool = True):
        issues = self.get_product_issues(resolved=False)
        critical = [i for i in issues if i["issue_type"] in ["404_error", "name_mismatch"]]
        handled = 0
        for issue in critical:
            if issue["issue_type"] == "404_error" and auto_remove:
                if self.remove_product_completely(issue["product_id"], "404 error"):
                    handled += 1
            elif issue["issue_type"] == "name_mismatch":
                if self.deactivate_product_url(issue["url"], "name mismatch"):
                    self.resolve_product_issue(issue["id"])
                    handled += 1
        if handled:
            self.logger.info(f"Auto-handled {handled} critical product issues")
        return handled

    # legacy no-op for CSV export
    def export_to_csv(self):
        self.logger.info("export_to_csv called - CSV support removed (no-op)")
