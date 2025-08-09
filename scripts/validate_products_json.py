#!/usr/bin/env python3
"""Validate products.json structure.
Exit non-zero if invalid."""
import json, sys, re, pathlib

RE_URL = re.compile(r"^https?://")
path = pathlib.Path("products.json")
if not path.exists():
    print("products.json missing", file=sys.stderr)
    sys.exit(1)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as e:
    print("JSON parse error:", e, file=sys.stderr)
    sys.exit(2)
if data.get("version") != 1:
    print("Invalid or missing version (expected 1)", file=sys.stderr)
    sys.exit(3)
products = data.get("products")
if not isinstance(products, list) or not products:
    print("products must be non-empty list", file=sys.stderr)
    sys.exit(4)
seen = set()
errors = 0
for idx, p in enumerate(products):
    if not isinstance(p, dict):
        print(f"Product at index {idx} not object", file=sys.stderr)
        errors += 1
        continue
    name = str(p.get("name", "")).strip()
    if not name:
        print(f"Product {idx} missing name", file=sys.stderr)
        errors += 1
    if name in seen:
        print(f"Duplicate product name: {name}", file=sys.stderr)
        errors += 1
    seen.add(name)
    urls = p.get("urls")
    if not isinstance(urls, list) or not urls:
        print(f"Product {name or idx} has empty urls", file=sys.stderr)
        errors += 1
    else:
        for u in urls:
            if not RE_URL.match(str(u)):
                print(f"Product {name} invalid url: {u}", file=sys.stderr)
                errors += 1
    cat = p.get("category")
    if not isinstance(cat, str) or not cat.strip():
        print(f"Product {name} missing/invalid category", file=sys.stderr)
        errors += 1
if errors:
    print(f"Validation failed with {errors} error(s).", file=sys.stderr)
    sys.exit(5)
print(f"products.json valid: {len(products)} products")
