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
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional, List

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

        def is_valid_product_jsonld(obj):
            """Validate that JSON-LD object is a trusted Product schema."""
            return (
                isinstance(obj, dict)
                and obj.get("@context") in ["https://schema.org", "http://schema.org"]
                and obj.get("@type") == "Product"
            )

        for script in json_scripts:
            try:
                script_content = script.text_content()
                if script_content:
                    data = json.loads(script_content)
                    # Look for product name in validated JSON-LD
                    if isinstance(data, dict) and is_valid_product_jsonld(data):
                        name = data.get("name") or data.get("@name")
                        if name and len(name.strip()) > 5:
                            product_name = name.strip()
                            break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and is_valid_product_jsonld(item):
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
        logger.warning("[IDEALO] Could not extract product name from page")
        return False

    logger.info(f"[IDEALO] Product name found on page: {actual_product_name}")

    # Check brand mismatch
    expected_brand = expected["brand"]
    brand_found = expected_brand.lower() in actual_product_name.lower()

    if not brand_found:
        logger.warning("[IDEALO] Product brand mismatch detected!")
        logger.warning(f"[IDEALO] Expected: {expected_brand} product (from URL)")
        logger.warning(f"[IDEALO] Actual product: {actual_product_name}")

        # Log critical error with actionable guidance
        logger.error(
            f"[IDEALO] CRITICAL: Product mismatch detected for URL: {original_url}\n"
            f"  Expected brand: {expected_brand} (from URL)\n"
            f"  Actual product name: {actual_product_name}\n"
            f"  ACTION: Please update or remove this URL from produits.csv."
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
            logger.warning("[IDEALO] Product model mismatch detected!")
            logger.warning(f"[IDEALO] Expected keywords: {model_keywords} (from URL)")
            logger.warning(f"[IDEALO] Actual product: {actual_product_name}")

            # Log critical error and recommendation
            logger.error(f"[IDEALO] CRITICAL: URL {original_url} serves wrong product!")
            logger.error(
                "[IDEALO] This URL should be removed or corrected in produits.csv"
            )

            return True

    logger.info(f"[IDEALO] Product matches expected content: {actual_product_name}")
    return False


def handle_cookie_consent(page: Page):
    """Handle Idealo cookie consent dialog."""
    try:
        # Wait for potential consent dialog to appear
        page.wait_for_timeout(2000)

        # Look for common consent button patterns including Idealo-specific ones
        consent_selectors = [
            'button:has-text("Accepter")',
            'button:has-text("Accept")',
            'button:has-text("Tout accepter")',
            'button:has-text("Accept all")',
            'button:has-text("Akzeptieren")',  # German
            '[data-testid="accept"]',
            '[data-testid="accept-button"]',
            ".cookie-consent button",
            "#cookie-consent button",
            ".consent-dialog button",
            ".consent button",
            'button[class*="consent"]',
            'button[class*="accept"]',
            'iframe button:has-text("Accepter")',  # For iframe-based consent
            'iframe button:has-text("Accept")',
        ]

        # Check for iframe-based consent dialogs first
        try:
            iframes = page.locator("iframe").all()
            for iframe in iframes:
                try:
                    iframe_content = iframe.content_frame()
                    if iframe_content:
                        for selector in [
                            'button:has-text("Accepter")',
                            'button:has-text("Accept")',
                        ]:
                            try:
                                consent_button = iframe_content.locator(selector).first
                                if consent_button.is_visible():
                                    logger.info(
                                        f"[IDEALO] Found iframe cookie consent button: {selector}"
                                    )
                                    consent_button.click()
                                    page.wait_for_timeout(3000)
                                    logger.info(
                                        "[IDEALO] Successfully accepted iframe cookie consent"
                                    )
                                    return
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[IDEALO] Iframe consent check failed: {e}")

        # Try main page consent buttons
        for selector in consent_selectors:
            try:
                consent_button = page.locator(selector).first
                if consent_button.is_visible():
                    logger.info(f"[IDEALO] Found cookie consent button: {selector}")
                    consent_button.click()
                    page.wait_for_timeout(3000)  # Wait for consent to process
                    logger.info("[IDEALO] Successfully accepted cookie consent")
                    return
            except Exception as e:
                logger.debug(f"[IDEALO] Consent selector {selector} failed: {e}")
                continue

        logger.debug("[IDEALO] No cookie consent dialog found")

    except Exception as e:
        logger.warning(f"[IDEALO] Cookie consent handling failed: {e}")


def extract_price_from_meta_description(page: Page) -> str:
    """Extract price from Idealo meta description tag."""
    try:
        # Get meta description content
        meta_desc = page.locator('meta[name="description"]').first
        if meta_desc:
            content = meta_desc.get_attribute("content")
            if content:
                # Look for price pattern: "à partir de X,XX€" or "X,XX€"
                price_pattern = (
                    r"à partir de ([\d,]+)(?:&nbsp;)?€|(\d+,\d+)(?:&nbsp;)?€"
                )
                match = re.search(price_pattern, content)
                if match:
                    price = match.group(1) or match.group(2)
                    if price:
                        # Convert comma to dot for standardization
                        price = price.replace(",", ".")
                        logger.info(
                            f"[IDEALO] Found price in meta description: {price}€"
                        )
                        return f"{price}€"

        logger.debug("[IDEALO] No price found in meta description")
        return ""

    except Exception as e:
        logger.debug(f"[IDEALO] Meta description price extraction failed: {e}")
        return ""


def extract_vendor_offers(page: Page, soup: BeautifulSoup) -> List[Dict]:
    """
    Extract vendor offers from Idealo page.

    Returns list of offers with vendor name, price, and potential redirect URL.
    """
    offers = []

    try:
        # Strategy 1: Look for offer items in the price comparison table
        offer_selectors = [
            ".productOffers-listItem",
            ".product-offers-item",
            ".offer-item",
            '[data-testid*="offer"]',
            ".price-comparison-item",
        ]

        for selector in offer_selectors:
            offer_elements = soup.select(selector)
            if offer_elements:
                logger.info(
                    f"[IDEALO] Found {len(offer_elements)} offers using selector: {selector}"
                )

                for i, offer_elem in enumerate(
                    offer_elements[:5]
                ):  # Limit to top 5 offers
                    try:
                        # Extract vendor name - Updated selectors based on screenshots
                        vendor_name = None

                        # Strategy 1: Look for data-shop-name attribute (most reliable)
                        shop_elem = offer_elem.select_one("[data-shop-name]")
                        if shop_elem:
                            raw_vendor_name = shop_elem.get(
                                "data-shop-name", ""
                            ).strip()
                            if raw_vendor_name:
                                # Clean up the vendor name - remove product categories and location info
                                vendor_name = raw_vendor_name

                                # Remove product category prefix (e.g., "SSD - ")
                                if " - " in vendor_name:
                                    parts = vendor_name.split(" - ")
                                    # Find the part that looks like a vendor domain or known retailer
                                    for part in parts:
                                        part_lower = part.lower()
                                        if any(
                                            domain in part_lower
                                            for domain in [
                                                ".fr",
                                                ".com",
                                                ".net",
                                                "amazon",
                                                "fnac",
                                                "ldlc",
                                                "materiel",
                                                "corsair",
                                                "topachat",
                                                "cdiscount",
                                                "darty",
                                                "boulanger",
                                                "rueducommerce",
                                            ]
                                        ):
                                            vendor_name = part
                                            break

                                    # If no obvious vendor found, take the second part (after category)
                                    if (
                                        vendor_name == raw_vendor_name
                                        and len(parts) >= 2
                                    ):
                                        vendor_name = parts[1]

                                # Remove location info (e.g., " - Marchand de Paris")
                                if " - Marchand de " in vendor_name:
                                    vendor_name = vendor_name.split(" - Marchand de ")[
                                        0
                                    ]

                                # Clean up marketplace indicators
                                vendor_name = vendor_name.replace(
                                    " (Marketplace)", ""
                                ).strip()

                                logger.debug(
                                    f"[IDEALO] Found vendor via data-shop-name: {vendor_name} (cleaned from: {raw_vendor_name})"
                                )

                        # Strategy 2: Look for aria-label with vendor info
                        if not vendor_name:
                            aria_elem = offer_elem.select_one('[aria-label*="chez"]')
                            if aria_elem:
                                aria_label = aria_elem.get("aria-label", "")
                                # Extract vendor from "Voir l'offre de Amazon.fr" pattern
                                if "chez " in aria_label:
                                    vendor_name = aria_label.split("chez ")[-1].strip()
                                elif " de " in aria_label:
                                    vendor_name = aria_label.split(" de ")[-1].strip()
                                if vendor_name:
                                    logger.debug(
                                        f"[IDEALO] Found vendor via aria-label: {vendor_name}"
                                    )

                        # Strategy 3: Look for shop logo images with alt text
                        if not vendor_name:
                            logo_selectors = [
                                ".productOffers-listItemOfferShop2LogoImage img",
                                ".productOffers-listItemOfferShopLogoImage img",
                                ".shop-logo img",
                                'img[alt*="logo"]',
                                'img[src*="logo"]',
                            ]

                            for logo_sel in logo_selectors:
                                logo_img = offer_elem.select_one(logo_sel)
                                if logo_img:
                                    alt_text = logo_img.get("alt", "").strip()
                                    if alt_text and not alt_text.lower().endswith(
                                        "logo"
                                    ):
                                        vendor_name = (
                                            alt_text.replace(" logo", "")
                                            .replace("-logo", "")
                                            .strip()
                                        )
                                        logger.debug(
                                            f"[IDEALO] Found vendor via logo alt: {vendor_name}"
                                        )
                                        break

                        # Strategy 4: Look for common vendor names in links or text
                        if not vendor_name:
                            common_vendors = [
                                "amazon",
                                "ldlc",
                                "materiel.net",
                                "topachat",
                                "cdiscount",
                                "fnac",
                                "darty",
                                "boulanger",
                            ]
                            offer_text = offer_elem.get_text().lower()
                            for vendor in common_vendors:
                                if vendor in offer_text:
                                    vendor_name = vendor.title()
                                    logger.debug(
                                        f"[IDEALO] Found vendor via text search: {vendor_name}"
                                    )
                                    break

                        # Extract price
                        price = None
                        price_selectors = [
                            ".productOffers-listItemOfferPrice",
                            ".offer-price",
                            ".price",
                            '[data-testid*="price"]',
                            ".productOffers-listItemOfferPriceValue",
                        ]

                        for price_sel in price_selectors:
                            price_elem = offer_elem.select_one(price_sel)
                            if price_elem:
                                price_text = price_elem.get_text(strip=True)
                                price_match = re.search(
                                    r"(\d+(?:,\d+)?)\s*€", price_text
                                )
                                if price_match:
                                    price = price_match.group(1).replace(",", ".")
                                    logger.debug(f"[IDEALO] Found price: {price}€")
                                    break

                        # Extract offer URL/link - improved to find the actual redirect URL
                        offer_url = None
                        link_selectors = [
                            'a[href*="/relocator/relocate"]',  # Idealo redirects
                            'a[href*="/go/"]',
                            'a[href*="redirect"]',
                            'a[href*="clickout"]',
                            'a[data-testid*="offer-link"]',
                            ".offer-link a",
                            'a[href*="idealo."]',
                        ]

                        for link_sel in link_selectors:
                            link_elem = offer_elem.select_one(link_sel)
                            if link_elem and link_elem.get("href"):
                                href = link_elem.get("href")
                                if href and (
                                    "/relocator/" in href
                                    or "/go/" in href
                                    or "redirect" in href
                                    or "clickout" in href
                                ):
                                    # Convert relative URLs to absolute
                                    if href.startswith("/"):
                                        offer_url = f"https://www.idealo.fr{href}"
                                    else:
                                        offer_url = href
                                    logger.debug(
                                        f"[IDEALO] Found redirect URL: {offer_url[:80]}..."
                                    )
                                    break

                        if vendor_name and price:
                            offer = {
                                "vendor": vendor_name,
                                "price": f"{price}€",
                                "redirect_url": offer_url,
                                "position": i + 1,
                            }
                            offers.append(offer)
                            logger.info(
                                f"[IDEALO] Extracted offer: {vendor_name} - {price}€"
                            )
                        elif vendor_name:
                            logger.debug(
                                f"[IDEALO] Found vendor {vendor_name} but no price"
                            )
                        elif price:
                            logger.debug(f"[IDEALO] Found price {price}€ but no vendor")

                    except Exception as e:
                        logger.debug(f"[IDEALO] Failed to extract offer {i}: {e}")
                        continue

                if offers:
                    break  # Found offers with this selector

        logger.info(f"[IDEALO] Total offers extracted: {len(offers)}")
        return offers

    except Exception as e:
        logger.error(f"[IDEALO] Vendor extraction failed: {e}")
        return []


def follow_vendor_redirect(
    page: Page, redirect_url: str, base_url: str
) -> Optional[str]:
    """
    Follow Idealo redirect to get the actual vendor URL.

    Returns the final vendor URL or None if failed.
    """
    try:
        if not redirect_url:
            return None

        # Make URL absolute if needed
        if redirect_url.startswith("/"):
            redirect_url = urljoin(base_url, redirect_url)

        logger.info(f"[IDEALO] Following redirect: {redirect_url}")

        # Follow the redirect
        response = page.goto(redirect_url, timeout=15000, wait_until="domcontentloaded")

        if response and response.ok:
            final_url = page.url
            domain = urlparse(final_url).netloc

            # Handle vendor-specific cookie consent
            handle_vendor_cookie_consent(page, final_url)

            # Filter out obviously bad redirects
            if domain and "idealo" not in domain and len(domain) > 3:
                logger.info(f"[IDEALO] Successfully redirected to: {domain}")
                return final_url

        logger.warning(f"[IDEALO] Redirect failed or invalid: {redirect_url}")
        return None

    except Exception as e:
        logger.debug(f"[IDEALO] Redirect follow failed: {e}")
        return None


def handle_vendor_cookie_consent(page: Page, vendor_url: str) -> None:
    """
    Handle cookie consent for different vendor sites.
    """
    try:
        domain = urlparse(vendor_url).netloc.lower()

        # Amazon cookie consent
        if "amazon." in domain:
            amazon_cookie_selectors = [
                'input[name="accept"][type="submit"]',  # Amazon "Accepter" button
                'button:has-text("Accepter")',
                'button:has-text("Accept")',
                "#sp-cc-accept",
                '[data-testid="cookie-accept"]',
            ]

            for selector in amazon_cookie_selectors:
                try:
                    cookie_button = page.locator(selector)
                    if cookie_button.count() > 0:
                        cookie_button.click()
                        logger.info(f"[IDEALO] Accepted Amazon cookie consent")
                        page.wait_for_timeout(2000)
                        return
                except Exception:
                    continue

        # Other vendor cookie consents can be added here
        elif "corsair.com" in domain:
            corsair_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accepter")',
                "#cookie-accept",
                ".cookie-accept",
            ]

            for selector in corsair_selectors:
                try:
                    cookie_button = page.locator(selector)
                    if cookie_button.count() > 0:
                        cookie_button.click()
                        logger.info(f"[IDEALO] Accepted Corsair cookie consent")
                        page.wait_for_timeout(1000)
                        return
                except Exception:
                    continue

    except Exception as e:
        logger.debug(f"[IDEALO] Cookie consent handling failed for {domain}: {e}")


