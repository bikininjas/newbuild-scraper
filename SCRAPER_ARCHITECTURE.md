# Newbuild Scraper Architecture

## Overview

This project follows a modular architecture designed for scalability, maintainability, and ease of extension for new e-commerce sites.

## Core Components

### `/src/main.py`
- **Purpose**: Main entry point and orchestration
- **Responsibilities**: 
  - Coordinates scraping across all configured sites
  - Handles CSV data persistence
  - Manages Discord alerts
  - Processes configuration from `produits.csv`

### `/src/sites/`
- **Purpose**: Site-specific scraping implementations
- **Pattern**: Each site has its own module with standardized interface
- **Current Sites**:
  - `amazon.py` - Amazon France scraping
  - `idealo.py` - Idealo price comparison
  - `pccomponentes.py` - PC Componentes Spain
  - `topachat.py` - TopAchat France
  - `handler.py` - Generic scraping utilities
  - `config.py` - Site configuration management

### `/src/antibot/`
- **Purpose**: Anti-detection and stealth browsing
- **Components**:
  - `detection.py` - Bot detection avoidance
  - `stealth.py` - Browser stealth configuration
  - `stealth.js` - JavaScript stealth injection

### `/src/htmlgen/`
- **Purpose**: HTML report generation and data visualization
- **Components**:
  - `render.py` - Main HTML template rendering
  - `data.py` - Data processing and aggregation
  - `graph.py` - Price history chart generation
  - `normalize.py` - Price data normalization
  - `price_utils.py` - Price calculation utilities
  - `constants.py` - UI constants and styling

### `/src/utils/`
- **Purpose**: Shared utility functions
- **Components**:
  - `__init__.py` - Core utilities (price cleaning, formatting)

## Data Flow

1. **Configuration Loading**: `produits.csv` defines products and URLs to monitor
2. **Site Processing**: Each site module extracts prices using specialized selectors
3. **Price Normalization**: `clean_price()` function handles various price formats (€579.95, 579€95, etc.)
4. **Data Persistence**: Results saved to `historique_prix.csv` with timestamps
5. **Report Generation**: HTML reports created with price history charts and comparisons
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
- French format with superscript: "579€<sup>95</sup>"
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
