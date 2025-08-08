#!/usr/bin/env python3
"""
Migration script to convert existing CSV data to SQLite.
This script can be run manually or will be executed automatically.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseManager, DatabaseConfig


def main():
    """Main migration function."""
    print("🔄 Starting database migration from CSV to SQLite...")

    # Check if CSV files exist
    if not Path("produits.csv").exists():
        print("❌ produits.csv not found. Nothing to migrate.")
        return

    if not Path("historique_prix.csv").exists():
        print("⚠️  historique_prix.csv not found. Will migrate products only.")

    # Load configuration
    config_path = "database.conf"
    if Path(config_path).exists():
        print(f"📁 Loading configuration from {config_path}")
        config = DatabaseConfig.from_config_file(config_path)
    else:
        print("📁 Using default configuration")
        config = DatabaseConfig()

    # Force SQLite for migration
    config.database_type = "sqlite"
    config.enable_auto_migration = True

    try:
        # Initialize database manager (will trigger migration)
        db_manager = DatabaseManager(config)

        # Verify migration
        products = db_manager.get_products()
        history = db_manager.get_price_history()

        print(f"✅ Migration completed successfully!")
        print(f"   - {len(products)} products migrated")
        print(f"   - {len(history)} price records migrated")
        print(f"   - Database saved to: {config.sqlite_path}")

        # Export to CSV for backward compatibility
        db_manager.export_to_csv()
        print("✅ CSV files updated for GitHub Actions compatibility")

        print("\n🎉 Migration completed! You can now use SQLite backend.")
        print("\nNext steps:")
        print("1. Test the migration: python test_database.py")
        print("2. Run scraper with SQLite: python src/main.py --db-type sqlite")
        print("3. Use selective scraping: python src/main.py --new-products-only")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    main()
