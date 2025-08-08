"""
Generic site handler for coordinating all site-specific functionality.

This module provides a unified interface for handling different e-commerce sites,
routing requests to appropriate site-specific modules.
"""

import logging
from bs4 import BeautifulSoup
from playwright.sync_api import Page

from .amazon import is_amazon_url, extract_amazon_price, clean_amazon_url
from .idealo import handle_idealo_page
from .topachat import wait_for_topachat_price, extract_topachat_price
from .pccomponentes import emulate_pccomponentes_user
from .config import is_site_supported
from utils import clean_price

logger = logging.getLogger(__name__)


def clean_url_for_site(url: str) -> str:
    """Clean URL based on site-specific requirements."""
    if is_amazon_url(url):
        return clean_amazon_url(url)
    # Add other site-specific URL cleaning here
    return url


def handle_site_specific_page_setup(page: Page, url: str) -> bool:
    """
    Handle site-specific page setup and validation.

    Returns True if page is ready for price extraction, False if should skip.
    """
    is_topachat = is_site_supported(url, "topachat.com")
    is_pccomponentes = is_site_supported(url, "pccomponentes.fr")
    is_idealo = is_site_supported(url, "idealo.fr")

    if is_pccomponentes:
        emulate_pccomponentes_user(page)
    elif is_topachat:
        wait_for_topachat_price(page)
    elif is_idealo:
        # Handle Idealo-specific processing (cookies, mismatch detection, etc.)
        if not handle_idealo_page(page, url):
            # Page validation failed (product mismatch), skip price extraction
            return False

    return True


def extract_price_for_site(
    soup: BeautifulSoup, url: str, site_selectors: list, method: str = ""
) -> str:
    """
    Extract price using site-specific logic.

    Args:
        soup: BeautifulSoup object of the page
        url: URL being processed
        site_selectors: List of CSS selectors to try
        method: Method used for extraction (for logging)

    Returns:
        Price string if found, None otherwise
    """
    # Check if this is a site with special handling
    if is_amazon_url(url):
        return extract_amazon_price(soup, site_selectors, method)

    # Check if TopAchat requires special extraction
    is_topachat = is_site_supported(url, "topachat.com")

    # Generic price extraction for all other sites
    for selector in site_selectors:
        if method == "requests":
            # For requests method, use select_one
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = clean_price(price_text)
                if price:
                    return price
        else:
            # For Playwright method, use select (multiple elements)
            price_elems = soup.select(selector)
            if price_elems:
                for elem in price_elems:
                    if is_topachat:
                        price = extract_topachat_price(elem)
                    else:
                        text = elem.get_text(strip=True)
                        price = clean_price(text)
                    if price:
                        return price

    return None


def get_site_info(url: str) -> dict:
    """Get information about the site being processed."""
    return {
        "is_amazon": is_amazon_url(url),
        "is_topachat": is_site_supported(url, "topachat.com"),
        "is_pccomponentes": is_site_supported(url, "pccomponentes.fr"),
        "is_idealo": is_site_supported(url, "idealo.fr"),
    }
