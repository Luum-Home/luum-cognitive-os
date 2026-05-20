# Refactor Python Multifile Fixture

License: MIT-compatible repository-owned fixture.

Workload: refactor duplicated normalization logic in `orders.py` and `customers.py` into a shared helper while preserving tests.
Determinism: no network, no external services, Python standard library only.
Success command: `python -m pytest tests -q`.
