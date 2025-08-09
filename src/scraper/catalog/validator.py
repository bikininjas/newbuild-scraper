"""Validation for products.json payload."""

from __future__ import annotations
import re
from typing import List, Dict, Any

RE_URL = re.compile(r"^https?://")


class ProductValidationError(Exception):
    pass


def validate_products_payload(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        raise ProductValidationError("Root must be an object")
    if data.get("version") != 1:
        raise ProductValidationError("Unsupported or missing version (expected 1)")
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ProductValidationError("'products' must be a non-empty list")
    seen = set()
    normed: List[Dict[str, Any]] = []
    for idx, entry in enumerate(products):
        if not isinstance(entry, dict):
            raise ProductValidationError(f"Product at index {idx} is not an object")
        name = str(entry.get("name", "")).strip()
        category = str(entry.get("category", "Other")).strip() or "Other"
        urls = entry.get("urls")
        if not name:
            raise ProductValidationError(f"Product at index {idx} missing name")
        if name in seen:
            raise ProductValidationError(f"Duplicate product name: {name}")
        if not isinstance(urls, list) or not urls:
            raise ProductValidationError(f"Product '{name}' must have a non-empty 'urls' list")
        clean_urls = []
        for u in urls:
            su = str(u).strip()
            if not RE_URL.search(su):
                raise ProductValidationError(f"Product '{name}' has invalid url: {su}")
            clean_urls.append(su)
        normed.append({"name": name, "category": category, "urls": clean_urls})
        seen.add(name)
    return normed
