"""Session-scoped order memory.

Stores the most-recently-mentioned Dunder Mifflin order ID within a
conversation so follow-up questions resolve without repetition.
"""
import re
from typing import Any

# In-process session store: maps session_id -> context dict.
# Replace with a Redis or DB-backed store for production.
_store: dict[str, dict[str, Any]] = {}

# Matches order IDs like DM-1037 or dm-1037
_ORDER_PATTERN = re.compile(r"\bDM-\d+\b", re.IGNORECASE)


def extract_and_store(session_id: str, text: str) -> None:
    """Extract an order ID from *text* and store it for *session_id*."""
    match = _ORDER_PATTERN.search(text)
    if match:
        context = _store.setdefault(session_id, {})
        context["active_order_id"] = match.group(0).upper()


def get_context(session_id: str) -> dict[str, Any]:
    """Return the stored memory context for *session_id*, or an empty dict."""
    return dict(_store.get(session_id, {}))


def clear(session_id: str) -> None:
    """Discard the memory context for *session_id*."""
    _store.pop(session_id, None)