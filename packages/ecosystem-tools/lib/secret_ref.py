# SCOPE: both
# scope: both
"""Resolve SecretRef objects in configuration dictionaries.

A SecretRef is a dict with keys "source" and "id" that references
a secret value stored in an environment variable, file, or literal.

Usage:
    from lib.secret_ref import resolve_secret_ref, resolve_config_secrets, mask_secrets

    ref = {"source": "env", "id": "GITHUB_TOKEN"}
    value = resolve_secret_ref(ref)  # -> "ghp_abc123..."

    config = {"token": {"source": "env", "id": "API_KEY"}, "name": "my-app"}
    resolve_config_secrets(config)   # mutates in-place
    safe = mask_secrets(config)      # returns copy with '***'

Python 3.9+ compatible.
"""

import copy
import os
from typing import Any, Dict, Optional


def _is_secret_ref(value: Any) -> bool:
    """Check if a value is a SecretRef dict (has 'source' and 'id' keys)."""
    return (
        isinstance(value, dict)
        and "source" in value
        and "id" in value
        and len(value) == 2
    )


def resolve_secret_ref(ref: Dict[str, str]) -> Optional[str]:
    """Resolve a SecretRef object like {"source": "env", "id": "KEY"} to its value.

    Supported sources:
    - "env": reads from environment variable
    - "file": reads from file path
    - "literal": returns the id directly (for non-sensitive defaults)

    Args:
        ref: A dict with "source" and "id" keys.

    Returns:
        The resolved secret value, or None if not found / unreadable.
    """
    source = ref.get("source", "")
    secret_id = ref.get("id", "")

    if source == "env":
        return os.environ.get(secret_id)

    if source == "file":
        try:
            with open(secret_id, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (OSError, IOError):
            return None

    if source == "literal":
        return secret_id

    return None


def resolve_config_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Walk a config dict and resolve all SecretRef objects in-place.

    A SecretRef is any dict with exactly the keys "source" and "id".
    Example: {"token": {"source": "env", "id": "GITHUB_TOKEN"}}
    becomes: {"token": "ghp_abc123..."}

    Nested dicts are traversed recursively. Lists are traversed element-wise.
    If a SecretRef cannot be resolved (returns None), the original ref dict
    is left in place.

    Args:
        config: The configuration dict to process (mutated in-place).

    Returns:
        The same config dict (for chaining convenience).
    """
    for key, value in config.items():
        if _is_secret_ref(value):
            resolved = resolve_secret_ref(value)
            if resolved is not None:
                config[key] = resolved
        elif isinstance(value, dict):
            resolve_config_secrets(value)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if _is_secret_ref(item):
                    resolved = resolve_secret_ref(item)
                    if resolved is not None:
                        value[i] = resolved
                elif isinstance(item, dict):
                    resolve_config_secrets(item)

    return config


def mask_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy with all resolved secret values masked as '***'.

    A value is considered a resolved secret if the key name suggests
    it is sensitive (contains 'secret', 'token', 'key', 'password',
    'credential', 'api_key', or 'apikey', case-insensitive) and the
    value is a non-empty string.

    SecretRef dicts that were NOT resolved are left as-is (they don't
    contain the actual secret value).

    Args:
        config: The configuration dict to mask.

    Returns:
        A deep copy of config with sensitive string values replaced by '***'.
    """
    _SENSITIVE_KEYS = {"secret", "token", "key", "password", "credential", "api_key", "apikey"}

    result = copy.deepcopy(config)
    _mask_recursive(result, _SENSITIVE_KEYS)
    return result


def _mask_recursive(obj: Dict[str, Any], sensitive_keys: set) -> None:
    """Recursively mask sensitive string values in a dict."""
    for key, value in obj.items():
        key_lower = key.lower()
        is_sensitive = any(s in key_lower for s in sensitive_keys)

        if is_sensitive and isinstance(value, str) and value:
            obj[key] = "***"
        elif isinstance(value, dict) and not _is_secret_ref(value):
            _mask_recursive(value, sensitive_keys)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and not _is_secret_ref(item):
                    _mask_recursive(item, sensitive_keys)
