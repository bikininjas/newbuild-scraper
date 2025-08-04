# 🚀 Refactored Scraper Architecture

## Overview

The scraper has been refactored into a modular architecture that separates concerns and makes it easier to maintain and extend.

## New Directory Structure

```
src/
├── sites/              # Site-specific configurations and handlers
│   ├── __init__.py
│   ├── config.py       # Selector configurations for all sites
│   ├── pccomponentes.py # PCComponentes specific logic
│   └── topachat.py     # TopAchat specific logic
├── antibot/            # Anti-bot detection and evasion
│   ├── __init__.py
│   ├── stealth.py      # Browser stealth configurations
│   └── detection.py    # Anti-bot detection and handling
├── scraper_new.py      # New modular scraper
└── scraper.py          # Legacy scraper (for fallback)
```

## Key Improvements

### 🎯 **Site-Specific Handling**
- **Centralized Configuration**: All site selectors in `sites/config.py`
- **Modular Site Logic**: Each complex site gets its own module
- **Easy Extension**: Add new sites by updating config or creating new modules

### 🛡️ **Enhanced Anti-Bot Protection**
- **Stealth Mode**: Advanced browser fingerprinting evasion
- **Smart Detection**: Automatic anti-bot system detection
- **Adaptive Behavior**: Different strategies per site

### 🔧 **Cookie Consent Handling**
- **PCComponentes**: Handles `.button_styledChild__14nwxvlr` and other consent buttons
- **Universal Fallback**: Generic cookie consent handling for other sites
- **Robust Detection**: Multiple selector strategies

## Usage

### Basic Usage

## Idealo-First Scraping Strategy

### How it works
- **Primary Source:** Idealo is used as the main price source for all products.
- **Reduced Frequency:** Scraping is performed less often and requests are staggered to avoid anti-bot triggers.
- **Fallback Logic:** If Idealo does not return a price, the scraper automatically falls back to other sites (TopAchat, Amazon, LDLC, etc.).
- **Selector Optimization:** The selector `.productOffers-listItemOfferPrice` is used and monitored for changes. If Idealo's HTML changes, update this selector in `sites/config.py`.
- **Monitoring:** Regularly check Idealo's HTML structure and update selectors as needed.

### Example Usage
```python
from src.scraper_new import get_price_playwright
from src.sites.config import get_site_selector

url = "https://www.idealo.fr/prix/202107846/logitech-g502-x-lightspeed.html"
selectors = get_site_selector(url)
price = get_price_playwright(url, selectors)
if price is None:
    # Fallback to other sites if Idealo fails
    url = "https://www.topachat.com/pages/detail2_cat_est_gaming_puis_rubrique_est_wg_pcsou_puis_ref_est_in20014517.html"
    selectors = get_site_selector(url)
    price = get_price_playwright(url, selectors)
```

### Best Practices
- **Scrape Idealo first for all products.**
- **Limit scraping frequency** (e.g., once per day or stagger requests with delays).
- **Monitor selector validity**: If `.productOffers-listItemOfferPrice` fails, inspect Idealo's HTML and update the selector.
- **Log and alert on selector failures** to catch changes early.
- **Fallback only if Idealo fails**: Avoid unnecessary scraping of other sites.

## Site Status

| Site | Status | Special Handling | Notes |
|------|--------|------------------|-------|
| **PCComponentes** | 🔶 **Improved** | Cookie consent + stealth mode | Strong anti-bot, cookies handled |
| **TopAchat** | ✅ **Working** | Custom price extraction | Stable |
| **Amazon** | ✅ **Working** | Standard selectors | Reliable |
| **LDLC** | ✅ **Working** | Standard selectors | Reliable |
| **Materiel.net** | ✅ **Working** | Standard selectors | Reliable |
| **Idealo** | 🔶 **Challenging** | Stealth mode | Anti-bot protection |
| **BPM Power** | 🔶 **Challenging** | Stealth mode | Cloudflare protection |

## PCComponentes Specific Improvements

### ✅ **What's Working**
- Cookie consent popup detection and handling
- Stealth browser mode with realistic fingerprinting
- Enhanced user behavior emulation
- Anti-bot detection and logging

### 🔶 **Current Challenge**
PCComponentes has **very strong anti-bot protection** that persists even after:
- Handling cookie consent
- Using stealth browser mode
- Realistic user behavior emulation
- Non-headless browsing

### 📊 **Typical Output**
```
INFO [PCComponentes] Found cookie button with text: ok
INFO [PCComponentes] Successfully clicked cookie button with text: ok
WARNING Anti-bot protection detected: robot
WARNING Possible anti-bot detected for {url} (Playwright)
```

## Adding New Sites

### 1. Simple Site (selectors only)
Add to `sites/config.py`:
```python
SITE_SELECTORS = {
    # ... existing sites ...
    "newsite.com": [".price", ".product-price"],
}
```

### 2. Complex Site (custom logic)
1. Create `sites/newsite.py`
2. Implement site-specific functions
3. Import and use in `scraper_new.py`

### 3. Anti-Bot Protected Site
1. Add to stealth sites in `antibot/stealth.py`:
```python
def should_use_stealth_mode(url):
    stealth_sites = [
        "pccomponentes.fr",
        "newsite.com",  # Add here
    ]
    return any(site in url for site in stealth_sites)
```

## Migration Guide

The system automatically uses the new scraper with fallback:
- ✅ **New scraper loads**: Uses modular architecture
- ❌ **Import fails**: Falls back to legacy scraper

To force legacy scraper, rename `scraper_new.py` temporarily.

## Future Enhancements

### 🎯 **Planned Improvements**
1. **Proxy Rotation**: Distribute requests across multiple IPs
2. **Session Management**: Maintain longer sessions for better success rates
3. **CAPTCHA Solving**: Integration with CAPTCHA solving services
4. **Rate Limiting**: Smart request spacing per site
5. **Success Rate Monitoring**: Track and optimize per-site success rates

### 🔬 **Research Areas**
- Residential proxy networks for PCComponentes
- Browser automation detection evasion techniques
- Alternative data sources for blocked sites
- Machine learning for adaptive anti-bot strategies

## Debugging

### Enable Detailed Logging
```bash
python src/main.py --debug-domains pccomponentes.fr --site pccomponentes.fr
```

### Test Single URL
```python
import logging
logging.basicConfig(level=logging.INFO)

from src.scraper_new import get_price_playwright
from src.sites.config import get_site_selector

url = "your-test-url"
selectors = get_site_selector(url)
price = get_price_playwright(url, selectors)
```

## Contributing

When adding site-specific logic:
1. **Keep it modular**: Separate files for complex sites
2. **Update config**: Add selectors to `sites/config.py`
3. **Document behavior**: Update this README
4. **Test thoroughly**: Verify with multiple URLs
5. **Handle failures gracefully**: Log warnings, don't crash

---

**Note**: Anti-bot protection is constantly evolving. Some sites may require periodic updates to scraping strategies.
