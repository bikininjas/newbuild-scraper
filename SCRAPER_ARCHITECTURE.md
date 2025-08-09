# Newbuild Scraper Architecture

## Overview

This project follows a modular architecture designed for scalability, maintainability, and ease of extension for new e-commerce sites. The system now includes advanced vendor extraction capabilities for aggregator sites and comprehensive database management.

## Core Components

### `/src/main.py`
- **Purpose**: Main entry point and orchestration
- **Responsibilities**: 
  - Coordinates scraping across all configured sites
  - Manages SQLite data persistence
  - Performs non-destructive JSON (`products.json`) import of product definitions
  - Processes Discord alerts and HTML generation
  - Integrates vendor extraction and marketplace detection

### `/src/sites/`
- **Purpose**: Site-specific scraping implementations with advanced vendor extraction
- **Pattern**: Each site has its own module with standardized interface
- **Current Sites**:
  - `amazon.py` - Amazon France scraping with marketplace and Prime detection
  - `idealo.py` - **ENHANCED** - Advanced vendor aggregator parsing with redirect following
  - `pccomponentes.py` - PC Componentes Spain
  - `topachat.py` - TopAchat France
  - `handler.py` - Generic scraping utilities
  - `config.py` - Site configuration management

### `/src/sites/idealo.py` - Advanced Features
- **Multi-Strategy Vendor Extraction**: 4-tier detection system using data attributes, logos, text patterns, and domains
- **Redirect Following**: Automatic following of Idealo redirects to extract prices from actual vendor websites
- **Cookie Consent Framework**: Comprehensive handling for Idealo, Amazon, Corsair, and vendor-specific dialogs
- **Marketplace Detection**: Distinguishes between marketplace sellers and direct vendor sales
- **Prime Eligibility**: Tracks Amazon Prime eligibility for enhanced purchasing decisions

### `/src/database/` (Legacy Shim)

- **Purpose**: Backwards compatibility only. Provides a lazy shim exposing `DatabaseManager` for older imports.
- **Components**:
  - `models.py` - **ENHANCED** - Database models (products, urls, price_history with vendor fields, cache, product_issues)
  - `config.py` - Database configuration (currently forces SQLite)
  - `__init__.py` - Shim that emits a one‑time deprecation warning; new code must import `DatabaseManager` from `scraper.persistence.sqlite`.

### `/src/scraper/persistence/`

- **Purpose**: New persistence layer (Phase 3 refactor) decoupling higher layers from raw SQL.
- **Components**:
  - `sqlite.py` - `DatabaseManager` implementation (migrated from legacy `database.manager` which has been removed)
  - `repositories.py` - Intention‑revealing thin wrappers (e.g. `record_price`, `log_issue`, `products_needing_scrape`) used by scraping & HTML layers.

### Layering

```text
products.json -> scraper.catalog.loader -> repositories -> persistence.sqlite.DatabaseManager -> SQLite
scraper / sites -> repositories (migrating; some direct calls remain temporarily)
html generation -> DatabaseManager (to be migrated gradually)
```

The repositories layer enables future alternative backends and simplifies unit testing.

### `products.json`

- **Purpose**: Canonical product declaration file (versioned). Replaces legacy CSV inputs.
- **Import Semantics**: Non-destructive sync (adds new products/URLs; never deletes existing DB rows to preserve history).

### `/src/antibot/`

- **Purpose**: Anti-detection and stealth browsing
- **Components**:
  - `detection.py` - Bot detection avoidance
  - `stealth.py` - Browser stealth configuration
  - `stealth.js` - JavaScript stealth injection

### `/src/htmlgen/`

- **Purpose**: HTML report generation with vendor-aware displays
- **Components**:
  - `render.py` - **ENHANCED** - HTML template rendering with vendor information
  - `data.py` - Data processing with marketplace and Prime status aggregation
  - `graph.py` - Price history chart generation
  - `normalize.py` - Price data normalization
  - `price_utils.py` - Price calculation utilities
  - `constants.py` - UI constants and styling

### `/src/utils/`

- **Purpose**: Shared utility functions
- **Components**:
  - `__init__.py` - Core utilities (price cleaning, formatting)

## Data Flow

1. **Product Import**: `products.json` parsed & validated; new products/URLs synced into SQLite
2. **Site Processing**: Each site module extracts prices using specialized selectors
3. **Price Normalization**: `clean_price()` function handles various price formats (€579.95, 579€95, etc.)
4. **Data Persistence**: Results saved to SQLite (`price_history` table)
5. **Report Generation**: HTML reports with price history charts and comparisons
6. **Alert System**: Discord notifications for significant price changes

## Key Design Patterns

### Site Handler Pattern

Each site implements a consistent interface:

```python
def scrape_site_name(url, product_name):
  # Returns (price, availability, timestamp)
```

### Price Normalization

Centralized price cleaning handles multiple formats:

- European format: "579,95 €"
- French format with superscript: "579€(95)"  <!-- simplified to avoid inline HTML -->
- Simple format: "579.95"

### Stealth Architecture

Multi-layered anti-detection:

- Browser fingerprint randomization
- JavaScript stealth injection
- User agent rotation
- Request timing variation

## Extension Points

### Adding New Sites

1. Create new module in `/src/sites/`
2. Implement scraping function following established pattern
3. Add site configuration to `config.py`
4. Update main orchestration logic

### Adding New Features

- HTML generation: Extend `/src/htmlgen/` modules
- Alert systems: Modify alert logic in main.py
- Data processing: Add utilities to `/src/utils/`

## Architecture Benefits

- **Modularity**: Each site is isolated and independently maintainable
- **Scalability**: Easy to add new sites without affecting existing ones
- **Maintainability**: Clear separation of concerns
- **Testability**: Each component can be tested in isolation
- **Robustness**: Anti-detection measures protect against blocking
