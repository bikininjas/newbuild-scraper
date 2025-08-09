"""High-level HTML generation entrypoint (Phase 1 wrapper)."""

from .data import load_history  # re-export for compatibility
from .render import *  # noqa: F401,F403
from .graph import *  # noqa: F401,F403
