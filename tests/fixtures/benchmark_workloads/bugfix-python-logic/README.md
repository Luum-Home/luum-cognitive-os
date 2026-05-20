# Bugfix Python Logic Fixture

License: MIT-compatible repository-owned fixture.

Workload: fix the off-by-one bug in `cart.py` so the included pytest suite passes.
Determinism: no network, no external services, Python standard library only.
Success command: `python -m pytest tests/test_cart.py -q`.
