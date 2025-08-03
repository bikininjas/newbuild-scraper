import time
import random
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


def get_site_selector(url):
    if "amazon.fr" in url:
        return [".a-price-whole"]
    if "caseking.de" in url:
        return [".js-unit-price"]
    if "ldlc.com" in url:
        return [PRICE, NEW_PRICE, ".price__amount"]
    if "topachat.com" in url:
        return [".offer-price__price svelte-hgy1uf"]
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
                logging.info(f"Selector '{selector}' matched for {url}")
                return clean_price(price_elem.get_text())
            else:
                logging.debug(f"Selector '{selector}' did not match for {url}")
        logging.warning(
            f"No price found for {url} with selectors {site_selectors}. HTML snippet: {resp.text[:500]}"
        )
        if "captcha" in resp.text.lower() or "robot" in resp.text.lower():
            logging.warning(f"Possible anti-bot detected for {url}")
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None


def get_price_playwright(url, site_selectors):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")
            for selector in site_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    logging.info(
                        f"Selector '{selector}' matched for {url} (Playwright)"
                    )
                    browser.close()
                    return clean_price(price_elem.get_text())
                else:
                    logging.debug(
                        f"Selector '{selector}' did not match for {url} (Playwright)"
                    )
            browser.close()
            logging.warning(
                f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}"
            )
            if "captcha" in content.lower() or "robot" in content.lower():
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None
