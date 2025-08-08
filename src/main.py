import os
import pandas as pd
from datetime import datetime
import time
import logging
import argparse
from pathlib import Path
from utils import setup_logging  # From utils package
from scraper import get_price_requests, get_price_playwright
from sites.config import get_site_selector
from alerts import send_discord_alert
from generate_html import generate_html
from database import DatabaseManager, DatabaseConfig

# Import the product loader
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from load_products import ProductLoader

# Default domains for which debug logging is enabled
DEFAULT_DEBUG_DOMAINS = ["topachat.com"]

# Legacy file paths for backward compatibility
PRODUCTS_FILE = "produits.csv"
HISTORY_FILE = "historique_prix.csv"
LOG_FILE = "scraper.log"

setup_logging(LOG_FILE)


def debug_log_domain(url, message, debug_domains=None):
    domains = debug_domains or DEFAULT_DEBUG_DOMAINS
    for domain in domains:
        if domain in url:
            logging.info(f"[{domain.upper()}] {message}")
            break


def append_row(
    product_prices, updated_rows, name, url, price_info, now_iso, today, label, args
):
    # Extract price from price_info (could be string or dict)
    if isinstance(price_info, dict):
        price = price_info.get("price", "")
    else:
        price = price_info or ""

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

    # Add vendor information if available
    if isinstance(price_info, dict):
        if price_info.get("vendor_name"):
            row_dict["Vendor_Name"] = price_info["vendor_name"]
        if price_info.get("vendor_url"):
            row_dict["Vendor_URL"] = price_info["vendor_url"]
        if price_info.get("is_marketplace"):
            row_dict["Is_Marketplace"] = price_info["is_marketplace"]
        if price_info.get("is_prime_eligible"):
            row_dict["Is_Prime_Eligible"] = price_info["is_prime_eligible"]

    updated_rows.append(row_dict)
    debug_log_domain(
        url, f"{label} Added row to updated_rows: {row_dict}", args.debug_domains
    )


def get_idealo_price(url, db_manager=None):
    selectors = get_site_selector(url)
    price_info = get_price_requests(url, selectors, db_manager)
    if price_info is None:
        price_info = get_price_playwright(url, selectors, db_manager)
    if price_info is None:
        logging.warning(
            f"[IDEALO] Selector .productOffers-listItemOfferPrice may be invalid for {url}"
        )
    time.sleep(3)
    return price_info


def get_fallback_price(url, db_manager=None):
    fallback_sites = ["topachat.com", "amazon.fr", "ldlc.com", "materiel.net"]
    selectors = get_site_selector(url)
    for site in fallback_sites:
        if site in url:
            price_info = get_price_requests(url, selectors, db_manager)
            if price_info is None:
                price_info = get_price_playwright(url, selectors, db_manager)
            if price_info is not None:
                return price_info, site
    return None, None


def process_product_row_db(
    row, args, product_prices, updated_rows, now_iso, today, db_manager
):
    """Process a product row with database manager integration."""
    url = row["URL"]
    name = row["Product_Name"]
    price_info = None

    if "idealo.fr" in url:
        price_info = get_idealo_price(url, db_manager)
        if price_info is not None:
            append_row(
                product_prices,
                updated_rows,
                name,
                url,
                price_info,
                now_iso,
                today,
                "[IDEALO]",
                args,
            )
        else:
            price_info, site = get_fallback_price(url, db_manager)
            if price_info is not None:
                append_row(
                    product_prices,
                    updated_rows,
                    name,
                    url,
                    price_info,
                    now_iso,
                    today,
                    f"[FALLBACK:{site}]",
                    args,
                )
    else:
        price_info, site = get_fallback_price(url, db_manager)
        if price_info is not None:
            append_row(
                product_prices,
                updated_rows,
                name,
                url,
                price_info,
                now_iso,
                today,
                f"[FALLBACK:{site}]",
                args,
            )


def process_product_row(row, args, product_prices, updated_rows, now_iso, today):
    url = row["URL"]
    name = row["Product_Name"]
    if "idealo.fr" in url:
        price_info = get_idealo_price(url)
        if price_info is not None:
            append_row(
                product_prices,
                updated_rows,
                name,
                url,
                price_info,
                now_iso,
                today,
                "[IDEALO]",
                args,
            )
        else:
            price_info, site = get_fallback_price(url)
            if price_info is not None:
                append_row(
                    product_prices,
                    updated_rows,
                    name,
                    url,
                    price_info,
                    now_iso,
                    today,
                    f"[FALLBACK:{site}]",
                    args,
                )
    else:
        price_info, site = get_fallback_price(url)
        if price_info is not None:
            append_row(
                product_prices,
                updated_rows,
                name,
                url,
                price_info,
                now_iso,
                today,
                f"[FALLBACK:{site}]",
                args,
            )


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


import argparse
from alerts import send_discord_alert
from generate_html import generate_html


