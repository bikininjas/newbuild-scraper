import unittest
import os
import sys

# Ensure src/ is on sys.path for imports
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from htmlgen.render import compute_summary_total


class TestTotals(unittest.TestCase):
    def test_excludes_upgrade_kit(self):
        category_products = {
            "CPU": [{"name": "CPU A", "price": "200.00", "url": "#"}],
            "GPU": [{"name": "GPU A", "price": "300.00", "url": "#"}],
            "Upgrade Kit": [
                {"name": "Bundle", "price": "999.99", "url": "#"}
            ],
        }
        total = compute_summary_total(category_products)
        self.assertEqual(total, 500.00)

    def test_respects_selections(self):
        category_products = {
            "CPU": [
                {"name": "CPU A", "price": "200.00", "url": "#"},
                {"name": "CPU B", "price": "150.00", "url": "#"},
            ],
            "GPU": [{"name": "GPU A", "price": "300.00", "url": "#"}],
            "Upgrade Kit": [
                {"name": "Bundle", "price": "999.99", "url": "#"}
            ],
        }
        selections = {"CPU": "CPU B"}
        total = compute_summary_total(category_products, selections)
        self.assertEqual(total, 450.00)


if __name__ == "__main__":
    unittest.main()
