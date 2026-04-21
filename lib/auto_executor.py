# SCOPE: both
"""Deprecation shim — lib.auto_executor is replaced by lib.orchestrator_mode_activator.

This module re-exports everything from the canonical module and emits a
DeprecationWarning on import.  It will be removed in v0.16.

Migration:
    # Old
    from lib.auto_executor import AutoExecutor
    # New
    from lib.orchestrator_mode_activator import AutoExecutor
"""
import warnings

warnings.warn(
    "lib.auto_executor is deprecated and will be removed in v0.16. "
    "Use lib.orchestrator_mode_activator instead.",
    DeprecationWarning,
    stacklevel=2,
)

from lib.orchestrator_mode_activator import (  # noqa: F401, E402
    AutoExecutor,
    _is_valkey_reachable,
    _VALKEY_HOST_DEFAULT,
    _VALKEY_PORT_DEFAULT,
    _CONNECT_TIMEOUT_S,
)

__all__ = [
    "AutoExecutor",
    "_is_valkey_reachable",
    "_VALKEY_HOST_DEFAULT",
    "_VALKEY_PORT_DEFAULT",
    "_CONNECT_TIMEOUT_S",
]
