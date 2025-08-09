# Usage Guide: Newbuild Scraper

## Quick Start

### 1. Add / Update Products

Edit `products.json` (canonical format):

```json
{
   "version": 1,
   "products": [
      {"name": "AMD Ryzen 7 7800X3D", "category": "CPU", "urls": ["https://www.idealo.fr/prix/example"]},
      {"name": "NVIDIA RTX 4080", "category": "GPU", "urls": ["https://www.amazon.fr/product/example"]}
   ]
}
```

Rules:
- `version` must be 1
- Each product needs a non-empty `urls` list
- URLs must start with http/https
- Names should be unique (duplicates merge URLs)

**Supported Categories**: Mouse, Keyboard, PSU, RAM, SSD, GPU, Cooler, Motherboard, CPU, Upgrade Kit

### 2. Run the Scraper

#### Basic Usage
```bash
cd /home/seb/GITRepos/newbuild-scraper
python src/main.py
```

#### Advanced Options
```bash
# Only scrape specific sites
python src/main.py --site amazon.fr

# Skip HTML generation
python src/main.py --no-html

# Use SQLite database (recommended)
python src/main.py --db-type sqlite

# Only scrape products with no recent entries
python src/main.py --new-products-only --max-age-hours 24
```

### 3. JSON Import

When you run `python src/main.py`, new products/urls in `products.json` are imported into SQLite (non-destructive). No separate load step needed.

Legacy CSV loader (`produits.csv` + `load_products.py`) is deprecated.

## Database Management

### Configuration

Create a `database.conf` file to configure the database:

```ini
[database]
type = sqlite
sqlite_path = price_tracker.db
csv_products_file = (legacy only – prefer products.json)
csv_history_file = historique_prix.csv
```

### Manual Database Operations

```bash
# Initialize SQLite database
python -c "from src.database import DatabaseManager; db = DatabaseManager('price_tracker.db'); print('Database initialized')"

# Export SQLite data to CSV (for GitHub Actions)
python -c "from src.database import DatabaseManager; db = DatabaseManager('price_tracker.db'); db.export_to_csv(); print('Exported to CSV')"
```

## Idealo Vendor Extraction

### How It Works

1. **Product Discovery**: Scrapes Idealo product pages to find vendor offers
2. **Vendor Extraction**: Uses 4-strategy detection:
   - Data attributes (`data-shop-name`)
   - Logo analysis with domain extraction
   - Text pattern matching and cleaning
   - Domain-based vendor identification
3. **Redirect Following**: Follows Idealo redirects to vendor websites
4. **Enhanced Data**: Extracts marketplace status and Prime eligibility

### Example Output

Instead of generic "Idealo" entries, you get detailed vendor information:
- **Vendor**: Amazon.fr - 109€ (Prime)
- **Marketplace Status**: Direct sale vs. marketplace seller
- **Prime Eligibility**: Clear indication for Amazon products

## HTML Dashboard

### Generated Files

- `output.html` - Main dashboard with vendor-aware displays
- Includes vendor names, marketplace indicators, and Prime status
- Historical price graphs with vendor information
- Category summaries with best vendor prices

### Dashboard Features

- **Product Cards**: Show vendor details and marketplace status
- **Price History**: Toggle historical prices for each product
- **Summary Table**: Best prices per category with vendor information
- **Total Evolution**: Price trends excluding upgrade kit alternatives
- **Visual Indicators**: Yellow boxes for upgrade kit/alternative products

## Troubleshooting

### Common Issues

1. **Cookie Consent Blocking**
   - The system handles consent automatically for Idealo, Amazon, Corsair
   - If scraping fails, check console output for consent dialog issues

2. **Vendor Extraction Failures**
   - Check logs for vendor detection strategy used
   - Verify Idealo page structure hasn't changed
   - Some vendors may not have structured data attributes

3. **Database Migration**
   - SQLite database is created automatically
   - Existing CSV data is migrated on first run
   - CSV export maintains GitHub Actions compatibility

### Debug Mode

Enable detailed logging for specific domains:

```bash
python src/main.py --debug-domains idealo.fr amazon.fr
```

## Automation with GitHub Actions

### Workflow Integration

The system maintains CSV compatibility for GitHub Actions:
- SQLite database exports to CSV automatically
- GitHub Actions workflows continue working unchanged
- Enhanced data (vendor info) available in both formats

### Secrets Configuration

Required GitHub secrets:
- `DISCORD_WEBHOOK_URL` - For price alerts
- Database configuration through environment variables

## Product Categories and Pricing

### Category System

- **Regular Products**: Included in total price calculations
- **Upgrade Kit Category**: Excluded from totals (alternatives to individual components)
- **Visual Distinction**: Upgrade kits shown with yellow warning boxes

### Price Calculations

- **Summary Table**: Best price per category with vendor details
- **Total Evolution**: Historical total excluding upgrade kit alternatives
- **Vendor Comparison**: Shows marketplace vs. direct sale pricing

## Advanced Features

### Caching System

- **Success Cache**: 6 hours for successful price extractions
- **Failure Cache**: 24 hours for failed attempts with exponential backoff
- **Selective Scraping**: Option to skip recently updated products

### Multi-Strategy Extraction

1. **Data Attributes**: Primary extraction from structured data
2. **Logo Analysis**: Vendor identification from logos and images
3. **Text Patterns**: Cleaning and pattern matching for vendor names
4. **Domain Detection**: Fallback using URL domains for vendor identification

### Error Handling

- **Failed URL Tracking**: Comprehensive logging of problematic URLs
- **Retry Mechanisms**: Automatic retry with exponential backoff
- **Graceful Degradation**: Falls back to basic price extraction if vendor detection fails

## Development

### Adding New Sites

1. Create site module in `/src/sites/`
2. Implement standardized interface:
   - `get_price()` function
   - Selector configuration
   - Anti-bot handling
3. Add site configuration to `config.py`
4. Update documentation

### Testing

```bash
# Test specific sites
python src/main.py --site topachat.com

# Test with debug output
python src/main.py --debug-domains topachat.com idealo.fr

# Test product loading
python load_products.py --dry-run
```

## Support

For issues or questions:
1. Check the logs in `scraper.log`
2. Verify database configuration
3. Test with single sites using `--site` parameter
4. Review vendor extraction logs for Idealo issues
