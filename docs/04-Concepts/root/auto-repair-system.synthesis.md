---
type: concept-synthesis
source: docs/04-Concepts/root/auto-repair-system.md
provenance: "Enable Cognitive OS to autonomously detect, classify, and repair errors across all system layers instead of repeating the same fix from scratch every time."
---

## What it is

A MAPE-K (Monitor-Analyze-Plan-Execute-Knowledge) loop that detects errors, looks up or generates fixes, applies them in an isolated worktree, verifies, and records the outcome so repeat errors become near-free.

## Key mechanics

**MAPE-K flow**: Monitor (`error-learning.sh`) → Analyze+Plan (`auto-repair-dispatcher.sh`: classify error, registry lookup, decide action) → Execute (`execute-repair.sh`, worktree-isolated, deterministic or async LLM path) → Verify (build+test+lint) → success→register in registry / failure→circuit breaker (2 strikes→OPEN) → Knowledge (Engram + JSONL).

**Shared bash libs** (`hooks/_lib/`): `safe-jsonl.sh` (flock-protected writes + heartbeat trap), `circuit-breaker.sh` (per error_type:service, 2 strikes, 1h cooldown, 10/hr global cap), `remediation.sh` (registry O(1) lookup + GC), `execute-repair.sh` (worktree isolation).

**Python libs** (`lib/`): `file_mutation_queue.py` (per-file thread lock serializing concurrent writes, ported from Pi coding-agent, symlink-aware), `reinvention_guard.py` (checks `adoption-registry.yaml` before creating new primitives), `learning_pipeline.py` (chains prompt_classifier→skill_archive→consequence_engine→error_classifier, writes `error-skill-correlations.jsonl`), `memory_scanner.py` (12-pattern content security scanner gating all `mem_save`, ported from Hermes).

**Remediation registry** (`metrics/remediation-registry.jsonl` + O(1) index `metrics/remediation-index.json`): entries carry `fingerprint` (md5 of first 200 chars), `error_type` (BUILD|TEST|LINT|RUNTIME|INFRA), `fix_type`, `success_rate`, `times_applied/failed`, `confidence`. Known fix = 0 tokens, deterministic, instant; unknown fix = LLM repair, $0.01-2.00, async worktree-isolated.

**Circuit breaker**: max consecutive failures 2 (`COGNITIVE_OS_CB_MAX_FAILURES`), cooldown 1h (`COGNITIVE_OS_CB_COOLDOWN`), global hourly cap 10 (`COGNITIVE_OS_CB_HOURLY_CAP`). States: CLOSED→OPEN→HALF-OPEN.

**Phase autonomy**: reconstruction/stabilization allow code+LLM+infra repair; production/maintenance restrict to infra repair only (restart, cache).

**Never auto-repaired**: DB migrations, auth/authz changes, payment/billing code, `.env` files, Docker compose config, git history (rebase/force-push), security-sensitive files, third-party API integration changes.

**License-safe infra stack**: Valkey 8 (BSD-3) replaces Redis (AGPL); SeaweedFS (Apache-2.0) replaces MinIO (AGPL).

**Benchmark**: 1st fix new error: vanilla 85s vs COS 109s (hook overhead ~24s, COS slower first time). 2nd fix same error: vanilla 85s (no memory) vs COS ~10s (registry hit, $0). 10th fix: vanilla 850s/~$5 vs COS ~10s. At N=10 identical errors, COS is ~85x faster, ~50x cheaper. Cost model: vanilla = N × avg_fix_time × token_cost (linear); COS = first_fix_cost + (N-1) × registry_lookup_cost (≈constant after learning).

## Relations & where used

Rules: `auto-repair` (phase gates, circuit breaker, never-auto-repair list), `metrics-calibration`. Skills: `/repair-status`, `/metrics-calibrator`, `/conversation-memory`, `/tool-discovery`. Config block `auto_repair` in `cognitive-os.yaml` (circuit_breaker, phase_gates, remediation.confidence_threshold=0.8, gc_after_days=30).

## Status / caveats

The benchmark table is explicitly noted as biased toward "first time, no history" — the honest tradeoff is COS pays hook overhead upfront but wins on total cost of ownership after repeat errors accumulate in the registry.
