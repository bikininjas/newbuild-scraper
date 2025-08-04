def process_product_row(row, args, product_prices, updated_rows, now_iso, today):
    import time
    url = row["URL"]
    name = row["Product_Name"]

    def append_row(price, label):
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
        debug_log_domain(url, f"{label} Added row to updated_rows: {row_dict}", args.debug_domains)

    def get_idealo_price():
        selectors = get_site_selector(url)
        price = get_price_requests(url, selectors)
        if price is None:
            price = get_price_playwright(url, selectors)
        if price is None:
            logging.warning(f"[IDEALO] Selector .productOffers-listItemOfferPrice may be invalid for {url}")
        time.sleep(3)
        return price

    def get_fallback_price():
        fallback_sites = ["topachat.com", "amazon.fr", "ldlc.com", "materiel.net"]
        for site in fallback_sites:
            if site in url:
                selectors = get_site_selector(url)
                price = get_price_requests(url, selectors)
                if price is None:
                    price = get_price_playwright(url, selectors)
                time.sleep(2)
                if price is not None:
                    return price, site
        return None, None

    if "idealo.fr" in url:
        price = get_idealo_price()
        if price is not None:
            append_row(price, "[IDEALO]")
        else:
            price, site = get_fallback_price()
            if price is not None:
                append_row(price, f"[FALLBACK:{site}]")


def save_new_rows(df_new, history, debug_domains=None):
    """Save new rows to history and log debug info for specific domains."""
    domains = debug_domains or DEFAULT_DEBUG_DOMAINS
    df_new = df_new.dropna(how="all")
    logging.info(f"[CSV] DataFrame to add: {df_new}")
    if not df_new.empty:
        history = pd.concat([history, df_new], ignore_index=True)
        logging.info(f"[CSV] Saving {len(df_new)} new rows to {HISTORY_FILE}")
        history.to_csv(HISTORY_FILE, index=False)
        for domain in domains:
            domain_rows = df_new[df_new["URL"].str.contains(domain)]
            logging.info(f"[{domain.upper()}] Rows saved to CSV: {domain_rows}")
    return history


import os
import pandas as pd
from datetime import datetime
from utils import setup_logging
try:
    # Try to use the new modular scraper first
    from scraper_new import get_price_requests, get_price_playwright
    from sites.config import get_site_selector
    print("Using new modular scraper")
except ImportError:
    # Fall back to the old scraper
    from scraper import get_site_selector, get_price_requests, get_price_playwright
    print("Using legacy scraper")
from alerts import send_discord_alert
from generate_html import generate_html
import argparse
import logging

# Default domains for which debug logging is enabled
DEFAULT_DEBUG_DOMAINS = ["topachat.com"]


def debug_log_domain(url, message, debug_domains=None):
    """Log debug messages for specific domains."""
    domains = debug_domains or DEFAULT_DEBUG_DOMAINS
    for domain in domains:
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
    parser.add_argument(
        "--debug-domains", 
        type=str, 
        nargs="*", 
        default=DEFAULT_DEBUG_DOMAINS,
        help="Domains for which to enable debug logging (default: topachat.com)"
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
        history = save_new_rows(df_new, history, args.debug_domains)


if __name__ == "__main__":
    main()
