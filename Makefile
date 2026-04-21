# Cognitive OS — test + dev targets
# See docs/reports/next-session-handoff-2026-04-20.md for roadmap.

.PHONY: help test test-fast test-unit test-integration test-e2e test-chaos test-all test-changed smoke audit clean

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

test: test-fast

test-fast:
	pytest tests/unit/ -n auto --tb=line

test-unit:
	pytest tests/unit/ --tb=line

test-integration:
	pytest tests/integration/ -m "not slow and not docker" --tb=short

test-e2e:
	bash scripts/cos-smoke.sh -v
	pytest tests/e2e/ -v

test-chaos:
	pytest tests/chaos/ -v

test-all:
	pytest tests/ --ignore=tests/unit/test_aider_streaming_adapter.py -q --tb=short

test-changed:
	@files=$$(git diff --name-only HEAD | grep -E '\.py$$' || true); \
	if [ -z "$$files" ]; then echo "No changed .py files"; exit 0; fi; \
	pytest $$(echo $$files | tr ' ' '\n' | grep -E 'tests/' || echo tests/) --tb=short

smoke:
	bash scripts/cos-smoke.sh -v

audit:
	python3 scripts/aspirational-audit.py --dry-run
	python3 scripts/cos-build-self-knowledge.py

clean:
	find .cognitive-os/metrics -name "*.jsonl" -size +10M -exec tail -c 5M {} + 2>/dev/null || true
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true
