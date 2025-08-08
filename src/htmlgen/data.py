"""
Data loading and preprocessing for HTML generation.
"""

import pandas as pd
import csv


def load_products(csv_path):
    products = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows or rows with missing required fields
            if not row or not row.get("Product_Name") or not row.get("URL"):
                continue

            name = row["Product_Name"].strip()
            url = row["URL"].strip()
            category = row.get("Category", "Other").strip()

            # Skip if name or URL are empty after stripping
            if not name or not url:
                continue

            products.setdefault(name, {"urls": [], "category": category})
            if url not in products[name]["urls"]:
                products[name]["urls"].append(url)
    return products


def load_history(csv_path):
    return pd.read_csv(csv_path, encoding="utf-8")
