"""Legacy database package.

Deprecated shim: `DatabaseManager` now lives in `scraper.persistence.sqlite`.
We provide a lazy attribute to avoid circular import during initialization.
New code should import: `from scraper.persistence.sqlite import DatabaseManager`.
"""

from .models import Product, PriceHistory, URLEntry, CacheEntry  # re-export
from .config import DatabaseConfig  # re-export
import logging

_warning_emitted = False


def __getattr__(name: str):  # pragma: no cover - simple shim
    global _warning_emitted
    if name == "DatabaseManager":
        if not _warning_emitted:
            logging.getLogger(__name__).warning(
                "database.DatabaseManager is deprecated; import from scraper.persistence.sqlite instead (will be removed in a future release)"
            )
            _warning_emitted = True
        from scraper.persistence.sqlite import DatabaseManager as _DM

        return _DM
    raise AttributeError(name)


__all__ = ["DatabaseManager", "Product", "PriceHistory", "URLEntry", "CacheEntry", "DatabaseConfig"]
