import os
import pandas as pd
from datetime import datetime
from utils import setup_logging
from scraper import get_site_selector, get_price_requests, get_price_playwright
from alerts import send_discord_alert
from generate_html import generate_html

PRODUCTS_FILE = "produits.csv"
HISTORY_FILE = "historique_prix.csv"
LOG_FILE = "scraper.log"

setup_logging(LOG_FILE)


def main():
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
        url = row["URL"]
        name = row["Product_Name"]
        selectors = get_site_selector(url)
        price = get_price_requests(url, selectors)
        if price is None:
            price = get_price_playwright(url, selectors)
        if price is None:
            continue
        if name not in product_prices:
            product_prices[name] = []
        product_prices[name].append({"url": url, "price": price})
        updated_rows.append(
            {
                "Timestamp_ISO": now_iso,
                "Date": today,
                "Product_Name": name,
                "URL": url,
                "Price": price,
            }
        )

    generate_html(product_prices, history)

    if updated_rows:
        df_new = pd.DataFrame(updated_rows)
        df_new = df_new.dropna(how="all")
        if not df_new.empty:
            history = pd.concat([history, df_new], ignore_index=True)
            history.to_csv(HISTORY_FILE, index=False)


if __name__ == "__main__":
    main()
