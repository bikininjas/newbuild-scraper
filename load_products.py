#!/usr/bin/env python3
"""
Product CSV to SQLite loader with automatic cleanup.
Loads products from produits.csv into SQLite database and manages CSV file lifecycle.
"""

import pandas as pd
import logging
import os
import sys
from datetime import datetime
from typing import List, Tuple

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from database.manager import DatabaseManager
from database.config import DatabaseConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProductLoader:
    """Manages loading products from CSV to SQLite and CSV cleanup."""

    def __init__(self, csv_path: str = "produits.csv"):
        self.csv_path = csv_path
        self.db_config = DatabaseConfig()
        self.db_manager = DatabaseManager(self.db_config)

    def load_products_to_db(self) -> Tuple[int, List[str]]:
        """
        Load products from CSV to SQLite database.

        Returns:
            Tuple of (loaded_count, failed_urls)
        """
        if not os.path.exists(self.csv_path):
            logger.warning(f"CSV file not found: {self.csv_path}")
            return 0, []

        try:
            # Read CSV file
            df = pd.read_csv(self.csv_path, encoding="utf-8")
            logger.info(f"Found {len(df)} products in {self.csv_path}")

            if len(df) == 0:
                logger.info("No products to load")
                return 0, []

            loaded_count = 0
            failed_urls = []

            for _, row in df.iterrows():
                product_name = row.get("Product_Name", "").strip()
                url = row.get("URL", "").strip()
                category = row.get("Category", "Other").strip()

                if not product_name or not url:
                    logger.warning(f"Skipping row with missing data: {row.to_dict()}")
                    continue

                # Check if URL is accessible (basic validation)
                if self._is_valid_url(url):
                    # Add product to database
                    success = self.db_manager.add_product(product_name, category)
                    if success:
                        # Add URL entry
                        success = self.db_manager.add_url_entry(product_name, url)
                        if success:
                            loaded_count += 1
                            logger.info(f"✓ Loaded: {product_name} - {url}")
                        else:
                            failed_urls.append(url)
                            logger.warning(f"✗ Failed to add URL: {url}")
                    else:
                        failed_urls.append(url)
                        logger.warning(f"✗ Failed to add product: {product_name}")
                else:
                    failed_urls.append(url)
                    logger.warning(f"✗ Invalid/inaccessible URL: {url}")

            logger.info(f"Successfully loaded {loaded_count} products")
            if failed_urls:
                logger.warning(f"Failed to load {len(failed_urls)} URLs")

            return loaded_count, failed_urls

        except Exception as e:
            logger.error(f"Error loading products from CSV: {e}")
            return 0, []

    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        if not url.startswith(("http://", "https://")):
            return False

        # Add basic domain validation if needed
        blocked_domains = ["example.com", "test.com"]
        for domain in blocked_domains:
            if domain in url:
                return False

        return True

    def create_empty_csv_template(self):
        """Create an empty CSV template with example rows."""
        template_data = {
            "Product_Name": [
                "# Example products (these will NOT be loaded)",
                "Samsung 990 EVO 1TB",
                "Corsair MP700 Elite 1TB",
            ],
            "URL": [
                "# Add your product URLs here",
                "https://example.com/samsung-990-evo-1tb",
                "https://example.com/corsair-mp700-elite-1tb",
            ],
            "Category": ["# Categories: SSD, RAM, CPU, GPU, etc.", "SSD", "SSD"],
        }

        df = pd.DataFrame(template_data)
        df.to_csv(self.csv_path, index=False, encoding="utf-8")
        logger.info(f"Created empty CSV template: {self.csv_path}")

    def clear_csv_after_load(self):
        """Clear the CSV file after successful loading, keeping only template."""
        try:
            self.create_empty_csv_template()
            logger.info(f"Cleared {self.csv_path} and reset to template")
        except Exception as e:
            logger.error(f"Error clearing CSV: {e}")

    def handle_failed_urls(self, failed_urls: List[str]):
        """Store failed URLs in a separate table for analysis."""
        if not failed_urls:
            return

        try:
            # Create failed URLs table if it doesn't exist
            with self.db_manager._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS failed_urls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        failure_reason TEXT,
                        failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        retry_count INTEGER DEFAULT 0
                    )
                """
                )

                # Insert failed URLs
                for url in failed_urls:
                    conn.execute(
                        "INSERT OR IGNORE INTO failed_urls (url, failure_reason) VALUES (?, ?)",
                        (url, "Failed during CSV load"),
                    )

                logger.info(f"Stored {len(failed_urls)} failed URLs for later analysis")

        except Exception as e:
            logger.error(f"Error storing failed URLs: {e}")


def main():
    """Main function to load products and clean up CSV."""
    loader = ProductLoader()

    logger.info("Starting product CSV to SQLite loading process...")

    # Load products from CSV to SQLite
    loaded_count, failed_urls = loader.load_products_to_db()

    if loaded_count > 0:
        logger.info(f"Successfully loaded {loaded_count} products to database")

        # Handle failed URLs
        if failed_urls:
            loader.handle_failed_urls(failed_urls)

        # Clear CSV file after successful load
        loader.clear_csv_after_load()
    else:
        logger.info("No products were loaded - keeping CSV file unchanged")


if __name__ == "__main__":
    main()
