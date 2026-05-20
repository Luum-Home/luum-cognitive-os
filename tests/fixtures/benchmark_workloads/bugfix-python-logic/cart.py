"""Tiny cart total helper with an intentional fixture bug."""


def total_cents(prices_cents: list[int]) -> int:
    """Return the sum of all item prices in cents."""
    total = 0
    for index in range(len(prices_cents) - 1):
        total += prices_cents[index]
    return total
