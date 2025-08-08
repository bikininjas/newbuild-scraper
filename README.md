# 🛒 Price Scraper Project (2025)

## Overview

This project tracks prices for computer parts (or any products) across multiple e-commerce sites. It automatically finds the best price for each product, logs price history, and generates a modern HTML dashboard with graphs and tables. All logic is modular and easy to extend.

## Code Structure

All HTML generation logic is now modularized:

- `src/htmlgen/data.py`: Loads products and price history from CSV files
- `src/htmlgen/normalize.py`: Price normalization, category mapping, and site label helpers
- `src/htmlgen/render.py`: Renders summary tables and product cards
- `src/htmlgen/graph.py`: Renders Chart.js price history graphs for all products
- `src/generate_html.py`: Main entry point, orchestrates data loading and rendering using the above modules

To add new features or fix bugs, edit the relevant module. All scripts are auto-formatted with `black`.

### How to extend

- Add new product categories in `normalize.py`
- Change table/card layout in `render.py`
- Update graph logic in `graph.py`

### Refactored Output

The generated HTML now includes:
- Category summary table (cheapest product per category)
- Total price history graph (Chart.js)
- Product cards grid (all prices, best price, **toggleable** history)
- Individual price history graphs for each product (Chart.js)
- **Interactive UI**: Historical price sections are hidden by default with individual toggle buttons for each product
- ⚠️ Upgrade Kits shown as alternatives and excluded from total calculations

### UI Features

- **Toggleable Historical Prices**: Each product card has a "Show/Hide History" button to toggle the display of historical price data
- **Hidden by Default**: Historical price sections start hidden to reduce visual clutter
- **Individual Controls**: Each product has its own toggle - you can show history for specific products while keeping others hidden
- **Smooth Animations**: CSS transitions provide smooth show/hide animations
- **Responsive Design**: Toggle functionality works across all device sizes

### Single-file HTML (inlined JS)

- The generated `output.html` is fully self-contained: all JavaScript needed for UI interactions is inlined.
- Dropdown selection switches components without reloading the page, persists via `localStorage`, and updates the total instantly.
- The “Show/Hide history” toggle is implemented inline as well; no external `static/` scripts are required.
- The previous `static/toggleHistory.js` file has been removed to avoid 404s when serving a single file.

# 🛒 Price Scraper Project (2025)

## Overview

This project tracks prices for computer parts (or any products) across multiple e-commerce sites. It automatically finds the best price for each product, logs price history, and generates a modern HTML dashboard with graphs and tables. All logic is modular and easy to extend.

## 🆕 Enhanced Idealo Integration (August 2025)

### Vendor Extraction from Aggregators

Instead of generic "Idealo" entries, the scraper now extracts **actual vendor information** from aggregator sites:

- **Real Vendor Names**: Shows "Amazon.fr", "Corsair.com", "Fnac.com" instead of just "Idealo"
- **Redirect Following**: Automatically follows Idealo redirects to actual vendor sites
- **Direct Price Scraping**: Gets prices directly from vendor pages when possible
- **Marketplace Detection**: Identifies Amazon Marketplace vs. Amazon direct sales
- **Prime Eligibility**: Detects and stores Amazon Prime shipping eligibility
- **Cookie Consent Handling**: Automatically handles both Idealo and vendor cookie dialogs

### Database Enhancements

New fields in `price_history` table:

- `vendor_name`: Actual vendor (e.g., "Amazon.fr")
- `vendor_url`: Direct link to product on vendor site
- `is_marketplace`: Boolean for marketplace vs. direct sales
- `is_prime_eligible`: Boolean for Amazon Prime eligibility

### Example Output

Before: `Idealo - 109.99€`

After: `Amazon.fr - 109€ (Prime)` with full vendor URL and marketplace status

## Technical Architecture

### Modular HTML Generation

All HTML generation logic is now modularized:

- `src/htmlgen/data.py`: Loads products and price history from CSV files
- `src/htmlgen/normalize.py`: Price normalization, category mapping, and site label helpers
- `src/htmlgen/render.py`: Renders summary tables and product cards
- `src/htmlgen/graph.py`: Renders Chart.js price history graphs for all products
- `src/generate_html.py`: Main entry point, orchestrates data loading and rendering using the above modules

To add new features or fix bugs, edit the relevant module. All scripts are auto-formatted with `black`.

### Extension Points

- Add new product categories in `normalize.py`
- Change table/card layout in `render.py`
- Update graph logic in `graph.py`

### Generated HTML Features

The generated HTML now includes:

- Category summary table (cheapest product per category)
- Total price history graph (Chart.js)
- Product cards grid (all prices, best price, **toggleable** history)
- Individual price history graphs for each product (Chart.js)
- **Interactive UI**: Historical price sections are hidden by default with individual toggle buttons for each product
- ⚠️ Upgrade Kits shown as alternatives and excluded from total calculations

### Interactive UI Features

- **Toggleable Historical Prices**: Each product card has a "Show/Hide History" button to toggle the display of historical price data
- **Hidden by Default**: Historical price sections start hidden to reduce visual clutter
- **Individual Controls**: Each product has its own toggle - you can show history for specific products while keeping others hidden
- **Smooth Animations**: CSS transitions provide smooth show/hide animations
- **Responsive Design**: Toggle functionality works across all device sizes

### Self-Contained Output

- The generated `output.html` is fully self-contained: all JavaScript needed for UI interactions is inlined.
- Dropdown selection switches components without reloading the page, persists via `localStorage`, and updates the total instantly.
- The "Show/Hide history" toggle is implemented inline as well; no external `static/` scripts are required.
- The previous `static/toggleHistory.js` file has been removed to avoid 404s when serving a single file.

