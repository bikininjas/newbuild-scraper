import os
import pandas as pd
from datetime import datetime
from utils import setup_logging
from scraper import get_site_selector, get_price_requests, get_price_playwright
from alerts import send_discord_alert
from generate_html import generate_html
import argparse

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

    import logging

    for _, row in products.iterrows():
        url = row["URL"]
        name = row["Product_Name"]
        if args.site and args.site not in url:
            continue
        selectors = get_site_selector(url)
        price = get_price_requests(url, selectors)
        if price is None:
            price = get_price_playwright(url, selectors)
        if price is None:
            continue
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
        if "topachat.com" in url:
            logging.info(f"[TOPACHAT] Added row to updated_rows: {row_dict}")

    if not args.no_html:
        generate_html(product_prices, history)

    if updated_rows:
        df_new = pd.DataFrame(updated_rows)
        df_new = df_new.dropna(how="all")
        logging.info(f"[CSV] DataFrame to add: {df_new}")
        if not df_new.empty:
            history = pd.concat([history, df_new], ignore_index=True)
            logging.info(f"[CSV] Saving {len(df_new)} new rows to {HISTORY_FILE}")
            history.to_csv(HISTORY_FILE, index=False)
            # Check if topachat.com rows are present in df_new
            topachat_rows = df_new[df_new["URL"].str.contains("topachat.com")]
            logging.info(f"[TOPACHAT] Rows saved to CSV: {topachat_rows}")


if __name__ == "__main__":
    main()
