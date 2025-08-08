"""Detection and handling of anti-bot protection systems."""

import logging


def detect_anti_bot_protection(content):
    """Detect common anti-bot protection systems in page content."""
    anti_bot_indicators = [
        "cloudflare",
        "checking your browser",
        "please wait",
        "verification",
        "captcha",
        "robot",
        "bot detection",
        "security check",
        "ddos protection",
        "javascript required",
        "enable javascript",
        "turnstile",
    ]

    content_lower = content.lower()
    detected_systems = [
        indicator for indicator in anti_bot_indicators if indicator in content_lower
    ]

    if detected_systems:
        logging.warning(f"Anti-bot protection detected: {', '.join(detected_systems)}")
        return True
    return False


def get_anti_bot_wait_time(url):
    """Get appropriate wait time based on site's anti-bot protection."""
    wait_times = {
        "pccomponentes.fr": 15000,  # 15 seconds
        "bpm-power.com": 12000,  # 12 seconds
        "idealo.fr": 8000,  # 8 seconds
        "grosbill.com": 5000,  # 5 seconds
    }

    for site, wait_time in wait_times.items():
        if site in url:
            return wait_time

    return 3000  # Default 3 seconds


def handle_cloudflare_protection(page):
    """Handle Cloudflare protection specifically."""
    try:
        # Wait for Cloudflare challenge to complete
        page.wait_for_selector("body", timeout=20000)

        # Check if we're still on a Cloudflare page
        if (
            "cloudflare" in page.url.lower()
            or "cf-browser-verification" in page.content()
        ):
            logging.warning("Cloudflare challenge detected, waiting for completion...")
            page.wait_for_timeout(10000)

        return True
    except Exception as e:
        logging.warning(f"Cloudflare handling failed: {e}")
        return False
