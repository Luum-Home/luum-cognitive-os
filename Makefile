# Cognitive OS — test + dev targets
# All python invocations go through `uv run` so UV-managed deps
# (fastmcp, openai SDK, etc.) are visible. See docs/reports/next-session-handoff-2026-04-20.md.

.PHONY: help test test-fast test-unit test-integration test-e2e test-chaos test-all test-changed smoke audit clean

PY := uv run python3
PYTEST := uv run pytest

help:
	@echo "Targets:"
	@echo "  test-fast         Unit tests, paralelo (-n auto). <30s."
	@echo "  test-unit         Unit tests serial (useful for debugging xdist conflicts)."
	@echo "  test-integration  Integration tests serial (tmp state sensitive)."
	@echo "  test-e2e          E2E smoke + full e2e suite."
	@echo "  test-chaos        Chaos tests."
	@echo "  test-all          Full suite serial (slowest, most complete)."
	@echo "  test-changed      Only tests affected by git diff HEAD."
	@echo "  smoke             bash scripts/cos-smoke.sh — critical path e2e."
	@echo "  audit             Aspirational audit + self-knowledge refresh."
	@echo "  clean             Prune metrics + caches (keeps last 1000 JSONL events)."
	@echo ""
	@echo "All python commands run via 'uv run' — plain 'python3' or 'pytest' will miss UV-managed deps."

test: test-fast

test-fast:
	$(PYTEST) tests/unit/ -n auto --tb=line

test-unit:
	$(PYTEST) tests/unit/ --tb=line

test-integration:
	$(PYTEST) tests/integration/ -m "not slow and not docker" --tb=short

test-e2e:
	bash scripts/cos-smoke.sh -v
	$(PYTEST) tests/e2e/ -v

test-chaos:
	$(PYTEST) tests/chaos/ -v

test-all:
	$(PYTEST) tests/ --ignore=tests/unit/test_aider_streaming_adapter.py -q --tb=short

test-changed:
	@files=$$(git diff --name-only HEAD | grep -E '\.py$$' || true); \
	if [ -z "$$files" ]; then echo "No changed .py files"; exit 0; fi; \
	$(PYTEST) $$(echo $$files | tr ' ' '\n' | grep -E 'tests/' || echo tests/) --tb=short

smoke:
	bash scripts/cos-smoke.sh -v

audit:
	$(PY) scripts/aspirational-audit.py --dry-run
	$(PY) scripts/cos-build-self-knowledge.py

clean:
	find .cognitive-os/metrics -name "*.jsonl" -size +10M -exec tail -c 5M {} + 2>/dev/null || true
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true
