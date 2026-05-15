# Cognitive OS — test + dev targets
# All python invocations go through `uv run` so UV-managed deps
# (fastmcp, openai SDK, etc.) are visible. See docs/06-Daily/reports/next-session-handoff-2026-04-20.md.
#
# DEPRECATION NOTICE (ADR-072): The test-fast, test-unit, test-all, test-no-docker-shard-a,
# and test-no-docker-shard-b targets are deprecated in favour of `cos-test`.
# They will be removed in the next minor release.
# Canonical entry points:
#   cos-test focused                    — single-file iteration (<30s)
#   cos-test cluster --lane <name>      — validate one lane
#   cos-test broad                      — full pre-push sweep

.PHONY: help test-agentic-mastery test test-local-fast test-laptop test-laptop-direct test-laptop-integration test-local-wide-no-docker test-ci-default test-integration-no-docker test-release test-docker test-optional test-docker-explicit test-optional-cost test-fast test-unit test-integration test-e2e test-chaos test-all test-changed typecheck-pyrefly smoke audit clean ci-deps check-docs-convention test-no-docker test-no-docker-shard-a test-no-docker-shard-b test-skip-report cos-test install-test

PY := uv run python3
PYTEST := uv run pytest
COS_TEST_PYTHON ?= python3

# Build the cos-test binary on demand. All deprecated test-* targets depend on it.
cos-test:
	@cd cmd/cos-test && go build -o ../../cos-test .

help:
	@echo "Targets:"
	@echo "  test-agentic-mastery  Agentic mastery MVP: ACI, skill efficacy, runtime benchmark schema, adversarial suite, lethal trifecta."
	@echo "  test-local-fast   Official local quick lane: cos-test focused."
	@echo "  test-laptop       Laptop-friendly broad lane: capped workers, no Docker/cost/integration/chaos."
	@echo "  test-laptop-integration  Laptop-friendly explicit integration lane: serial + nice, still slow/stateful."
	@echo "  test-local-wide-no-docker  Official local broad lane without Docker/cost."
	@echo "  test-ci-default   Official CI/pre-merge default: broad non-Docker gate; do not run constantly on laptops."
	@echo "  test-release      Release gate: CI default + integration + Docker/e2e explicit."
	@echo "  test-integration-no-docker  Explicit slow integration lane without Docker."
	@echo "  test-docker       Explicit Docker/testcontainers lane."
	@echo "  test-optional     Explicit optional/cost-bearing lanes."
	@echo "  test-docker-explicit  [DEPRECATED → test-docker] Explicit Docker/testcontainers lane."
	@echo "  test-optional-cost    [DEPRECATED → test-optional] Explicit optional/cost-bearing lanes."
	@echo "  test-fast         [DEPRECATED → cos-test cluster --lane unit] Unit tests, parallel (-n auto). <30s."
	@echo "  test-unit         [DEPRECATED → cos-test cluster --lane unit] Unit tests serial."
	@echo "  test-integration  Integration tests serial (tmp state sensitive)."
	@echo "  test-e2e          E2E smoke + full e2e suite."
	@echo "  test-chaos        Chaos tests."
	@echo "  test-all          [DEPRECATED → cos-test broad] Full suite serial (slowest, most complete)."
	@echo "  test-no-docker    Sharded non-Docker lane (shard-a + shard-b sequential)."
	@echo "  test-no-docker-shard-a  [DEPRECATED → cos-test cluster --lane unit] Shard A: unit/ with xdist."
	@echo "  test-no-docker-shard-b  [DEPRECATED → cos-test cluster --lane behavior] Shard B: behavior/chaos/hooks/e2e/…"
	@echo "  test-skip-report  Full suite with -rs (prints every skip reason). On-demand only — noisy in CI."
	@echo "  test-changed      Only tests affected by git diff HEAD."
	@echo "  smoke             bash scripts/cos-smoke.sh — critical path e2e."
	@echo "  audit             Aspirational audit + self-knowledge refresh."
	@echo "  install-test      ADR-059 §Phase 2: clone + time end-to-end install; emits JSONL record."
	@echo "  clean             Prune metrics + caches (keeps last 1000 JSONL events)."
	@echo ""
	@echo "Canonical test entry (ADR-072):"
	@echo "  cos-test focused                   — single-file iteration"
	@echo "  cos-test cluster --lane <name>      — lane-scoped validation"
	@echo "  cos-test broad                      — full pre-push sweep"
	@echo ""
	@echo "All python commands run via 'uv run' — plain 'python3' or 'pytest' will miss UV-managed deps."

