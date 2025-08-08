"""
Idealo.fr site-specific handling and product validation.

This module handles:
- Product content mismatch detection (when URLs serve wrong products)
- Cookie consent handling
"""

import logging
import re
import json
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


def extract_product_info_from_url(url: str) -> dict:
    """Extract expected product information from Idealo URL structure."""
    # Extract product slug from URL
    # Example: https://www.idealo.fr/prix/202062898/razer-deathadder-v3-pro.html
    match = re.search(r"/prix/\d+/([^.]+)\.html", url)
    if not match:
        return {}

    product_slug = match.group(1)

    # Extract brand and model information from slug
    parts = product_slug.split("-")
    if not parts:
        return {}

    # Common brand patterns
    brand_patterns = {
        "razer": ["razer"],
        "logitech": ["logitech", "logitech-g"],
        "corsair": ["corsair"],
        "keychron": ["keychron"],
        "steelseries": ["steelseries"],
        "hyperx": ["hyperx"],
        "asus": ["asus"],
        "msi": ["msi"],
        "gigabyte": ["gigabyte"],
        "amd": ["amd"],
        "intel": ["intel"],
        "nvidia": ["nvidia"],
    }

    detected_brand = None
    for brand, patterns in brand_patterns.items():
        if any(pattern in product_slug.lower() for pattern in patterns):
            detected_brand = brand
            break

    # Extract model keywords (remove common words)
    common_words = {"pro", "gaming", "rgb", "wireless", "black", "white", "red", "blue"}
    model_parts = [
        part
        for part in parts
        if part.lower() not in common_words and part != detected_brand
    ]

    return {
        "slug": product_slug,
        "brand": detected_brand,
        "model_keywords": model_parts,
        "full_slug": product_slug,
    }


def extract_product_name_from_page(page: Page) -> str:
    """Extract product name from Idealo page using multiple strategies."""
    product_name = ""

    # Strategy 1: JSON-LD structured data (most reliable)
    try:
        json_scripts = page.locator('script[type="application/ld+json"]').all()
        for script in json_scripts:
            try:
                script_content = script.text_content()
                if script_content:
                    data = json.loads(script_content)
                    # Look for product name in JSON-LD
                    if isinstance(data, dict):
                        name = data.get("name") or data.get("@name")
                        if name and len(name.strip()) > 5:
                            product_name = name.strip()
                            break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                name = item.get("name") or item.get("@name")
                                if name and len(name.strip()) > 5:
                                    product_name = name.strip()
                                    break
            except (json.JSONDecodeError, AttributeError):
                continue
            if product_name:
                break
    except Exception as e:
        logger.debug(f"JSON-LD extraction failed: {e}")

    # Strategy 2: Standard CSS selectors
    if not product_name:
        selectors_to_try = [
            "h1",
            "h2",
            "header h1",
            "header h2",
            '[data-testid="productTitle"]',
            '[class*="productTitle"]',
            '[class*="product-title"]',
            ".productName",
            "header .productName",
        ]

        for selector in selectors_to_try:
            try:
                elements = page.locator(selector).all()
                for element in elements:
                    if element.is_visible():
                        text = element.text_content()
                        if text and len(text.strip()) > 5:
                            product_name = text.strip()
                            break
                if product_name:
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

    return product_name


def check_product_mismatch(page: Page, original_url: str) -> bool:
    """
    Check if the Idealo page serves the expected product based on URL.

    Returns True if mismatch is detected, False otherwise.
    """
    logger.info(f"[IDEALO] Checking product mismatch for: {original_url}")

    # Extract expected product info from URL
    expected = extract_product_info_from_url(original_url)
    if not expected.get("brand"):
        logger.debug(f"[IDEALO] Could not extract brand from URL: {original_url}")
        return False

    # Extract actual product name from page
    actual_product_name = extract_product_name_from_page(page)
    if not actual_product_name:
        logger.warning(f"[IDEALO] Could not extract product name from page")
        return False

    logger.info(f"[IDEALO] Product name found on page: {actual_product_name}")

    # Check brand mismatch
    expected_brand = expected["brand"]
    brand_found = expected_brand.lower() in actual_product_name.lower()

    if not brand_found:
        logger.warning(f"[IDEALO] Product brand mismatch detected!")
        logger.warning(f"[IDEALO] Expected: {expected_brand} product (from URL)")
        logger.warning(f"[IDEALO] Actual product: {actual_product_name}")

        # Log critical error and recommendation
        logger.error(f"[IDEALO] CRITICAL: URL {original_url} serves wrong product!")
        logger.error(
            f"[IDEALO] This URL should be removed or corrected in produits.csv"
        )

        return True

    # Check model keywords mismatch (if we have specific model keywords)
    model_keywords = expected.get("model_keywords", [])
    if model_keywords:
        # Check if at least one model keyword is found
        model_found = any(
            keyword.lower() in actual_product_name.lower()
            for keyword in model_keywords
            if len(keyword) > 2  # Skip very short keywords
        )

        if not model_found:
            logger.warning(f"[IDEALO] Product model mismatch detected!")
            logger.warning(f"[IDEALO] Expected keywords: {model_keywords} (from URL)")
            logger.warning(f"[IDEALO] Actual product: {actual_product_name}")

            # Log critical error and recommendation
            logger.error(f"[IDEALO] CRITICAL: URL {original_url} serves wrong product!")
            logger.error(
                f"[IDEALO] This URL should be removed or corrected in produits.csv"
            )

            return True

    logger.info(f"[IDEALO] Product matches expected content: {actual_product_name}")
    return False


def handle_cookie_consent(page: Page):
    """Handle Idealo cookie consent dialog."""
    try:
        # Look for common consent button patterns
        consent_selectors = [
            'button:has-text("Accepter")',
            'button:has-text("Accept")',
            'button:has-text("Tout accepter")',
            'button:has-text("Accept all")',
            '[data-testid="accept"]',
            ".cookie-consent button",
            "#cookie-consent button",
        ]

        for selector in consent_selectors:
            try:
                consent_button = page.locator(selector).first
                if consent_button.is_visible():
                    logger.info(f"[IDEALO] Found cookie consent button: {selector}")
                    consent_button.click()
                    page.wait_for_timeout(2000)  # Wait for consent to process
                    logger.info(f"[IDEALO] Successfully accepted cookie consent")
                    return
            except Exception as e:
                logger.debug(f"[IDEALO] Consent selector {selector} failed: {e}")
                continue

        logger.debug(f"[IDEALO] No cookie consent dialog found")

    except Exception as e:
        logger.warning(f"[IDEALO] Cookie consent handling failed: {e}")


def handle_idealo_page(page: Page, url: str) -> bool:
    """
    Handle Idealo-specific page processing.

    Returns True if page is valid for price extraction, False if should be skipped.
    """
    try:
        # Handle cookie consent
        handle_cookie_consent(page)

        # Wait for page to stabilize
        page.wait_for_timeout(3000)

        # Check for product mismatch
        mismatch_detected = check_product_mismatch(page, url)

        if mismatch_detected:
            logger.error(
                f"[IDEALO] Skipping price extraction due to product mismatch: {url}"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"[IDEALO] Page handling failed for {url}: {e}")
        return False
