import os
import re
import pandas as pd
from htmlgen.builder import SingleFileHTMLBuilder


def normalize_dynamic(html: str) -> str:
    # Remove ISO timestamps / dates that vary
    html = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:[0-9:.+-]+", "<TS>", html)
    html = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", html)
    return html


def test_builder_basic_snapshot(tmp_path):
    # Minimal synthetic history
    history = pd.DataFrame(
        [
            {
                "Timestamp_ISO": "2025-01-01T10:00:00",
                "Product_Name": "CPU X",
                "URL": "http://a",
                "Price": 100,
            },
            {
                "Timestamp_ISO": "2025-01-02T10:00:00",
                "Product_Name": "CPU X",
                "URL": "http://a",
                "Price": 90,
            },
            {
                "Timestamp_ISO": "2025-01-01T10:00:00",
                "Product_Name": "GPU Y",
                "URL": "http://b",
                "Price": 300,
            },
        ]
    )
    product_prices = {
        "CPU X": [{"url": "http://a", "price": 90}],
        "GPU Y": [{"url": "http://b", "price": 300}],
    }
    products_meta = {
        "CPU X": {"category": "CPU"},
        "GPU Y": {"category": "GPU"},
    }
    builder = SingleFileHTMLBuilder()
    html = builder.build(product_prices, history, products_meta)
    norm = normalize_dynamic(html)
    snapshot_file = tmp_path / "snapshot.html"
    snapshot_file.write_text(norm, encoding="utf-8")
    # Basic assertions on structure
    assert "<!DOCTYPE html>" in html
    assert "Historique du prix total" in html
    assert "CPU X" in html and "GPU Y" in html
    # Ensure chart JSON present
    assert "new Chart" in html
