
import time
import random
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging
from .utils import get_user_agent, clean_price

# Selector constants
PRICE = '.price'
PRICE_LG = '.price-lg'
PRODUCT_PRICE = '.product-price'

def get_site_selector(url):
    if 'amazon.' in url:
        return ['.a-price .a-offscreen', '#priceblock_ourprice', '#priceblock_dealprice', '.a-price-whole']
    if 'ldlc.com' in url:
        return [PRICE, '.price__amount', PRICE_LG]
    if 'topachat.com' in url:
        return ['.prodPrice', PRODUCT_PRICE, PRICE]
    if 'alternate.fr' in url:
        return [PRICE, '.product-detail-price', PRICE_LG]
    if 'materiel.net' in url:
        return [PRODUCT_PRICE, PRICE, PRICE_LG]
    return [PRICE, PRODUCT_PRICE, '#price', '.a-price-whole']

def get_price_requests(url, site_selectors):
    headers = {'User-Agent': get_user_agent()}
    time.sleep(random.uniform(2, 5))
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Fetched {url} with requests, status {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"Non-200 status code for {url}: {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for selector in site_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                logging.info(f"Selector '{selector}' matched for {url}")
                return clean_price(price_elem.get_text())
            else:
                logging.debug(f"Selector '{selector}' did not match for {url}")
        logging.warning(f"No price found for {url} with selectors {site_selectors}. HTML snippet: {resp.text[:500]}")
        if 'captcha' in resp.text.lower() or 'robot' in resp.text.lower():
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
            soup = BeautifulSoup(content, 'html.parser')
            for selector in site_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    logging.info(f"Selector '{selector}' matched for {url} (Playwright)")
                    browser.close()
                    return clean_price(price_elem.get_text())
                else:
                    logging.debug(f"Selector '{selector}' did not match for {url} (Playwright)")
            browser.close()
            logging.warning(f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}")
            if 'captcha' in content.lower() or 'robot' in content.lower():
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None