def load_products_from_csv(db_manager, db_config):
    """Load products from CSV file to database if new products are present."""
    try:
        # Check if CSV file exists and has new products
        if os.path.exists(PRODUCTS_FILE):
            loader = ProductLoader(csv_path=PRODUCTS_FILE)
            loaded_count, failed_urls = loader.load_products_to_db()

            if loaded_count > 0:
                logging.info(f"Loaded {loaded_count} new products from {PRODUCTS_FILE}")

                if failed_urls:
                    logging.warning(f"Failed to process {len(failed_urls)} URLs")
                    for url in failed_urls:
                        logging.warning(f"Failed URL: {url}")

                # Clear CSV after successful loading (optional - can be disabled)
                # loader.clear_csv_after_load()
                # logging.info(f"Cleared {PRODUCTS_FILE} after successful loading")
            else:
                logging.info("No new products found in CSV file")

    except Exception as e:
        logging.error(f"Error loading products from CSV: {e}")


def setup_database_manager(args):
    """Setup and return database manager based on configuration."""
    # Initialize database manager
    if Path(args.config).exists():
        db_config = DatabaseConfig.from_config_file(args.config)
    else:
        db_config = DatabaseConfig.from_env()

    # Force SQLite as the only supported database type
    db_config.database_type = "sqlite"

    db_manager = DatabaseManager(db_config)
    logging.info(f"Using {db_config.database_type} database backend")
    return db_manager, db_config


def get_products_to_scrape(args, db_manager, db_config):
    """Get products that need to be scraped."""
    if args.new_products_only:
        products_to_scrape = db_manager.get_products_needing_scrape(args.max_age_hours)
        logging.info(
            f"Found {len(products_to_scrape)} products needing scrape (max age: {args.max_age_hours}h)"
        )

        # Convert to DataFrame format for compatibility
        if products_to_scrape:
            products_data = []
            for name, url in products_to_scrape:
                products_data.append({"Product_Name": name, "URL": url})
            return pd.DataFrame(products_data)
        else:
            logging.info("No products need scraping, exiting")
            return None
    else:
        # Get all products
        if db_config.database_type == "csv":
            return pd.read_csv(PRODUCTS_FILE)
        else:
            # Build products DataFrame from database
            all_products = db_manager.get_products()
            products_data = []
            for product in all_products:
                urls = db_manager.get_product_urls(product.name)
                for url_entry in urls:
                    products_data.append(
                        {"Product_Name": product.name, "URL": url_entry.url}
                    )
            return pd.DataFrame(products_data)


def scrape_products(products, args, db_manager, db_config):
    """Scrape prices for the given products."""
    now_iso = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    updated_rows = []
    product_prices = {}

    for _, row in products.iterrows():
        # Check cache for SQLite backend
        if db_config.database_type == "sqlite" and db_manager.is_url_cached(row["URL"]):
            logging.info(f"Skipping cached URL: {row['URL']}")
            continue

        process_product_row_db(
            row, args, product_prices, updated_rows, now_iso, today, db_manager
        )

    return product_prices, updated_rows


def save_scraping_results(updated_rows, db_manager, db_config):
    """Save scraping results to database."""
    if updated_rows:
        logging.info(f"Saving {len(updated_rows)} new price entries")
        for row_data in updated_rows:
            success = db_manager.add_price_entry(
                row_data["Product_Name"],
                row_data["URL"],
                row_data["Price"],
                datetime.fromisoformat(row_data["Timestamp_ISO"]),
                vendor_name=row_data.get("Vendor_Name"),
                vendor_url=row_data.get("Vendor_URL"),
                is_marketplace=row_data.get("Is_Marketplace", False),
                is_prime_eligible=row_data.get("Is_Prime_Eligible", False),
            )

            # Update cache for SQLite
            if db_config.database_type == "sqlite":
                db_manager.update_cache(row_data["URL"], success=success)

        # Export to CSV for GitHub Actions compatibility
        if db_config.database_type == "sqlite":
            db_manager.export_to_csv()
            logging.info("Data exported to CSV files for GitHub Actions compatibility")


def main():
    parser = argparse.ArgumentParser(description="Product price scraper")
    parser.add_argument(
        "--no-html", action="store_true", help="Do not generate output.html"
    )
    parser.add_argument(
        "--debug-domains",
        type=str,
        nargs="*",
        default=DEFAULT_DEBUG_DOMAINS,
        help="Domains for which to enable debug logging (default: topachat.com)",
    )
    parser.add_argument(
        "--new-products-only",
        action="store_true",
        help="Only scrape products with no entries in the last 48 hours",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=48,
        help="Maximum age in hours for --new-products-only (default: 48)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="database.conf",
        help="Path to database configuration file",
    )
    args = parser.parse_args()

    # Setup database
    db_manager, db_config = setup_database_manager(args)

    # Load products from CSV if available (for SQLite database only)
    if db_config.database_type == "sqlite":
        load_products_from_csv(db_manager, db_config)

    # Get products to scrape
    products = get_products_to_scrape(args, db_manager, db_config)
    if products is None:
        return

    # Get price history for HTML generation
    history = db_manager.get_price_history()

    # Scrape products
    product_prices, updated_rows = scrape_products(
        products, args, db_manager, db_config
    )

    # Generate HTML report
    if not args.no_html:
        generate_html(product_prices, history)

    # Save results
    save_scraping_results(updated_rows, db_manager, db_config)

    logging.info("Scraping completed successfully")

    if updated_rows:
        df_new = pd.DataFrame(updated_rows)
        history = save_new_rows(df_new, history, args.debug_domains)


if __name__ == "__main__":
    main()