def extract_best_vendor_info(page: Page, soup: BeautifulSoup) -> Dict:
    """
    Extract the best vendor offer from Idealo page.

    Returns dict with vendor info and potentially the vendor's actual URL.
    """
    try:
        offers = extract_vendor_offers(page, soup)

        if not offers:
            logger.warning("[IDEALO] No vendor offers found")
            return {}

        # Get the best offer (first one, usually lowest price)
        best_offer = offers[0]
        logger.info(
            f"[IDEALO] Best offer: {best_offer['vendor']} - {best_offer['price']}"
        )

        # Try to get the actual vendor URL
        vendor_url = None
        if best_offer.get("redirect_url"):
            vendor_url = follow_vendor_redirect(
                page, best_offer["redirect_url"], page.url
            )

        return {
            "vendor_name": best_offer["vendor"],
            "vendor_price": best_offer["price"],
            "vendor_url": vendor_url,
            "all_offers": offers[:3],  # Keep top 3 for reference
        }

    except Exception as e:
        logger.error(f"[IDEALO] Best vendor extraction failed: {e}")
        return {}


def extract_idealo_price_with_vendor(
    page: Page, soup: BeautifulSoup, site_selectors: list
) -> dict:
    """
    Extract price from Idealo with vendor information (wrapper for new format).

    Returns dict with price and vendor info.
    """
    # Get vendor info
    vendor_info = extract_best_vendor_info(page, soup)

    # Try to get actual vendor price
    if vendor_info.get("vendor_url") and vendor_info.get("vendor_name"):
        logger.info(
            f"[IDEALO] Found vendor redirect: {vendor_info['vendor_name']} -> {vendor_info['vendor_url']}"
        )

        try:
            # Navigate to vendor's page
            response = page.goto(
                vendor_info["vendor_url"], timeout=20000, wait_until="domcontentloaded"
            )
            if response and response.ok:
                page.wait_for_timeout(3000)

                # Get vendor's page content
                vendor_content = page.content()
                vendor_soup = BeautifulSoup(vendor_content, "html.parser")

                # Try to extract price from vendor's page
                vendor_price = extract_vendor_page_price(
                    vendor_soup, vendor_info["vendor_url"]
                )

                if vendor_price:
                    logger.info(
                        f"[IDEALO] Successfully got price from {vendor_info['vendor_name']}: {vendor_price}"
                    )

                    # Get Amazon marketplace and Prime info if applicable
                    is_marketplace, is_prime = get_amazon_info()
                    result = {
                        "price": vendor_price,
                        "vendor_name": vendor_info["vendor_name"],
                        "vendor_url": vendor_info["vendor_url"],
                    }

                    # Add Amazon-specific info if it's an Amazon vendor
                    if "amazon" in vendor_info.get("vendor_name", "").lower():
                        result["is_marketplace"] = is_marketplace
                        result["is_prime_eligible"] = is_prime

                    # Clear the Amazon info after use
                    clear_amazon_info()
                    return result
                else:
                    logger.warning(
                        f"[IDEALO] Could not extract price from {vendor_info['vendor_name']}, using Idealo price"
                    )

                    # Get Amazon info for fallback case too
                    is_marketplace, is_prime = get_amazon_info()
                    result = {
                        "price": vendor_info.get("vendor_price", ""),
                        "vendor_name": vendor_info["vendor_name"],
                        "vendor_url": vendor_info["vendor_url"],
                    }

                    if "amazon" in vendor_info.get("vendor_name", "").lower():
                        result["is_marketplace"] = is_marketplace
                        result["is_prime_eligible"] = is_prime

                    clear_amazon_info()
                    return result

        except Exception as e:
            logger.warning(
                f"[IDEALO] Vendor page scraping failed for {vendor_info['vendor_name']}: {e}"
            )
            # Fall back to Idealo's listed price for this vendor
            if vendor_info.get("vendor_price"):
                return {
                    "price": vendor_info["vendor_price"],
                    "vendor_name": vendor_info["vendor_name"],
                    "vendor_url": vendor_info.get("vendor_url"),
                }

    # Fall back to standard Idealo extraction
    price = extract_idealo_price(page, soup, site_selectors)
    result = {"price": price} if price else {}

    # Add vendor info if available
    if vendor_info.get("vendor_name"):
        result["vendor_name"] = vendor_info["vendor_name"]
    if vendor_info.get("vendor_url"):
        result["vendor_url"] = vendor_info["vendor_url"]

    return result


