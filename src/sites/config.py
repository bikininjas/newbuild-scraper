"""Site configuration and selector management."""

# Selector constants
PRICE = ".price"
PRICE_LG = ".price-lg"
PRODUCT_PRICE = ".product-price"
OLD_PRICE = ".old-price"
NEW_PRICE = ".new-price"

# Site-specific selector configurations
SITE_SELECTORS = {
    "amazon.fr": [
        ".a-price-whole",
        ".a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen",
        ".a-price .a-offscreen",
        "span.a-price-symbol + span.a-price-whole",
        ".a-price-range .a-price .a-offscreen",
        "#priceblock_dealprice",
        "#priceblock_ourprice",
        ".a-price-current .a-price-whole",
    ],
    "caseking.de": [".js-unit-price"],
    "ldlc.com": [PRICE, NEW_PRICE, ".price__amount"],
    "topachat.com": [
        ".offer-price__price.svelte-hgy1uf",
        ".offer-price__price",
        "span.offer-price__price",
        ".price",
        "[data-price]",
        ".product-price",
        ".price-value",
    ],
    "alternate.fr": [PRICE, ".product-detail-price"],
    "materiel.net": [".o-product__price", ".o-product__price o-product__price--promo"],
    "pccomponentes.fr": [".price", ".product-price", "#price"],
    "grosbill.com": [".p-3x"],
    "idealo.fr": [".productOffers-listItemOfferPrice"],
    "bpm-power.com": [".prezzoSchedaProd"],
    "rueducommerce.fr": [PRICE],
}

# Default selectors for unknown sites
DEFAULT_SELECTORS = [PRICE, PRODUCT_PRICE, "#price"]


def get_site_selector(url):
    """Get the appropriate selectors for a given URL."""
    for domain, selectors in SITE_SELECTORS.items():
        if domain in url:
            return selectors
    return DEFAULT_SELECTORS


def is_site_supported(url, site_name):
    """Check if a URL belongs to a specific site."""
    return site_name in url
