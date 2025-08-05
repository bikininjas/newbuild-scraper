"""Browser stealth and anti-detection configurations."""

from pathlib import Path
from utils import get_user_agent


def get_stealth_browser_args():
    """Get browser launch arguments for anti-detection."""
    return [
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


def get_stealth_context_options():
    """Get browser context options for anti-detection."""
    return {
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


def add_stealth_scripts(page):
    """Add stealth JavaScript to hide automation detection."""
    js_path = Path(__file__).parent / "stealth.js"
    try:
        with open(js_path, "r", encoding="utf-8") as js_file:
            stealth_js = js_file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Stealth JavaScript file not found at {js_path}. Please ensure 'stealth.js' exists in the same directory as 'stealth.py'.")
    page.add_init_script(stealth_js)


def should_use_stealth_mode(url):
    """Determine if stealth mode should be used for a URL."""
    stealth_sites = [
        "pccomponentes.fr",
        "bpm-power.com",
        "idealo.fr"
    ]
    return any(site in url for site in stealth_sites)