def extract_idealo_price(page: Page, soup: BeautifulSoup, site_selectors: list) -> str:
    """
    Extract price from Idealo with vendor information.

    Priority:
    1. Get best vendor offer and follow redirect to vendor's site
    2. Fall back to meta description
    3. Fall back to CSS selectors
    """

    # Strategy 1: Extract vendor offers and try to follow to actual vendor
    vendor_info = extract_best_vendor_info(page, soup)
    if vendor_info.get("vendor_url") and vendor_info.get("vendor_name"):
        logger.info(
            f"[IDEALO] Found vendor redirect: {vendor_info['vendor_name']} -> {vendor_info['vendor_url']}"
        )

        # Try to scrape the actual vendor's price
        try:
            # Navigate to vendor's page
            response = page.goto(
                vendor_info["vendor_url"], timeout=20000, wait_until="domcontentloaded"
            )
            if response and response.ok:
                page.wait_for_timeout(3000)  # Wait for page to stabilize

                # Get vendor's page content
                vendor_content = page.content()
                vendor_soup = BeautifulSoup(vendor_content, "html.parser")

                # Try to extract price from vendor's page using generic selectors
                vendor_price = extract_vendor_page_price(
                    vendor_soup, vendor_info["vendor_url"]
                )

                if vendor_price:
                    logger.info(
                        f"[IDEALO] Successfully got price from {vendor_info['vendor_name']}: {vendor_price}"
                    )
                    return vendor_price
                else:
                    logger.warning(
                        f"[IDEALO] Could not extract price from {vendor_info['vendor_name']}, using Idealo price"
                    )
                    return vendor_info.get("vendor_price", "")

        except Exception as e:
            logger.warning(
                f"[IDEALO] Vendor page scraping failed for {vendor_info['vendor_name']}: {e}"
            )
            # Fall back to Idealo's listed price for this vendor
            if vendor_info.get("vendor_price"):
                return vendor_info["vendor_price"]

    # Strategy 2: Try meta description
    price = extract_price_from_meta_description(page)
    if price:
        return price

    # Strategy 3: Fall back to CSS selectors
    logger.debug("[IDEALO] Vendor extraction failed, trying CSS selectors")

    for selector in site_selectors:
        try:
            price_elems = soup.select(selector)
            if price_elems:
                for elem in price_elems:
                    text = elem.get_text(strip=True)
                    if text and "€" in text:
                        # Extract price using regex
                        price_match = re.search(r"(\d+(?:,\d+)?)\s*€", text)
                        if price_match:
                            price = price_match.group(1).replace(",", ".")
                            logger.info(
                                f"[IDEALO] Found price via selector {selector}: {price}€"
                            )
                            return f"{price}€"
        except Exception as e:
            logger.debug(f"[IDEALO] Selector {selector} failed: {e}")
            continue

    logger.warning("[IDEALO] No price found using any method")
    return ""


