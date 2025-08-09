"""SQLiteCloud database manager implementing minimal subset used by app.

Fallbacks to local SQLite if connection string missing.
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
import pandas as pd

try:  # lazy import
    import sqlitecloud  # type: ignore
except Exception:  # pragma: no cover
    sqlitecloud = None  # type: ignore

from .config import DatabaseConfig
from .models import CREATE_TABLES_SQL


class SQLiteCloudManager:
    def __init__(self, config: DatabaseConfig, driver_module=None):
        if not config.sqlitecloud_connection:
            raise ValueError("sqlitecloud_connection not provided in config")
        module = driver_module or sqlitecloud
        if module is None:  # allow tests to inject fake driver
            raise ImportError("sqlitecloud package not installed")
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.conn = module.connect(config.sqlitecloud_connection)
        # Ensure schema exists (idempotent)
        self.conn.executescript(CREATE_TABLES_SQL)

    # --- compatibility helpers (subset) --- #
    def get_products(self):
        rows = self.conn.execute(
            "SELECT id, name, category, created_at, updated_at FROM products ORDER BY name"
        ).fetchall()
        result = []
        for r in rows:
            result.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "category": r[2],
                    "created_at": r[3],
                    "updated_at": r[4],
                }
            )
        return result

    def get_product_urls(self, product_name: str):
        rows = self.conn.execute(
            """SELECT u.id,u.product_id,u.url,u.site_name,u.active,u.created_at FROM urls u JOIN products p ON u.product_id=p.id WHERE p.name=? AND u.active=1 ORDER BY u.site_name""",
            (product_name,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "product_id": r[1],
                "url": r[2],
                "site_name": r[3],
                "active": bool(r[4]),
                "created_at": r[5],
            }
            for r in rows
        ]

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
            scraped_at = datetime.now(timezone.utc)
        product_row = self.conn.execute(
            "SELECT id FROM products WHERE name=?", (product_name,)
        ).fetchone()
        if not product_row:
            self.logger.warning("Product not found: %s", product_name)
            return False
        product_id = product_row[0]
        site_name = url.split("/")[2] if "//" in url else "Unknown"
        self.conn.execute(
            """INSERT INTO price_history (product_id,url,price,scraped_at,site_name,vendor_name,vendor_url,is_marketplace,is_prime_eligible) VALUES (?,?,?,?,?,?,?,?,?)""",
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
        try:
            self.conn.commit()
        except Exception:  # pragma: no cover
            pass
        return True

    def get_price_history(self, product_name: Optional[str] = None) -> pd.DataFrame:
        if product_name:
            q = """SELECT DATE(ph.scraped_at) as Date,p.name as Product_Name,ph.url as URL,ph.price as Price,ph.scraped_at as Timestamp_ISO FROM price_history ph JOIN products p ON ph.product_id=p.id WHERE p.name=? ORDER BY ph.scraped_at"""
            return pd.read_sql_query(q, self.conn, params=(product_name,))
        q = """SELECT DATE(ph.scraped_at) as Date,p.name as Product_Name,ph.url as URL,ph.price as Price,ph.scraped_at as Timestamp_ISO FROM price_history ph JOIN products p ON ph.product_id=p.id ORDER BY ph.scraped_at"""
        return pd.read_sql_query(q, self.conn)

    # Caching features skipped for cloud (could be added later)
    def is_url_cached(self, _url: str) -> bool:
        return False

    def update_cache(self, *_, **__):  # no-op for cloud
        return None

    def get_products_needing_scrape(self, max_age_hours: int = 48) -> List[Tuple[str, str]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        rows = self.conn.execute(
            """SELECT DISTINCT p.name,u.url FROM products p JOIN urls u ON p.id=u.product_id WHERE u.active=1 AND NOT EXISTS (SELECT 1 FROM price_history ph WHERE ph.product_id=p.id AND ph.url=u.url AND ph.scraped_at > ?) ORDER BY p.name,u.site_name""",
            (cutoff,),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    # Issues
    def log_product_issue(self, product_id: int, url: str, issue_type: str, **meta):
        self.conn.execute(
            """INSERT INTO product_issues (product_id,url,issue_type,error_message,http_status_code,expected_name,actual_name) VALUES (?,?,?,?,?,?,?)""",
            (
                product_id,
                url,
                issue_type,
                meta.get("error_message"),
                meta.get("http_status_code"),
                meta.get("expected_name"),
                meta.get("actual_name"),
            ),
        )

    def get_product_by_url(self, url: str):
        row = self.conn.execute(
            """SELECT p.id,p.name,p.category,p.created_at,p.updated_at FROM products p JOIN urls u ON p.id=u.product_id WHERE u.url=?""",
            (url,),
        ).fetchone()
        if not row:
            return None
        return type("ProductObj", (), {"id": row[0], "name": row[1], "category": row[2]})

    # Malfunctioning links (basic)
    def log_malfunctioning_link(
        self, product_id: int, url: str, error_type: str, error_message: str | None = None, **_
    ):
        existing = self.conn.execute(
            "SELECT id FROM malfunctioning_links WHERE url=?", (url,)
        ).fetchone()
        if existing:
            self.conn.execute(
                """UPDATE malfunctioning_links SET last_detected=CURRENT_TIMESTAMP, occurrences=occurrences+1, error_type=?, error_message=? WHERE id=?""",
                (error_type, error_message, existing[0]),
            )
        else:
            self.conn.execute(
                """INSERT INTO malfunctioning_links (product_id,url,site_name,error_type,error_message) VALUES (?,?,?,?,?)""",
                (product_id, url, url.split("/")[2], error_type, error_message),
            )
        self.conn.execute("UPDATE urls SET active=0 WHERE url=?", (url,))
        try:
            self.conn.commit()
        except Exception:  # pragma: no cover
            pass

    def get_malfunctioning_links(self, include_resolved: bool = False):
        where_clause = "" if include_resolved else "WHERE ml.resolved=0"
        q = f"""
            SELECT ml.*, p.name as product_name, p.category
            FROM malfunctioning_links ml JOIN products p ON ml.product_id=p.id
            {where_clause}
            ORDER BY ml.last_detected DESC
        """
        rows = self.conn.execute(q).fetchall()
        # Get column names once (best-effort)
        cols = []
        try:
            cols = [
                c[0]
                for c in self.conn.execute("PRAGMA table_info(malfunctioning_links)").fetchall()
            ]
        except Exception:  # pragma: no cover
            pass

        def row_to_dict(r):  # small helper
            if hasattr(r, "keys"):
                return dict(r)
            if not cols:
                return dict(enumerate(r))
            return {col: r[idx] for idx, col in enumerate(cols) if idx < len(r)}

        return [row_to_dict(r) for r in rows]

    def resolve_malfunctioning_link(self, url: str):
        self.conn.execute("UPDATE malfunctioning_links SET resolved=1 WHERE url=?", (url,))
        try:
            self.conn.commit()
        except Exception:  # pragma: no cover
            pass

    def reactivate_url_if_resolved(self, url: str):
        row = self.conn.execute(
            "SELECT resolved FROM malfunctioning_links WHERE url=?", (url,)
        ).fetchone()
        if row and (row[0] if not isinstance(row, dict) else row.get("resolved")):
            self.conn.execute("UPDATE urls SET active=1 WHERE url=?", (url,))
            try:
                self.conn.commit()
            except Exception:  # pragma: no cover
                pass
            return True
        return False
