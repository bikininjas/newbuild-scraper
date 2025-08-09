import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from scraper.persistence.sqlite import DatabaseManager
from scraper.persistence import repositories as repo
from scraper.catalog.loader import import_from_json


def make_db(tmp_path: Path) -> DatabaseManager:
    cfg_path = tmp_path / "scraper.db"
    from database.config import DatabaseConfig

    cfg = DatabaseConfig(sqlite_path=str(cfg_path))
    return DatabaseManager(cfg)


def seed_products(db: DatabaseManager):
    # minimal inline products list to avoid reading real file
    products_payload = {
        "version": 1,
        "products": [
            {
                "name": "Test CPU",
                "category": "CPU",
                "urls": [
                    "https://www.amazon.fr/dp/TESTCPU/",
                    "https://www.topachat.com/pages/detail2_cat_est_micro_puis_rubrique_est_w_cpu_puis_ref_est_testcpu.html",
                ],
            }
        ],
    }
    import json, io

    tmp_json = io.StringIO(json.dumps(products_payload))
    # Write to a temp file because loader expects a path
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(json.dumps(products_payload))
        temp_path = f.name
    try:
        import_from_json(db, temp_path)
    finally:
        os.unlink(temp_path)


def test_record_price_round_trip(tmp_path):
    db = make_db(tmp_path)
    seed_products(db)
    ok = repo.record_price(db, "Test CPU", "https://www.amazon.fr/dp/TESTCPU/", 123.45)
    assert ok
    hist = repo.price_history(db, "Test CPU")
    assert not hist.empty
    assert (hist["Product_Name"] == "Test CPU").all()


def test_log_issue_and_auto_handle(tmp_path):
    db = make_db(tmp_path)
    seed_products(db)
    prod = next(p for p in repo.list_products(db) if p.name == "Test CPU")
    # log 404 issue
    repo.log_issue(
        db,
        product_id=prod.id,
        url="https://www.amazon.fr/dp/TESTCPU/",
        issue_type="404_error",
        http_status_code=404,
    )
    issues = repo.unresolved_issues(db)
    assert len(issues) == 1
    handled = repo.auto_handle_critical(db, auto_remove=True)
    assert handled >= 1
    # product should be gone
    products = repo.list_products(db)
    assert all(p.name != "Test CPU" for p in products)


def test_cache_backoff(tmp_path):
    db = make_db(tmp_path)
    seed_products(db)
    url = "https://www.amazon.fr/dp/TESTCPU/"
    # First failed attempt
    db.update_cache(url, success=False)
    # Second failed attempt
    db.update_cache(url, success=False)
    # Inspect cache table directly for backoff > 0
    with db._get_connection() as conn:  # type: ignore
        row = conn.execute("SELECT attempts, next_retry FROM cache WHERE url=?", (url,)).fetchone()
        assert row is not None
        assert row["attempts"] >= 2
        assert row["next_retry"] is not None