def extract_vendor_page_price(soup: BeautifulSoup, vendor_url: str) -> str:
    """
    Extract price from the actual vendor page with enhanced Amazon support.
    """
    try:
        domain = urlparse(vendor_url).netloc.lower()
        logger.info(f"[IDEALO] Extracting price from {domain}...")

        # Amazon-specific extraction with marketplace and Prime detection
        if "amazon." in domain:
            return extract_amazon_price_and_info(soup, vendor_url)

        # Use existing generic extraction for other vendors
        from .config import SITE_SELECTORS, DEFAULT_SELECTORS

        selectors = DEFAULT_SELECTORS
        for site_domain, site_selectors in SITE_SELECTORS.items():
            if site_domain in domain:
                selectors = site_selectors
                break

        # Try to extract price
        for selector in selectors:
            try:
                price_elem = soup.select_one(selector)
                if price_elem:
                    text = price_elem.get_text(strip=True)
                    if text:
                        # Clean and extract price
                        price_match = re.search(
                            r"(\d+(?:[.,]\d+)?)", text.replace(",", ".")
                        )
                        if price_match:
                            price = price_match.group(1)
                            logger.info(f"[IDEALO] Vendor price found: {price}€")
                            return f"{price}€"
            except Exception as e:
                logger.debug(f"[IDEALO] Vendor selector {selector} failed: {e}")
                continue

        logger.warning(f"[IDEALO] No price found on vendor page: {domain}")
        return ""

    except Exception as e:
        logger.error(f"[IDEALO] Vendor price extraction failed: {e}")
        return ""


