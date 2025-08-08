import os
import sys
import unittest
from html import unescape
import pandas as pd

# Ensure src/ is on sys.path for imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from htmlgen.render import render_summary_table  # noqa: E402


class TestRenderSummary(unittest.TestCase):
    def test_summary_excludes_upgrade_kit_in_total(self):
        # Build minimal category_products input matching renderer contract
        category_products = {
            "CPU": [
                {"name": "CPU A", "price": "200.00", "url": "https://example.com/cpu"}
            ],
            "Upgrade Kit": [
                {"name": "Bundle", "price": "999.99", "url": "https://example.com/kit"}
            ],
        }

        # Build minimal history DataFrame with matching row for CPU
        history = pd.DataFrame(
            [
                {
                    "Product_Name": "CPU A",
                    "URL": "https://example.com/cpu",
                    "Price": "200.00",
                    "Timestamp_ISO": "2025-08-08 07:25",
                },
                {
                    "Product_Name": "Bundle",
                    "URL": "https://example.com/kit",
                    "Price": "999.99",
                    "Timestamp_ISO": "2025-08-08 07:25",
                },
            ]
        )

        html = render_summary_table(category_products, history)
        text = unescape(html)
        # Ensure total equals 200.00€ (kit excluded)
        self.assertIn("💰 Total", text)
        self.assertIn("200.00€", text)
        # Ensure the exclusion note is present
        self.assertIn("Upgrade Kit non inclus", text)


if __name__ == "__main__":
    unittest.main()
