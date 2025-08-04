import time
import random
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging
from utils import get_user_agent, clean_price

# Selector constants
PRICE = ".price"
PRICE_LG = ".price-lg"
PRODUCT_PRICE = ".product-price"
OLD_PRICE = ".old-price"
NEW_PRICE = ".new-price"

# Mouse movement coordinates for anti-bot detection
PCCOMPONENTES_MOUSE_MOVES = [
    (100, 200),
    (200, 300),
    (300, 400),
    (400, 500),
    (500, 600),
    (600, 700),
    (700, 800),
    (800, 900),
    (900, 1000),
    (1000, 1100),
]


def get_site_selector(url):
    # Extract site checks to variables for better performance
    is_topachat = "topachat.com" in url

    if "amazon.fr" in url:
        return [".a-price-whole"]
    if "caseking.de" in url:
        return [".js-unit-price"]
    if "ldlc.com" in url:
        return [PRICE, NEW_PRICE, ".price__amount"]
    if is_topachat:
        # Try multiple selectors for topachat.com, ordered from most specific to more generic
        return [
            ".offer-price__price.svelte-hgy1uf",
            ".offer-price__price",
            "span.offer-price__price",
        ]
    if "alternate.fr" in url:
        return [PRICE, ".product-detail-price"]
    if "materiel.net" in url:
        return [".o-product__price", ".o-product__price o-product__price--promo"]
    if "pccomponents.fr" in url:
        return [".pdp-price-current-integer"]
    if "grosbill.com" in url:
        return [".p-3x"]
    if "idealo.fr" in url:
        return [".productOffers-listItemOfferPrice"]
    if "bpm-power.com" in url:
        return [".prezzoSchedaProd"]
    if "rueducommerce.fr" in url:
        return [PRICE]
    return [PRICE, PRODUCT_PRICE, "#price"]


def get_price_requests(url, site_selectors):
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
            else:
                pass
        logging.warning(
            f"No price found for {url} with selectors {site_selectors}. HTML snippet: {resp.text[:500]}"
        )
        if "captcha" in resp.text.lower() or "robot" in resp.text.lower():
            logging.warning(f"Possible anti-bot detected for {url}")
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None


def get_price_playwright(url, site_selectors):
    # Extract site checks to variables to avoid repeated string operations
    is_topachat = "topachat.com" in url
    is_pccomponentes = "pccomponentes.fr" in url

    try:
        with sync_playwright() as p:
            # Use non-headless mode for pccomponentes.fr
            headless_mode = not is_pccomponentes
            browser = p.chromium.launch(headless=headless_mode)
            # Add realistic headers
            context = browser.new_context(
                user_agent=get_user_agent(),
                locale="fr-FR",
                extra_http_headers={
                    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "no-cache",
                },
            )
            page = context.new_page()
            page.goto(url, timeout=30000)
            # Emulate user actions for pccomponentes.fr
            if is_pccomponentes:
                try:
                    for x, y in PCCOMPONENTES_MOUSE_MOVES:
                        page.mouse.move(x, y)
                    page.keyboard.press("PageDown")
                    page.keyboard.press("PageDown")
                    page.keyboard.press("ArrowDown")
                    page.keyboard.press("ArrowDown")
                    page.wait_for_timeout(5000)
                except Exception as e:
                    logging.warning(
                        f"[Playwright] User emulation failed for {url}: {e}"
                    )
            # For topachat, just wait for price element to appear
            if is_topachat:
                try:
                    page.wait_for_selector(".offer-price__price", timeout=10000)
                except Exception:
                    logging.warning(
                        f"[Playwright] .offer-price__price not found after wait for {url}"
                    )
            # Wait longer for pccomponentes.fr
            if is_pccomponentes:
                page.wait_for_timeout(7000)
            else:
                page.wait_for_timeout(3000)
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            def close_and_return(val):
                browser.close()
                return val

            found_price = None
            for selector in site_selectors:
                price_elems = soup.select(selector)
                if price_elems:
                    for elem in price_elems:
                        if is_topachat:
                            direct_texts = [t for t in elem.strings if t.strip()]
                            main_text = (
                                direct_texts[0]
                                if direct_texts
                                else elem.get_text(strip=True)
                            )
                            match = re.search(r"([\d.,]+)\s*€", main_text)
                            if match:
                                price_str = match.group(1)
                                price = clean_price(price_str)
                                if price:
                                    found_price = price
                                    break
                            if "€" in main_text:
                                price_str = main_text.split("€")[0].strip()
                                price = clean_price(price_str)
                                if price:
                                    found_price = price
                                    break
                        else:
                            text = elem.get_text(strip=True)
                            price = clean_price(text)
                            if price:
                                found_price = price
                                break
                    if found_price is not None:
                        return close_and_return(found_price)
            browser.close()
            logging.warning(
                f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}"
            )
            if "captcha" in content.lower() or "robot" in content.lower():
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None
