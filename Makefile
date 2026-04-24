# Cognitive OS — test + dev targets
# All python invocations go through `uv run` so UV-managed deps
# (fastmcp, openai SDK, etc.) are visible. See docs/reports/next-session-handoff-2026-04-20.md.

.PHONY: help test test-fast test-unit test-integration test-e2e test-chaos test-all test-changed smoke audit clean ci-deps check-docs-convention test-no-docker test-no-docker-shard-a test-no-docker-shard-b test-skip-report

PY := uv run python3
PYTEST := uv run pytest

help:
	@echo "Targets:"
	@echo "  ci-deps           Install optional CI deps (flock + Paperclip stub) to unblock skipped tests."
	@echo "  test-fast         Unit tests, paralelo (-n auto). <30s."
	@echo "  test-unit         Unit tests serial (useful for debugging xdist conflicts)."
	@echo "  test-integration  Integration tests serial (tmp state sensitive)."
	@echo "  test-e2e          E2E smoke + full e2e suite."
	@echo "  test-chaos        Chaos tests."
	@echo "  test-all          Full suite serial (slowest, most complete)."
	@echo "  test-no-docker    Sharded non-Docker lane (shard-a + shard-b sequential)."
	@echo "  test-no-docker-shard-a  Shard A: tests/unit/ with xdist (~114s)."
	@echo "  test-no-docker-shard-b  Shard B: behavior/chaos/hooks/e2e/audit/contracts/architecture/system serial (~350s)."
	@echo "  test-skip-report  Full suite with -rs (prints every skip reason). On-demand only — noisy in CI."
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
	$(PYTEST) tests/ -q --tb=short

test-changed:
	@files=$$(git diff --name-only HEAD | grep -E '\.py$$' || true); \
	if [ -z "$$files" ]; then echo "No changed .py files"; exit 0; fi; \
	$(PYTEST) $$(echo $$files | tr ' ' '\n' | grep -E 'tests/' || echo tests/) --tb=short

smoke:
	bash scripts/cos-smoke.sh -v

audit:
	$(PY) scripts/aspirational_audit.py --dry-run
	$(PY) scripts/cos_build_self_knowledge.py

ci-deps:
	@bash scripts/ci-setup.sh

clean:
	find .cognitive-os/metrics -name "*.jsonl" -size +10M -exec tail -c 5M {} + 2>/dev/null || true
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true

# ADR-054/055 — check an adopting project follows the 10-category docs convention.
# Override PROJECT_DIR to target an external project; defaults to the SO repo.
# Soft-warn by default; pass STRICT=1 to fail on missing categories.
# Non-Docker lane — sharded to fit under 900s CI timeout.
# Measured 2026-04-24: shard-a ~114s (xdist), shard-b ~350s (serial). Combined <500s.
# Run shards in parallel on CI (2 jobs) for wall-clock ~350s; serial locally.
test-no-docker-shard-a:
	$(PYTEST) tests/unit/ -n auto --timeout=60 --tb=short -q

test-no-docker-shard-b:
	$(PYTEST) tests/behavior/ tests/chaos/ tests/hooks/ tests/e2e/ tests/audit/ tests/contracts/ tests/architecture/ tests/system/ -m "not docker" --timeout=60 --tb=short -q

test-no-docker: test-no-docker-shard-a test-no-docker-shard-b

# On-demand skip-reason dump. The shard targets intentionally omit -rs to keep
# CI output clean; use this target locally to inspect which tests skip and why.
test-skip-report:
	$(PYTEST) tests/unit/ tests/behavior/ tests/chaos/ tests/hooks/ tests/e2e/ tests/audit/ tests/contracts/ tests/architecture/ tests/system/ -m "not docker" --timeout=60 --tb=short -rs -q

check-docs-convention:
	@PROJECT_DIR="$${PROJECT_DIR:-$$(pwd)}"; \
	if [ "$${STRICT:-0}" = "1" ]; then \
		bash hooks/project-docs-convention.sh --project-dir "$$PROJECT_DIR" --strict; \
	else \
		bash hooks/project-docs-convention.sh --project-dir "$$PROJECT_DIR"; \
	fi
