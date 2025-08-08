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
            name = row["Product_Name"].strip()
            url = row["URL"].strip()
            category = row.get("Category", "Other").strip()
            products.setdefault(name, {"urls": [], "category": category})
            if url not in products[name]["urls"]:
                products[name]["urls"].append(url)
    return products


def load_history(csv_path):
    return pd.read_csv(csv_path, encoding="utf-8")
