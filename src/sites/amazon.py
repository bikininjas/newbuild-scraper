"""
Amazon.fr site-specific handling.

This module handles:
- URL cleaning (removing wishlist parameters)
- Amazon-specific debugging and logging
- Price extraction with Amazon-specific selectors
"""

import logging
from bs4 import BeautifulSoup
from utils import clean_price

logger = logging.getLogger(__name__)

# Amazon-specific constants
AMAZON_DOMAIN = "amazon."
WISHLIST_COLIID = "coliid="
WISHLIST_COLID = "colid="


def clean_amazon_url(url: str) -> str:
    """Clean Amazon URLs by removing wishlist parameters that can cause issues."""
    if AMAZON_DOMAIN in url and (WISHLIST_COLIID in url or WISHLIST_COLID in url):
        # Extract the core product URL
        if "/dp/" in url:
            dp_part = url.split("/dp/")[1].split("/")[0].split("?")[0]
            clean_url = url.split("/dp/")[0] + f"/dp/{dp_part}/"
            logger.info(f"Cleaned Amazon wishlist URL: {url} -> {clean_url}")
            return clean_url
    return url


def is_amazon_url(url: str) -> bool:
    """Check if URL is an Amazon URL."""
    return AMAZON_DOMAIN in url


def log_amazon_page_info(soup: BeautifulSoup, method: str = ""):
    """Log Amazon page information for debugging."""
    method_prefix = f" ({method})" if method else ""
    logger.info(
        f"Amazon page title{method_prefix}: {soup.title.string if soup.title else 'No title'}"
    )


def log_amazon_price_found(selector: str, price: str, method: str = ""):
    """Log when Amazon price is found."""
    method_prefix = f" {method}" if method else ""
    logger.info(f"Found Amazon price with{method_prefix} selector '{selector}': '{price}'")


def log_amazon_price_elements(soup: BeautifulSoup, method: str = ""):
    """Log available Amazon price elements for debugging."""
    method_prefix = f" ({method})" if method else ""
    all_price_elems = soup.select("[class*='price'], [id*='price']")
    logger.info(
        f"Amazon price elements found{method_prefix}: {[elem.get('class', []) + [elem.get('id', '')] for elem in all_price_elems[:5]]}"
    )


def extract_amazon_price(soup: BeautifulSoup, site_selectors: list, method: str = "") -> str:
    """
    Extract price from Amazon page with Amazon-specific debugging.

    Args:
        soup: BeautifulSoup object of the page
        site_selectors: List of CSS selectors to try
        method: Method used (for logging)

    Returns:
        Price string if found, None otherwise
    """
    # Log page info
    log_amazon_page_info(soup, method)

    # Try each selector
    for selector in site_selectors:
        price_elems = soup.select(selector)
        if price_elems:
            for elem in price_elems:
                price_text = elem.get_text(strip=True)
                price = clean_price(price_text)
                if price:
                    log_amazon_price_found(selector, price, method)
                    return price

    # Log available elements for debugging
    log_amazon_price_elements(soup, method)

    return None


def handle_amazon_page(page, url: str) -> str:
    """
    Handle Amazon-specific page processing.

    Returns cleaned URL for processing.
    """
    # Clean the URL
    cleaned_url = clean_amazon_url(url)

    # Additional Amazon-specific handling could go here
    # (cookies, captcha handling, etc.)

    return cleaned_url
