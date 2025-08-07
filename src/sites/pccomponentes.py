"""PCComponentes specific scraping logic."""

import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError


# Mouse movement coordinates for anti-bot detection
PCCOMPONENTES_MOUSE_MOVES = [
    (100, 200),
    (200, 300),
    (300, 400),
    (400, 500),
    (500, 600),
    (600, 700),
    (700, 800),
    (800, 900),
    (900, 1000),
    (1000, 1100),
]


def handle_pccomponentes_behavior(page, url):
    """Handle PCComponentes-specific behavior including cookie consent."""
    try:
        handle_cookie_consent(page)
    except Exception as e:
        logging.warning(f"Cookie consent handling failed for {url}: {e}")

def handle_cookie_consent(page):
    """Handle cookie consent popup with multiple selector fallbacks."""
    logging.info("[PCComponentes] Attempting to handle cookie consent popup")
    
    # Common cookie consent selectors for PCComponentes
    cookie_selectors = [
        '#didomi-notice-agree-button',  # Didomi consent manager
        '.didomi-notice-component-button[aria-label*="Tout accepter"]',
        '.didomi-notice-component-button[aria-label*="Accept All"]',
        '.didomi-button-standard',
        '.didomi-continue-without-agreeing',  # Didomi alternative
        '.cmp-accept-all',  # CMP (Consent Management Platform)
        '.gdpr-accept',  # GDPR accept button
    ]
    
    for selector in cookie_selectors:
        try:
            # Check if the element exists and is visible
            element = page.locator(selector)
            if element.is_visible(timeout=2000):
                logging.info(f"[PCComponentes] Found cookie consent button with selector: {selector}")
                # Scroll to element to ensure it's in view
                element.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                element.click(timeout=3000)
                page.wait_for_timeout(2000)  # Wait for the popup to disappear
                logging.info("[PCComponentes] Successfully clicked cookie consent button")
                return
        except (PlaywrightTimeoutError, PlaywrightError):
            continue  # Try next selector


def emulate_pccomponentes_user(page):
    """Emulate realistic user behavior for PCComponentes."""
    try:
        # First, try to handle cookie consent popup
        handle_cookie_consent(page)
        
        # Add more natural-looking user behavior
        page.wait_for_timeout(2000)
        
        # Scroll down slowly to simulate reading
        for _ in range(3):
            page.mouse.wheel(0, 300)  # Scroll down 300 pixels
            page.wait_for_timeout(1000)
        
        # Then perform user emulation with mouse movements
        for x, y in PCCOMPONENTES_MOUSE_MOVES[:5]:  # Reduce movements to be more natural
            page.mouse.move(x, y)
            page.wait_for_timeout(200)  # Shorter delays between movements
            
        # Simulate reading behavior
        page.keyboard.press("PageDown")
        page.wait_for_timeout(2000)
        page.keyboard.press("PageDown")
        page.wait_for_timeout(2000)
        
        # Give more time for any lazy-loaded content
        page.wait_for_timeout(5000)
        
    except Exception as e:
        logging.warning(f"[PCComponentes] User emulation failed: {e}")
