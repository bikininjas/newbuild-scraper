def process_product_row(row, args, product_prices, updated_rows, now_iso, today):
    url = row["URL"]
    name = row["Product_Name"]
    if args.site and args.site not in url:
        return
    selectors = get_site_selector(url)
    price = get_price_requests(url, selectors)
    if price is None:
        price = get_price_playwright(url, selectors)
    if price is None:
        return
    if name not in product_prices:
        product_prices[name] = []
    product_prices[name].append({"url": url, "price": price})
    row_dict = {
        "Timestamp_ISO": now_iso,
        "Date": today,
        "Product_Name": name,
        "URL": url,
        "Price": price,
    }
    updated_rows.append(row_dict)
    debug_log_domain(url, f"Added row to updated_rows: {row_dict}")


def save_new_rows(df_new, history):
    df_new = df_new.dropna(how="all")
    logging.info(f"[CSV] DataFrame to add: {df_new}")
    if not df_new.empty:
        history = pd.concat([history, df_new], ignore_index=True)
        logging.info(f"[CSV] Saving {len(df_new)} new rows to {HISTORY_FILE}")
        history.to_csv(HISTORY_FILE, index=False)
        for domain in DEBUG_DOMAINS:
            domain_rows = df_new[df_new["URL"].str.contains(domain)]
            logging.info(f"[{domain.upper()}] Rows saved to CSV: {domain_rows}")
    return history


import os
import pandas as pd
from datetime import datetime
from utils import setup_logging
from scraper import get_site_selector, get_price_requests, get_price_playwright
from alerts import send_discord_alert
from generate_html import generate_html
import argparse
import logging

# Domains for which debug logging is enabled
DEBUG_DOMAINS = ["topachat.com"]


def debug_log_domain(url, message):
    for domain in DEBUG_DOMAINS:
        if domain in url:
            logging.info(f"[{domain.upper()}] {message}")
            break


PRODUCTS_FILE = "produits.csv"
HISTORY_FILE = "historique_prix.csv"
LOG_FILE = "scraper.log"

setup_logging(LOG_FILE)


def main():
    parser = argparse.ArgumentParser(description="Product price scraper")
    parser.add_argument(
        "--site", type=str, help="Only test URLs containing this domain", default=None
    )
    parser.add_argument(
        "--no-html", action="store_true", help="Do not generate output.html"
    )
    args = parser.parse_args()

    products = pd.read_csv(PRODUCTS_FILE)
    try:
        history = pd.read_csv(HISTORY_FILE)
    except Exception:
        history = pd.DataFrame(
            columns=["Timestamp_ISO", "Date", "Product_Name", "URL", "Price"]
        )
    now_iso = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    updated_rows = []
    product_prices = {}

    for _, row in products.iterrows():
        process_product_row(row, args, product_prices, updated_rows, now_iso, today)

    if not args.no_html:
        generate_html(product_prices, history)

    if updated_rows:
        df_new = pd.DataFrame(updated_rows)
        history = save_new_rows(df_new, history)


if __name__ == "__main__":
    main()
