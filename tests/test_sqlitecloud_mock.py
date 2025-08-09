import os
import sys
import types
import sqlite3
import pandas as pd

from database.config import DatabaseConfig


def make_fake_sqlitecloud_module():
    mod = types.ModuleType("sqlitecloud")

    def connect(conn_str):  # mimic sqlitecloud.connect API
        # Use in-memory sqlite3 DB to simulate remote
        return sqlite3.connect(":memory:")

    mod.connect = connect  # type: ignore
    return mod


def test_sqlitecloud_manager_with_fake_module(monkeypatch):
    # Inject fake sqlitecloud before importing manager
    fake_mod = make_fake_sqlitecloud_module()
    sys.modules["sqlitecloud"] = fake_mod

    from database.sqlitecloud_manager import SQLiteCloudManager  # import after injection

    os.environ["DB_TYPE"] = "sqlitecloud"
    os.environ["SQLITECLOUD_SCRAPER_CONNECTION_STRING"] = "sqlitecloud://fake/test"  # placeholder
    cfg = DatabaseConfig.from_env()
    mgr = SQLiteCloudManager(cfg, driver_module=fake_mod)
    # Ensure schema includes malfunctioning_links (run again idempotently)
    from database.models import CREATE_TABLES_SQL

    mgr.conn.executescript(CREATE_TABLES_SQL)

    # Seed minimal schema data (products + url + price)
    mgr.conn.execute("INSERT INTO products (name, category) VALUES (?, ?)", ("Mock CPU", "CPU"))
    mgr.conn.execute(
        "INSERT INTO urls (product_id, url, site_name) SELECT id, ?, ? FROM products WHERE name=?",
        ("https://example.com/mockcpu", "example.com", "Mock CPU"),
    )
    mgr.conn.commit()

    # Add price entry
    assert mgr.add_price_entry("Mock CPU", "https://example.com/mockcpu", 111.11)
    hist = mgr.get_price_history("Mock CPU")
    assert isinstance(hist, pd.DataFrame)
    assert not hist.empty
    assert abs(hist["Price"].iloc[-1] - 111.11) < 1e-6

    # Malfunctioning link logging & retrieval
    prod_id = mgr.conn.execute("SELECT id FROM products WHERE name='Mock CPU'").fetchone()[0]
    mgr.log_malfunctioning_link(prod_id, "https://example.com/mockcpu", "price_parse_failed", "x")
    rows = mgr.get_malfunctioning_links()

    # Rows may be dicts keyed by column index in mock scenario
    def extract_error_type(r):
        return r.get("error_type") if isinstance(r, dict) else None

    if rows and isinstance(rows[0], dict) and "error_type" not in rows[0]:
        # map index 4 from observed structure
        def extract_error_type(r):  # type: ignore
            return r.get(4)

    assert any(extract_error_type(r) == "price_parse_failed" for r in rows)
