"""TopAchat specific scraping logic."""

import re
import logging
from utils import clean_price


def wait_for_topachat_price(page):
    """Wait for TopAchat price elements to load with multiple attempts."""
    selectors_to_try = [
        ".offer-price__price.svelte-hgy1uf",
        ".offer-price__price",
        "span.offer-price__price",
        ".price",
        "[data-price]",
        ".product-price",
    ]

    for selector in selectors_to_try:
        try:
            page.wait_for_selector(selector, timeout=8000)
            logging.info(f"[Playwright] TopAchat price selector found: {selector}")
            return
        except Exception:
            continue

    logging.warning("[Playwright] No TopAchat price selectors found after wait")


def extract_topachat_price(elem):
    """Extract price from TopAchat specific elements."""
    direct_texts = [t for t in elem.strings if t.strip()]
    main_text = direct_texts[0] if direct_texts else elem.get_text(strip=True)
    match = re.search(r"([\d.,]+)\s*€", main_text)
    if match:
        price_str = match.group(1)
        price = clean_price(price_str)
        if price:
            return price
    if "€" in main_text:
        price_str = main_text.split("€")[0].strip()
        price = clean_price(price_str)
        if price:
            return price
    return None
