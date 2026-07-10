# SCOPE: both
# scope: both
"""Deprecation shim — module renamed to token_budget_monitor.

This file exists only for backwards compatibility.  Import from
``cos_lib.token_budget_monitor`` instead.

Reason for rename: this module monitors API *token consumption* (budget),
not action-count rate limits.  The name collided with ``lib/rate_limiter.py``
which IS the action-count governor, causing new contributors to pick the
wrong one.

Scheduled for removal once all importers have migrated.
"""

import warnings

warnings.warn(
    "cos_lib.rate_limit_protection is deprecated and will be removed in a future release. "
    "Use cos_lib.token_budget_monitor instead.",
    DeprecationWarning,
    stacklevel=2,
)

from cos_lib.token_budget_monitor import RateLimitProtection, RateLimitStatus  # noqa: E402, F401

__all__ = [
    "RateLimitProtection",
    "RateLimitStatus",
]