test-agentic-mastery:
	@echo "[test-agentic-mastery] Validating agentic mastery MVP slices." >&2
	@python3 -m pytest tests/unit/test_lethal_trifecta.py tests/contracts/test_lethal_trifecta_gate.py tests/unit/test_aci_observation.py tests/contracts/test_aci_observation_capture_hook.py tests/unit/test_skill_efficacy.py tests/unit/test_run_skill_efficacy_smoke.py tests/contracts/test_runtime_benchmark_schema.py tests/behavior/test_adversarial_generalization_manifest.py -q
	@python3 scripts/skill_efficacy_report.py >/dev/null
	@python3 scripts/run_skill_efficacy_smoke.py --reset >/dev/null
	@bash scripts/run-runtime-benchmark.sh --execute >/dev/null
	@bash scripts/run-adversarial-generalization.sh >/dev/null
	@python3 scripts/agentic_mastery_summary.py >/dev/null
	@echo "[test-agentic-mastery] Reports: .cognitive-os/reports/skill-efficacy-report.md, skill-efficacy-smoke-report.md, runtime-benchmark-leaderboard.md, adversarial-generalization-report.md, agentic-mastery-summary.md" >&2

test: test-fast

test-local-fast: cos-test
	@./cos-test focused

test-laptop: cos-test
	@echo "[test-laptop] Laptop-friendly broad validation in an isolated validation capsule." >&2
	@scripts/cos-validation-capsule.sh -- $(MAKE) test-laptop-direct

test-laptop-direct: cos-test
	@echo "[test-laptop-direct] Laptop-friendly broad validation: max 2 workers, no Docker/cost/integration/e2e/chaos." >&2
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane unit
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane audit
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane contract
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane architecture
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane system
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane behavior
	@COS_TEST_WORKERS_MAX=2 ./cos-test cluster --lane hooks

test-laptop-integration: cos-test
	@echo "[test-laptop-integration] Explicit SO integration validation via F1 stable shards. Override COS_INTEGRATION_SHARDS=4." >&2
	@i=0; shards="$${COS_INTEGRATION_SHARDS:-4}"; while [ "$$i" -lt "$$shards" ]; do \
		echo "[test-laptop-integration] shard $$i/$$shards" >&2; \
		nice -n 10 $(COS_TEST_PYTHON) scripts/cos-integration-shard-plan --shards "$$shards" --shard-index "$$i" --run || exit $$?; \
		i=$$((i + 1)); \
	done

test-laptop-integration-plan:
	@$(COS_TEST_PYTHON) scripts/cos-integration-shard-plan --shards "$${COS_INTEGRATION_SHARDS:-4}" --json

test-laptop-integration-shard:
	@nice -n 10 $(COS_TEST_PYTHON) scripts/cos-integration-shard-plan --shards "$${COS_INTEGRATION_SHARDS:-4}" --shard-index "$${SHARD_INDEX:?set SHARD_INDEX=0..N-1}" --run

test-local-wide-no-docker: cos-test
	@./cos-test broad --no-docker

test-ci-default: cos-test
	@./cos-test broad --no-docker --ci

test-release: test-ci-default test-integration-no-docker test-docker

test-integration-no-docker: cos-test
	@./cos-test cluster --lane integration

test-docker: cos-test
	@COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane integration-docker
	@COS_ALLOW_DOCKER_TESTS=1 ./cos-test cluster --lane e2e

