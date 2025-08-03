import os
import time
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime
import logging
from playwright.sync_api import sync_playwright

PRODUCTS_FILE = 'produits.csv'
HISTORY_FILE = 'historique_prix.csv'
LOG_FILE = 'scraper.log'
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]
)

# --- UTILS ---
def get_user_agent():
    try:
        return UserAgent().random
    except Exception:
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'

def clean_price(raw):
    if raw is None:
        return None
    price = raw.replace('€', '').replace(',', '.').replace(' ', '').strip()
    try:
        return float(price)
    except Exception:
        return None

def send_discord_alert(product_name, url, old_price, new_price):
    percent_drop = ((old_price - new_price) / old_price) * 100 if old_price else 0
    print("\n==============================")
    print(f"🔔 Price drop detected!")
    print(f"Product: {product_name}")
    print(f"Old price: {old_price}€")
    print(f"New price: {new_price}€")
    print(f"Drop: {percent_drop:.2f}%")
    print(f"Product page: {url}")
    print("==============================\n")

# --- SCRAPER LOGIC ---

def get_price_requests(url, site_selector):
    headers = {'User-Agent': get_user_agent()}
    time.sleep(random.uniform(2, 5))
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Fetched {url} with requests, status {resp.status_code}")
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        price_elem = soup.select_one(site_selector)
        if price_elem:
            return clean_price(price_elem.get_text())
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None

def get_price_playwright(url, site_selector):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            price_elem = soup.select_one(site_selector)
            browser.close()
            if price_elem:
                logging.info(f"Fetched {url} with Playwright")
                return clean_price(price_elem.get_text())
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None

def get_site_selector(url):
    # TODO: Add logic for each site, e.g.:
    # if 'example.com' in url:
    #     return '.price-class'
    # For demo, use a generic selector
    return '.price, .product-price, #price, .a-price-whole'

def main():
    html = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>Product Price Tracker</title>',
        '  <style>',
        '    body { font-family: Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }',
        '    .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }',
        '    h1 { text-align: center; margin-bottom: 32px; }',
        '    .product { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 32px; }',
        '    .best { color: #2196f3; font-weight: bold; }',
        '    .prices, .history { margin: 12px 0 0 0; }',
        '    .prices li, .history li { margin-bottom: 4px; }',
        '    .site { font-size: 0.95em; color: #555; }',
        '    .price { font-weight: bold; }',
        '    .best-site { background: #e3f2fd; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-bottom: 8px; }',
        '    .history-title { margin-top: 18px; font-size: 1.05em; color: #666; }',
        '  </style>',
        '</head>',
        '<body>',
        '<div class="container">',
        '<h1>Product Price Tracker</h1>'
    ]
    products = pd.read_csv(PRODUCTS_FILE)
    try:
        history = pd.read_csv(HISTORY_FILE)
    except Exception:
        history = pd.DataFrame(columns=['Timestamp_ISO', 'Date', 'Product_Name', 'URL', 'Price'])
    now_iso = datetime.now().isoformat()
    today = datetime.now().strftime('%Y-%m-%d')
    updated_rows = []
    product_prices = {}

    for _, row in products.iterrows():
        url = row['URL']
        name = row['Product_Name']
        selector = get_site_selector(url)
        price = get_price_requests(url, selector)
        if price is None:
            price = get_price_playwright(url, selector)
        if price is None:
            logging.warning(f"Could not find price for {name} ({url})")
            continue
        logging.info(f"Fetched price for {name}: {price}€ from {url}")
        # Track all prices for each product
        if name not in product_prices:
            product_prices[name] = []
        product_prices[name].append({'url': url, 'price': price})
        # Update history with ISO timestamp
        updated_rows.append({'Timestamp_ISO': now_iso, 'Date': today, 'Product_Name': name, 'URL': url, 'Price': price})

    # Prepare HTML output
    html = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>Product Price Tracker</title>',
        '  <style>',
        '    body { font-family: Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }',
        '    .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }',
        '    h1 { text-align: center; margin-bottom: 32px; }',
        '    .product { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 32px; }',
        '    .best { color: #2196f3; font-weight: bold; }',
        '    .prices, .history { margin: 12px 0 0 0; }',
        '    .prices li, .history li { margin-bottom: 4px; }',
        '    .site { font-size: 0.95em; color: #555; }',
        '    .price { font-weight: bold; }',
        '    .best-site { background: #e3f2fd; padding: 6px 12px; border-radius: 4px; display: inline-block; margin-bottom: 8px; }',
        '    .history-title { margin-top: 18px; font-size: 1.05em; color: #666; }',
        '  </style>',
        '</head>',
        '<body>',
        '<div class="container">',
        '<h1>Product Price Tracker</h1>'
    ]
    # Display best price and price history per product
    for name, entries in product_prices.items():
        best = min(entries, key=lambda x: x['price'])
        html.append(f'<div class="product">')
        html.append(f'<h2>{name}</h2>')
        html.append(f'<div class="best-site">Best price: <span class="price">{best["price"]}€</span> <span class="site">@ <a href="{best["url"]}" target="_blank">{best["url"]}</a></span></div>')
        html.append('<ul class="prices">')
        for entry in entries:
            html.append(f'<li><span class="price">{entry["price"]}€</span> <span class="site">@ <a href="{entry["url"]}" target="_blank">{entry["url"]}</a></span></li>')
        html.append('</ul>')
        history_entries = history[history['Product_Name'] == name]
        if not history_entries.empty:
            html.append('<div class="history-title">Price history:</div>')
            html.append('<ul class="history">')
            for _, h in history_entries.iterrows():
                timestamp = h["Timestamp_ISO"] if "Timestamp_ISO" in h else h.get("Date", "?")
                html.append(f'<li>{timestamp}: <span class="price">{h["Price"]}€</span> <span class="site">@ <a href="{h["URL"]}" target="_blank">{h["URL"]}</a></span></li>')
            html.append('</ul>')
        else:
            html.append('<div class="history-title">No price history yet.</div>')
        html.append('</div>')
    html.append('</div></body></html>')
    with open('output.html', 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))
    # Append new prices
    if updated_rows:
        df_new = pd.DataFrame(updated_rows)
        # Remove all-NA rows
        df_new = df_new.dropna(how='all')
        if not df_new.empty:
            history = pd.concat([history, df_new], ignore_index=True)
            history.to_csv(HISTORY_FILE, index=False)
            logging.info('Price history updated.')
        else:
            logging.info('No valid new prices to update.')
    else:
        logging.info('No new prices to update.')

if __name__ == '__main__':
    main()
