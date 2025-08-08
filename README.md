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

### How the graphs work

- **Total Price History graph:** Shows the sum of the best price for each product at each timestamp. The last point always matches the sum of the absolute best prices in the table. Missing prices are interpolated by repeating the last known value for visual continuity.
- **Product Price History graph:** Shows the best price (lowest) for each product at each timestamp. If a product's price is missing at a timestamp, the last known price is repeated for a smoother, visually appealing line.
- **Price Evolution Indicator:** Each product graph and card now displays an indicator (green ↓ for price drop, red ↑ for price increase, gray – for no change) comparing the last price to the previous one. Indicators use accessible colors and ARIA labels for screen readers.

### Pricing logic

- "Upgrade Kit" category is treated as an alternative bundle. It's displayed in the summary table for comparison but is not included in the total row or in the total price history chart.

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

### 2. Fill your product list

- Edit `produits.csv` like this:

  ```csv
  URL,Product_Name
  https://www.amazon.fr/dp/B07W7L4RBX/,"Logitech G G502 X LIGHTSPEED"
  https://www.amazon.fr/dp/B0DKFMSMYK/,"RYZEN ™ 7 9800X3D 8 Coeurs/16 Threads"
  https://www.pccomponentes.fr/amd-ryzen-7-7800x3d-processeur-42-ghz-96-mo-l3-boite,"RYZEN ™ 7 9800X3D 8 Coeurs/16 Threads"
  ...
  ```

- Add as many URLs as you want for each product (just repeat the product name)

### 3. Run locally

- Set the Discord webhook (if you want alerts):

  ```bash
  export DISCORD_WEBHOOK_URL='your_webhook_url'
  ```

- Run the script:

  ```bash
  python src/main.py
  ```

- See the best price, all prices, and price history for each product in your console

- To generate a modern HTML report with all products styled as Tailwind cards:

  ```bash
  python src/generate_html.py
  ```

### 4. Run automatically with GitHub Actions

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
