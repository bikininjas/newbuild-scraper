"""PCComponentes specific scraping logic."""

import logging


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


def handle_pccomponentes_cookies(page):
    """Handle cookie consent popup for PCComponentes."""
    try:
        # Wait longer for the page to fully load and any consent popups to appear
        page.wait_for_timeout(3000)
        
        # Check for common anti-bot protection patterns first
        content = page.content()
        if any(term in content.lower() for term in ['cloudflare', 'checking your browser', 'please wait', 'verification']):
            logging.warning("[PCComponentes] Anti-bot protection detected, waiting longer...")
            page.wait_for_timeout(10000)  # Wait 10 seconds for Cloudflare/similar
        
        # Common cookie consent selectors to try (most specific first)
        cookie_selectors = [
            '.button_styledChild__14nwxvlr',  # PCComponentes specific consent button
            '#onetrust-accept-btn-handler',  # OneTrust cookie banner
            '.ot-sdk-show-settings',  # OneTrust settings
            'button[data-testid="accept-all"]',  # Accept all button
            'button[aria-label*="Accept"]',  # Aria label accept
            'button[title*="Accept"]',  # Title accept
            'button[id*="accept"]',  # Any button with 'accept' in id
            'button[class*="accept"]',  # Any button with 'accept' in class
            'button[class*="consent"]',  # Any button with 'consent' in class
            '.consent-accept',  # Generic consent accept
            '.cookie-accept',  # Generic cookie accept
            '[data-cy="accept-all"]',  # Cypress data attribute
            '[data-testid*="accept"]',  # TestID accept
            '#didomi-notice-agree-button',  # Didomi consent manager
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
            except Exception:
                continue  # Try next selector
                
        # If no specific selector worked, try to find any button containing accept-like text
        accept_texts = [
            "accepter tout", "accept all", "tout accepter", "accepter", "accept", 
            "j'accepte", "continuer", "continue", "ok", "fermer", "close"
        ]
        for text in accept_texts:
            try:
                element = page.locator(f'button:has-text("{text}")')
                if element.is_visible(timeout=1000):
                    logging.info(f"[PCComponentes] Found cookie button with text: {text}")
                    element.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    element.click(timeout=3000)
                    page.wait_for_timeout(2000)
                    logging.info("[PCComponentes] Successfully clicked cookie button with text: " + text)
                    return
            except Exception:
                continue
                
        logging.warning("[PCComponentes] No cookie consent popup found or could not be handled")
        
    except Exception as e:
        logging.warning(f"[PCComponentes] Cookie handling failed: {e}")


def emulate_pccomponentes_user(page):
    """Emulate realistic user behavior for PCComponentes."""
    try:
        # First, try to handle cookie consent popup
        handle_pccomponentes_cookies(page)
        
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