def extract_amazon_price_and_info(soup: BeautifulSoup, vendor_url: str) -> str:
    """
    Extract price from Amazon page with marketplace and Prime detection.
    Returns price string with marketplace and Prime indicators.
    """
    try:
        logger.info("[IDEALO] Extracting Amazon price with marketplace/Prime info...")

        # Amazon price selectors (try multiple formats)
        amazon_price_selectors = [
            ".a-price-whole",
            ".a-price .a-offscreen",
            "#priceblock_dealprice",
            "#priceblock_ourprice",
            ".a-price-range .a-price",
            ".a-price.a-text-price.a-size-medium.apexPriceToPay",
            "[data-asin-price]",
            ".a-price .a-text-price",
        ]

        price = None
        for selector in amazon_price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Handle different Amazon price formats
                price_match = re.search(
                    r"(\d+(?:[,\.]\d+)?)",
                    price_text.replace(" ", "").replace("\xa0", ""),
                )
                if price_match:
                    price = price_match.group(1).replace(",", ".")
                    logger.info(f"[IDEALO] Found Amazon price: {price}€ via {selector}")
                    break

        if not price:
            logger.warning("[IDEALO] No Amazon price found")
            return ""

        # Check if it's sold by Amazon or marketplace
        marketplace_info = ""
        seller_selectors = [
            "#tabular-buybox .a-color-secondary",
            "#merchant-info",
            ".soldBy",
            '[data-feature-name="desktop_buybox"] .a-color-secondary',
            "#availability .a-color-state",
        ]

        is_marketplace = False
        for selector in seller_selectors:
            seller_elem = soup.select_one(selector)
            if seller_elem:
                seller_text = seller_elem.get_text(strip=True).lower()
                if (
                    "vendu par" in seller_text or "sold by" in seller_text
                ) and "amazon" not in seller_text:
                    is_marketplace = True
                    marketplace_info = " (Marketplace)"
                    logger.info("[IDEALO] Amazon Marketplace seller detected")
                    break
                elif "amazon" in seller_text:
                    logger.info("[IDEALO] Sold by Amazon directly")
                    break

        # Check Prime eligibility
        prime_eligible = False
        prime_selectors = [
            ".prime-logo",
            '[aria-label*="Prime"]',
            ".a-icon-prime",
            ".prime-text",
            '[data-testid*="prime"]',
        ]

        for selector in prime_selectors:
            if soup.select_one(selector):
                prime_eligible = True
                logger.info("[IDEALO] Amazon Prime eligible")
                break

        # Also check for Prime in text content
        if not prime_eligible:
            page_text = soup.get_text().lower()
            if "prime" in page_text and (
                "livraison" in page_text
                or "gratuite" in page_text
                or "free" in page_text
            ):
                prime_eligible = True
                logger.info("[IDEALO] Amazon Prime eligible (text detection)")

        # Store the marketplace and Prime info globally for database insertion
        # We'll use a module-level variable to pass this information
        global _amazon_marketplace_info, _amazon_prime_info
        _amazon_marketplace_info = is_marketplace
        _amazon_prime_info = prime_eligible

        # Format the result with additional info
        result = f"{price}€"
        if marketplace_info:
            result += marketplace_info
        if prime_eligible:
            result += " (Prime)"

        logger.info(f"[IDEALO] Amazon final result: {result}")
        return result

    except Exception as e:
        logger.error(f"[IDEALO] Error extracting Amazon price: {e}")
        return ""


# Global variables to store Amazon marketplace and Prime info
_amazon_marketplace_info = False
_amazon_prime_info = False


def get_amazon_info() -> tuple[bool, bool]:
    """Get the last extracted Amazon marketplace and Prime information."""
    global _amazon_marketplace_info, _amazon_prime_info
    return _amazon_marketplace_info, _amazon_prime_info


def clear_amazon_info():
    """Clear the Amazon information cache."""
    global _amazon_marketplace_info, _amazon_prime_info
    _amazon_marketplace_info = False
    _amazon_prime_info = False


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
