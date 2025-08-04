"""Refactored scraper with modular site and anti-bot handling."""

import time
import random
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests

from utils import get_user_agent, clean_price
from sites.config import get_site_selector, is_site_supported
from sites.pccomponentes import emulate_pccomponentes_user
from sites.topachat import wait_for_topachat_price, extract_topachat_price
from antibot.stealth import (
    get_stealth_browser_args, 
    get_stealth_context_options, 
    add_stealth_scripts,
    should_use_stealth_mode
)
from antibot.detection import (
    detect_anti_bot_protection, 
    get_anti_bot_wait_time,
    handle_cloudflare_protection
)


def get_price_requests(url, site_selectors):
    """Get price using requests (faster but less reliable for protected sites)."""
    headers = {"User-Agent": get_user_agent()}
    time.sleep(random.uniform(2, 5))
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Fetched {url} with requests, status {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"Non-200 status code for {url}: {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for selector in site_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                return clean_price(price_elem.get_text())
        logging.warning(
            f"No price found for {url} with selectors {site_selectors} (requests)"
        )
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None


def extract_price_from_elems(price_elems, is_topachat):
    """Extract price from found elements."""
    for elem in price_elems:
        if is_topachat:
            price = extract_topachat_price(elem)
        else:
            text = elem.get_text(strip=True)
            price = clean_price(text)
        if price:
            return price
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
    is_topachat = is_site_supported(url, "topachat.com")
    is_pccomponentes = is_site_supported(url, "pccomponentes.fr")
    
    if is_pccomponentes:
        emulate_pccomponentes_user(page)
    elif is_topachat:
        wait_for_topachat_price(page)
    
    # Wait based on site's anti-bot protection level
    wait_time = get_anti_bot_wait_time(url)
    page.wait_for_timeout(wait_time)


def process_page_content(page):
    """Process page content and handle anti-bot protection."""
    content = page.content()
    if detect_anti_bot_protection(content) and 'cloudflare' in content.lower():
        handle_cloudflare_protection(page)
        content = page.content()  # Get updated content
    return content


def get_price_playwright(url, site_selectors):
    """Get price using Playwright (more reliable for protected sites)."""
    is_topachat = is_site_supported(url, "topachat.com")
    use_stealth = should_use_stealth_mode(url)

    try:
        with sync_playwright() as p:
            # Use non-headless mode for sites that require stealth
            headless_mode = not (is_site_supported(url, "pccomponentes.fr") or use_stealth)
            
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
            
            # Parse content and extract price
            soup = BeautifulSoup(content, "html.parser")

            for selector in site_selectors:
                price_elems = soup.select(selector)
                if price_elems:
                    price = extract_price_from_elems(price_elems, is_topachat)
                    if price is not None:
                        browser.close()
                        return price

            browser.close()
            logging.warning(
                f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}"
            )
            
            # Log if anti-bot was detected
            if detect_anti_bot_protection(content):
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")
                
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None


# Maintain backward compatibility by re-exporting the original function
get_site_selector = get_site_selector