test-optional: cos-test
	@COS_ALLOW_COST_BEARING_TESTS=1 ./cos-test cluster --lane arena
	@COS_ALLOW_COST_BEARING_TESTS=1 ./cos-test cluster --lane benchmark
	@COS_ALLOW_COST_BEARING_TESTS=1 ./cos-test cluster --lane quality

test-docker-explicit: test-docker

test-optional-cost: test-optional

test-fast: cos-test
	@echo "[deprecated] 'make test-fast' will be removed in next minor; use 'cos-test focused' or 'cos-test cluster --lane unit'" >&2
	@./cos-test cluster --lane unit

test-unit: cos-test
	@echo "[deprecated] 'make test-unit' will be removed in next minor; use 'cos-test cluster --lane unit'" >&2
	@./cos-test cluster --lane unit

test-integration:
	$(PYTEST) tests/integration/ -m "not slow and not docker" --tb=short

test-e2e:
	bash scripts/cos-smoke.sh -v
	$(PYTEST) tests/e2e/ -v

test-chaos:
	$(PYTEST) tests/chaos/ -v

test-all: cos-test
	@echo "[deprecated] 'make test-all' will be removed in next minor; use 'cos-test broad'" >&2
	@./cos-test broad

test-changed:
	@files=$$(git diff --name-only HEAD | grep -E '\.py$$' || true); \
	if [ -z "$$files" ]; then echo "No changed .py files"; exit 0; fi; \
	$(PYTEST) $$(echo $$files | tr ' ' '\n' | grep -E 'tests/' || echo tests/) --tb=short

typecheck-pyrefly:
	@bash scripts/cos-pyrefly-pilot

smoke:
	bash scripts/cos-smoke.sh -v

audit:
	$(PY) scripts/aspirational_audit.py --dry-run
	$(PY) scripts/cos_build_self_knowledge.py

# ADR-059 §Phase 2 — measure end-to-end install time and emit JSONL record.
# Pass PROFILE= to override (default --standard).
# e.g. make install-test PROFILE=--minimal
install-test:
	@bash scripts/install-timing-test.sh --profile $${PROFILE:---standard}

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
# [DEPRECATED] These shard targets are superseded by cos-test cluster (ADR-072).
test-no-docker-shard-a: cos-test
	@echo "[deprecated] 'make test-no-docker-shard-a' will be removed in next minor; use 'cos-test cluster --lane unit'" >&2
	@./cos-test cluster --lane unit

test-no-docker-shard-b: cos-test
	@echo "[deprecated] 'make test-no-docker-shard-b' will be removed in next minor; use 'cos-test cluster --lane <name>' per lane (or 'cos-test broad' for full sweep)" >&2
	@./cos-test cluster --lane audit
	@./cos-test cluster --lane contract
	@./cos-test cluster --lane architecture
	@./cos-test cluster --lane system
	@./cos-test cluster --lane behavior
	@./cos-test cluster --lane hooks
	@./cos-test cluster --lane e2e
	@./cos-test cluster --lane chaos

test-no-docker: test-no-docker-shard-a test-no-docker-shard-b

# On-demand skip-reason dump. The shard targets intentionally omit -rs to keep
# CI output clean; use this target locally to inspect which tests skip and why.
# No cos-test equivalent for -rs verbose mode — kept as direct pytest invocation.
test-skip-report:
	$(PYTEST) tests/unit/ tests/behavior/ tests/chaos/ tests/hooks/ tests/e2e/ tests/audit/ tests/contracts/ tests/architecture/ tests/system/ -m "not docker" --timeout=60 --tb=short -rs -q

check-docs-convention:
	@PROJECT_DIR="$${PROJECT_DIR:-$$(pwd)}"; \
	if [ "$${STRICT:-0}" = "1" ]; then \
		bash hooks/project-docs-convention.sh --project-dir "$$PROJECT_DIR" --strict; \
	else \
		bash hooks/project-docs-convention.sh --project-dir "$$PROJECT_DIR"; \
	fi