### How the graphs work

- **Total Price History graph:** Shows the sum of the best price for each product at each timestamp. The last point always matches the sum of the absolute best prices in the table. Missing prices are interpolated by repeating the last known value for visual continuity.
- **Product Price History graph:** Shows the best price (lowest) for each product at each timestamp. If a product's price is missing at a timestamp, the last known price is repeated for a smoother, visually appealing line.
- **Price Evolution Indicator:** Each product graph and card now displays an indicator (green ↓ for price drop, red ↑ for price increase, gray – for no change) comparing the last price to the previous one. Indicators use accessible colors and ARIA labels for screen readers.

### Pricing logic

- "Upgrade Kit" category is treated as an alternative bundle. It's displayed in the summary table for comparison but is not included in the total row or in the total price history chart.

## Configuration: excluded categories

To change which categories are excluded from the total, edit:

- `src/htmlgen/constants.py` — update `EXCLUDED_CATEGORIES` (a Python `set` of category names). All pricing totals and the summary table use this list.

Example:

```python
EXCLUDED_CATEGORIES: set[str] = {"Upgrade Kit", "Another Alt Category"}
```

### Known Issues / To Fix

- If a product's best price is not present at every timestamp, the graph may show flat or stepped lines. This is expected.
- If a product is missing from the price history at a timestamp, it is excluded from the sum for that timestamp.
- The UI and CSV parsing are robust, but edge cases (e.g., malformed CSV, missing columns) may need more error handling.
- ✅ **RESOLVED**: Cognitive complexity warnings have been addressed through code refactoring

## How to Use

### 1. Prepare your environment

- Install Python 3.10+ (or newer)
- Install Chrome/Chromium for Selenium (or use a compatible driver)
- Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

### 2. Choose your database backend

#### SQLite Support with Automatic Migration

The scraper now supports both CSV and SQLite backends:

- **SQLite** (Recommended): Better performance, caching, selective scraping
- **CSV** (Legacy): Original format, GitHub Actions compatible

#### Automatic Migration

If you have existing CSV data, it will be automatically migrated to SQLite:

```bash
# Run manual migration (optional)
python migrate_to_sqlite.py

# Or let it migrate automatically on first run
python src/main.py --db-type sqlite
```

#### Configuration

Edit `database.conf` to configure the database:

```bash
# Database type: "sqlite" or "csv"
database_type=sqlite

# Cache settings
cache_duration_hours=6
failed_cache_duration_hours=24

# Enable automatic CSV to SQLite migration
enable_auto_migration=true
```

### 3. Fill your product list

- Edit `produits.csv` like this (works with both backends):

  ```csv
  URL,Product_Name,Category
  https://www.amazon.fr/dp/B07W7L4RBX/,"Logitech G G502 X LIGHTSPEED","Mouse"
  https://www.amazon.fr/dp/B0DKFMSMYK/,"RYZEN ™ 7 9800X3D 8 Coeurs/16 Threads","CPU"
  https://www.pccomponentes.fr/amd-ryzen-7-7800x3d-processeur-42-ghz-96-mo-l3-boite,"RYZEN ™ 7 9800X3D 8 Coeurs/16 Threads","CPU"
  ...
  ```

- Add as many URLs as you want for each product (just repeat the product name)

### 4. Run locally

#### Basic Usage

```bash
# Run with SQLite (recommended)
python src/main.py --db-type sqlite

# Run with CSV (legacy)
python src/main.py --db-type csv

# Generate HTML report only
python src/generate_html.py
```

#### 🆕 Advanced Options

```bash
# Only scrape products with no data in last 48 hours
python src/main.py --new-products-only

# Custom age threshold for selective scraping
python src/main.py --new-products-only --max-age-hours 24

# Use custom configuration file
python src/main.py --config my_database.conf

# Skip HTML generation (faster for scheduled runs)
python src/main.py --no-html
```

#### 🆕 Caching Benefits (SQLite only)

- Successful prices cached for 6 hours (configurable)
- Failed attempts cached for 24 hours with exponential backoff
- Automatic retry scheduling for failed URLs
- Significant performance improvement for large product lists

### 5. Set up alerts (optional)

- Set the Discord webhook:

  ```bash
  export DISCORD_WEBHOOK_URL='your_webhook_url'
  ```


### TopAchat URL Fix & Workflow

**TopAchat URL Format:**
Product URLs in produits.csv must use the full TopAchat format, e.g.:
https://www.topachat.com/pages/detail2_cat_est_micro_puis_rubrique_est_w_ssd_puis_ref_est_in20023645.html

**Workflow:**
1. Clean database and cache: `rm -f data/scraper.db historique_prix.csv scraper.log`
2. Add valid product URLs to produits.csv
3. Run `python load_products.py` to load products
4. Run `python src/main.py` to scrape and log issues
5. Run `python generate_issues_summary.py` to review issues

### 6. Run automatically with GitHub Actions

- Add your webhook to GitHub Actions secrets as `DISCORD_WEBHOOK_URL`
- Push your code to GitHub
- The workflow in `.github/workflows/main.yml` will run every 4 hours and update `historique_prix.csv` automatically

```yaml
      - name: Format HTML generator scripts
        run: |
          black src/htmlgen/data.py src/htmlgen/normalize.py src/htmlgen/render.py src/htmlgen/graph.py src/generate_html.py
          git add -A
          git diff --cached --quiet || git commit -m "Update price history and format scripts"
```
