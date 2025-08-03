# 🛒 Price Scraper Project

## What is this?

Track the prices of computer parts (or any products) across multiple e-commerce sites. Always see the best price and where to buy. Price history is logged for every product and every site. Fully automated with GitHub Actions, or run locally.

## Features

- Track multiple URLs for the same product (find the best price across sites)
- See all current prices and the best site to buy
- View full price history for every product and site
- Easy CSV-based product list
- Secure: no secrets in code, only in GitHub Actions
- Works locally or in CI (GitHub Actions)

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

- Open `output.html` in your browser to preview the results. All products will be displayed as modern, responsive cards using Tailwind CSS and the Inter font.

### 4. Output Format


- The generated `output.html` uses Tailwind CSS for a clean, modern look.


#### Category Summary Table
At the top of the page, a summary table displays the cheapest product for each category:
  - Category (e.g., CPU, GPU, RAM, SSD, Motherboard, Cooler, PSU, Mouse, Keyboard, Upgrade Kit)
  - Product name (cheapest in category)
  - Best price
  - Best site (as a label with link)
  - Last seen (timestamp)
  - **Total row**: Sums all category minimums for a quick budget overview

#### Product Cards
All products are rendered as cards inside a responsive grid below the table.
Each card shows the product name, best price, all current prices, and full price history.
No legacy markup remains; all products use the same card layout.

### 5. Run automatically with GitHub Actions

- Add your webhook to GitHub Actions secrets as `DISCORD_WEBHOOK_URL`
- Push your code to GitHub
- The workflow in `.github/workflows/main.yml` will run every 4 hours and update `historique_prix.csv` automatically

## Output Example

```
=== RYZEN ™ 7 9800X3D 8 Coeurs/16 Threads ===
Best price: 482.0€
Best site: https://www.amazon.fr/dp/B0DKFMSMYK/
All current prices:
- 482.0€ @ https://www.amazon.fr/dp/B0DKFMSMYK/
- 499.0€ @ https://www.pccomponentes.fr/amd-ryzen-7-7800x3d-processeur-42-ghz-96-mo-l3-boite
Price history:
- 2025-08-03: 482.0€ @ https://www.amazon.fr/dp/B0DKFMSMYK/
- 2025-08-03: 499.0€ @ https://www.pccomponentes.fr/amd-ryzen-7-7800x3d-processeur-42-ghz-96-mo-l3-boite
==============================
```

## Security & Best Practices

## Manual To-Do List

## 2025-08-03: Data Migration

All legacy rows in `historique_prix.csv` missing the `Timestamp_ISO` field have been migrated to include an ISO 8601 timestamp (midnight by default). This ensures compatibility with analytics and database tools.

## Advanced

- Customize CSS selectors for each site in `src/scraper.py` for more accurate price extraction
- Add more notification channels if needed

## Google Cloud Storage Automation

### Automated Push of output.html

A GitHub Actions workflow automatically uploads `output.html` to a Google Cloud Storage bucket when changes are pushed to the `gcs-output-html` branch. The upload only occurs if the file is non-empty and contains all required information (`<title>`, `<body>`, and at least one `<table>` tag).

#### Required GitHub Secrets
- `GCS_BUCKET_SVC_ACCOUNT_JSON_KEY`: Service account key JSON for authentication
- `GCP_PROJECT_ID`: Google Cloud project ID
- `GCS_BUCKET_NAME_NEWPC`: Name of the target GCS bucket

#### How it works
1. On push to `gcs-output-html`, the workflow checks `output.html` for content and required tags.
2. If valid, it uploads the file to the specified GCS bucket using `gsutil`.
3. If not valid, the upload is skipped.

See `.github/workflows/push-output-html-gcs.yml` for details.

## License

MIT