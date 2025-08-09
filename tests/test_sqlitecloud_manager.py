import os
import pytest

from database.config import DatabaseConfig
from database.sqlitecloud_manager import SQLiteCloudManager

pytestmark = pytest.mark.skipif(
    not os.getenv("SQLITECLOUD_SCRAPER_CONNECTION_STRING"),
    reason="SQLITECLOUD_SCRAPER_CONNECTION_STRING not set for integration test",
)


def test_sqlitecloud_basic_flow(monkeypatch):
    conn = os.environ["SQLITECLOUD_SCRAPER_CONNECTION_STRING"]
    cfg = DatabaseConfig(database_type="sqlitecloud", sqlitecloud_connection=conn)
    mgr = SQLiteCloudManager(cfg)

    # Insert a dummy product directly (since cloud manager is minimal)
    mgr.conn.execute(
        "INSERT INTO products (name, category) VALUES (?,?)",
        ("Cloud Test Product", "TestCat"),
    )
    mgr.conn.execute(
        "INSERT INTO urls (product_id, url, site_name) SELECT id, ?, ? FROM products WHERE name=?",
        ("https://example.com/test", "example.com", "Cloud Test Product"),
    )
    mgr.conn.commit()

    # Simulate price entry
    added = mgr.add_price_entry("Cloud Test Product", "https://example.com/test", 9.99)
    assert added
    hist = mgr.get_price_history("Cloud Test Product")
    assert not hist.empty
    assert (hist["Product_Name"] == "Cloud Test Product").all()

    # Malfunctioning link logging
    prod_row = mgr.conn.execute(
        "SELECT id FROM products WHERE name=?", ("Cloud Test Product",)
    ).fetchone()
    mgr.log_malfunctioning_link(
        prod_row[0], "https://example.com/test", "price_parse_failed", "No price"
    )
    rows = mgr.get_malfunctioning_links()
    assert any(r.get("error_type") == "price_parse_failed" for r in rows)
