# SCOPE: both
"""Shared token loader for portability tests.

Portability tests check that committed source files contain no
consumer-specific identifiers. The full token list lives **outside** the
repo at ``.cognitive-os/private/blocked-strings.txt`` (gitignored),
which is the same file Gate 1 (``.githooks/pre-commit``) reads.

This loader returns a tuple of (tokens, source_label) where
``source_label`` describes whether the operator's private list was
loaded or a placeholder fallback was used. Tests use the label in
assertion messages so a failure is always interpretable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PRIVATE_BLOCKED = _REPO_ROOT / ".cognitive-os" / "private" / "blocked-strings.txt"

# Placeholder tokens used when the operator's private list is absent.
# These names are deliberately NOT real consumer identifiers — when
# the private list isn't configured, the test still verifies the
# committed source doesn't accidentally contain these illustrative
# placeholders, but the falsification probe for *real* tokens
# requires the private list to be present.
_PLACEHOLDER_TOKENS: Tuple[str, ...] = (
    "consumer-alpha",
    "consumer-beta",
    "consumer-gamma",
    "service-alpha",
    "service-beta",
    "service-gamma",
    "service-alpha-go",
    "Consumer Alpha",
    "example-services/",
    "services/example",
)


def load_blocked_tokens() -> Tuple[Tuple[str, ...], str]:
    """Return ``(tokens, source_label)`` for portability assertions.

    Resolution order (matches Gate 1):
    1. ``COS_BLOCKED_STRINGS_FILE`` env override (if set and readable)
    2. ``.cognitive-os/private/blocked-strings.txt``
    3. Placeholder list (fallback — emits a label that flags this)
    """
    override = os.environ.get("COS_BLOCKED_STRINGS_FILE", "").strip()
    candidate = Path(override) if override else _PRIVATE_BLOCKED
    if candidate.is_file():
        tokens = tuple(
            line.strip()
            for line in candidate.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if tokens:
            return tokens, f"private list ({candidate})"
    return _PLACEHOLDER_TOKENS, "placeholder fallback (no private list configured)"
