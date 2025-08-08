"""Refactored scraper with modular site and anti-bot handling."""

import sys
import time
import random
import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from sites.config import SITE_SELECTORS, DEFAULT_SELECTORS, is_site_supported
from sites.handler import (
    clean_url_for_site,
    handle_site_specific_page_setup,
    extract_price_for_site,
)
from utils import clean_price, get_user_agent
from antibot.stealth import (
    get_stealth_context_options,
    get_stealth_browser_args,
    add_stealth_scripts,
    should_use_stealth_mode,
)
from antibot.detection import (
    detect_anti_bot_protection,
    handle_cloudflare_protection,
    get_anti_bot_wait_time,
)


def get_price_requests(url, site_selectors):
    """Get price using requests (faster but less reliable for protected sites)."""
    headers = {"User-Agent": get_user_agent()}

    # Clean URLs based on site-specific requirements
    url = clean_url_for_site(url)

    time.sleep(random.uniform(2, 5))
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Fetched {url} with requests, status {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"Non-200 status code for {url}: {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Use site-specific price extraction
        price = extract_price_for_site(soup, url, site_selectors, "requests")
        if price:
            return price

        logging.warning(
            f"No price found for {url} with selectors {site_selectors} (requests)"
        )
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None


def setup_browser_context(use_stealth):
    """Set up browser context with appropriate options."""
    if use_stealth:
        return get_stealth_context_options()
    else:
        return {
            "user_agent": get_user_agent(),
            "locale": "fr-FR",
            "extra_http_headers": {
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
            },
        }


def handle_site_specific_behavior(page, url):
    """Handle site-specific behavior and waits."""
    # Use the generic handler
    if not handle_site_specific_page_setup(page, url):
        # Page validation failed, skip processing
        return None

    # Wait based on site's anti-bot protection level
    wait_time = get_anti_bot_wait_time(url)
    page.wait_for_timeout(wait_time)


def process_page_content(page):
    """Process page content and handle anti-bot protection."""
    content = page.content()
    if detect_anti_bot_protection(content) and "cloudflare" in content.lower():
        handle_cloudflare_protection(page)
        # Get updated content
    return content


def should_use_headless_mode(is_linux, url, use_stealth):
    # Use headless mode on Linux CI/CD runners to avoid X server errors
    import os

    is_ci = any(
        os.environ.get(var)
        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "TRAVIS"]
    )
    return (
        True
        if (is_linux and is_ci)
        else not (is_site_supported(url, "pccomponentes.fr") or use_stealth)
    )


def get_price_playwright(url, site_selectors):
    """Get price using Playwright (more reliable for protected sites)."""
    # Clean URLs based on site-specific requirements
    original_url = url
    url = clean_url_for_site(url)
    if url != original_url:
        logging.info(f"Cleaned URL for Playwright: {original_url} -> {url}")

    use_stealth = should_use_stealth_mode(url)

    try:
        with sync_playwright() as p:
            # Always use headless mode on Linux runners to avoid X server errors
            is_linux = sys.platform.startswith("linux")
            headless_mode = should_use_headless_mode(is_linux, url, use_stealth)

            # Get browser arguments based on stealth requirements
            browser_args = get_stealth_browser_args() if use_stealth else []
            browser = p.chromium.launch(headless=headless_mode, args=browser_args)

            # Set up context
            context_options = setup_browser_context(use_stealth)
            context = browser.new_context(**context_options)
            page = context.new_page()

            # Add stealth scripts if needed
            if use_stealth:
                add_stealth_scripts(page)

            # Navigate with appropriate wait strategy
            wait_until = "domcontentloaded" if use_stealth else "load"
            page.goto(url, timeout=45000, wait_until=wait_until)

            # Handle site-specific behavior
            handle_site_specific_behavior(page, url)

            # Process page content and handle anti-bot protection
            content = process_page_content(page)

            # Parse content and extract price using site-specific logic
            soup = BeautifulSoup(content, "html.parser")
            price = extract_price_for_site(soup, url, site_selectors, "Playwright")

            browser.close()

            if price:
                return price

            logging.warning(
                f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}"
            )

            # Log if anti-bot was detected
            if detect_anti_bot_protection(content):
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")

    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None
