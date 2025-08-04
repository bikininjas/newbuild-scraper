import time
import random
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging
from utils import get_user_agent, clean_price

# Selector constants
PRICE = ".price"
PRICE_LG = ".price-lg"
PRODUCT_PRICE = ".product-price"
OLD_PRICE = ".old-price"
NEW_PRICE = ".new-price"

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


def get_site_selector(url):
    # Extract site checks to variables for better performance
    is_topachat = "topachat.com" in url

    if "amazon.fr" in url:
        return [".a-price-whole"]
    if "caseking.de" in url:
        return [".js-unit-price"]
    if "ldlc.com" in url:
        return [PRICE, NEW_PRICE, ".price__amount"]
    if is_topachat:
        # Try multiple selectors for topachat.com, ordered from most specific to more generic
        return [
            ".offer-price__price.svelte-hgy1uf",
            ".offer-price__price",
            "span.offer-price__price",
        ]
    if "alternate.fr" in url:
        return [PRICE, ".product-detail-price"]
    if "materiel.net" in url:
        return [".o-product__price", ".o-product__price o-product__price--promo"]
    if "pccomponentes.fr" in url:
        return [".price", ".product-price", "#price"]
    if "grosbill.com" in url:
        return [".p-3x"]
    if "idealo.fr" in url:
        return [".productOffers-listItemOfferPrice"]
    if "bpm-power.com" in url:
        return [".prezzoSchedaProd"]
    if "rueducommerce.fr" in url:
        return [PRICE]
    return [PRICE, PRODUCT_PRICE, "#price"]


def get_price_requests(url, site_selectors):
    headers = {"User-Agent": get_user_agent()}
    time.sleep(random.uniform(2, 5))
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Fetched {url} with requests, status {resp.status_code}")
        if resp.status_code != 200:
            logging.warning(f"Non-200 status code for {url}: {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for selector in site_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                return clean_price(price_elem.get_text())
        logging.warning(
            f"No price found for {url} with selectors {site_selectors}. HTML snippet: {resp.text[:500]}"
        )
        if "captcha" in resp.text.lower() or "robot" in resp.text.lower():
            logging.warning(f"Possible anti-bot detected for {url}")
    except Exception as e:
        logging.error(f"Requests error for {url}: {e}")
    return None


def emulate_pccomponentes_user(page):
    try:
        # First, try to handle cookie consent popup
        handle_pccomponentes_cookies(page)
        
        # Then perform user emulation
        for x, y in PCCOMPONENTES_MOUSE_MOVES:
            page.mouse.move(x, y)
        page.keyboard.press("PageDown")
        page.keyboard.press("PageDown")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(5000)
    except Exception as e:
        logging.warning(f"[Playwright] User emulation failed: {e}")

def handle_pccomponentes_cookies(page):
    """Handle cookie consent popup for PCComponentes"""
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
        logging.warning(f"[Playwright] User emulation failed: {e}")

def wait_for_topachat_price(page):
    try:
        page.wait_for_selector(".offer-price__price", timeout=10000)
    except Exception:
        logging.warning("[Playwright] .offer-price__price not found after wait")

def extract_topachat_price(elem):
    direct_texts = [t for t in elem.strings if t.strip()]
    main_text = direct_texts[0] if direct_texts else elem.get_text(strip=True)
    match = re.search(r"([\d.,]+)\s*€", main_text)
    if match:
        price_str = match.group(1)
        price = clean_price(price_str)
        if price:
            return price
    if "€" in main_text:
        price_str = main_text.split("€")[0].strip()
        price = clean_price(price_str)
        if price:
            return price
    return None

def extract_price_from_elems(price_elems, is_topachat):
    for elem in price_elems:
        if is_topachat:
            price = extract_topachat_price(elem)
        else:
            text = elem.get_text(strip=True)
            price = clean_price(text)
        if price:
            return price
    return None

def get_price_playwright(url, site_selectors):
    is_topachat = "topachat.com" in url
    is_pccomponentes = "pccomponentes.fr" in url

    try:
        with sync_playwright() as p:
            headless_mode = not is_pccomponentes
            
            # Enhanced browser launch args for anti-detection
            launch_args = [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-default-apps",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
            ]
            
            browser = p.chromium.launch(
                headless=headless_mode,
                args=launch_args
            )
            
            # Enhanced context with realistic viewport and permissions
            context_options = {
                "user_agent": get_user_agent(),
                "locale": "fr-FR",
                "viewport": {"width": 1920, "height": 1080},
                "screen": {"width": 1920, "height": 1080},
                "timezone_id": "Europe/Paris",
                "permissions": ["geolocation"],
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                },
            }
            
            context = browser.new_context(**context_options)
            
            # Add stealth measures to hide automation
            page = context.new_page()
            
            # Override webdriver detection
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Override the plugins property to use a fake value
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Override the languages property to use a fake value
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fr-FR', 'fr', 'en-US', 'en'],
                });
                
                // Override chrome runtime
                window.chrome = {
                    runtime: {},
                };
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Navigate with more realistic timing
            page.goto(url, timeout=45000, wait_until="domcontentloaded")

            if is_pccomponentes:
                emulate_pccomponentes_user(page)
                page.wait_for_timeout(10000)  # Longer wait for PCComponentes
            else:
                if is_topachat:
                    wait_for_topachat_price(page)
                page.wait_for_timeout(3000)

            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            for selector in site_selectors:
                price_elems = soup.select(selector)
                if price_elems:
                    price = extract_price_from_elems(price_elems, is_topachat)
                    if price is not None:
                        browser.close()
                        return price

            browser.close()
            logging.warning(
                f"No price found for {url} with selectors {site_selectors} (Playwright). HTML snippet: {content[:500]}"
            )
            if "captcha" in content.lower() or "robot" in content.lower():
                logging.warning(f"Possible anti-bot detected for {url} (Playwright)")
    except Exception as e:
        logging.error(f"Playwright error for {url}: {e}")
    return None
