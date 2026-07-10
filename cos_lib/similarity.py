"""Shared similarity helpers."""
from __future__ import annotations


def jaccard(left: set[str], right: set[str]) -> float:
    """Return Jaccard similarity for two sets."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def pair_key(left: str, right: str) -> str:
    """Return stable order-insensitive pair key."""
    return " :: ".join(sorted([left, right]))
