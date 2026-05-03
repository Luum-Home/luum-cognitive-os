# Integrity and De-Theater Sprint

## Goal

Stop adding new agentic primitives until Cognitive OS can distinguish proven
runtime safety from advisory/theater layers and until readiness reflects the real
projected runtime surface.

This sprint turns the latest DX assessment into executable gates. The target is
not to make the full maintainer runtime look small; the target is to make the
system honest when it is not small.

## P0 — Integrity gates

### 1. Active-index runtime coverage

Problem: ADR-127 currently indexes `manifests/primitive-lifecycle.yaml`, which is
a four-entry seed manifest, while the Claude projection registers roughly 120
hook entries.

Acceptance:

- `cos-active-primitive-index --json` reports projected hook count, unique
  projected hook count, lifecycle-covered hook count, missing projected hooks,
  and coverage status.
- `cos architecture readiness` fails when projected hooks are not represented by
  lifecycle metadata or an explicit bounded allowlist.
- A green readiness report can no longer hide a 4/120 lifecycle coverage gap.

### 2. Engram persistence integrity

Problem: Engram's value proposition depends on topic-key upsert, meaningful
ranking, and visible failure modes. The DX assessment found duplicate exports,
missing score fields, and silent reinforcement failure when the daemon is down.

Acceptance:

- Internal `engram_client.save_observation()` attempts wrapper-level upsert for
  exact `(project, topic_key)` matches when a topic key is supplied.
- Lifecycle ranking uses rank-derived fallback scores when Engram does not return
  numeric `score` fields; it does not collapse every base score to `1.0`.
- Reinforcement failure due to daemon unavailability writes a visible
  `engram-daemon-down.jsonl` metric.

### 3. Product-claim integrity

Problem: README/product-facing docs must not reference missing hooks or stale
model-branded readiness concepts.

Acceptance:

- Readiness checks README hook/script claims and fails if a backticked `*.sh`
  claim does not exist.
- Readiness scans product-facing docs for stale model-branded readiness names
  such as legacy model-branded readiness command names, reviewer-critique labels, and
  direct model IDs in product claims.
- Product docs describe advisory checks as advisory, not blocking.

## P1 — De-theater labeling

### Trust score and blast radius maturity

Problem: advisory checks are useful, but they become theater if product docs imply
that they block when they only log or add context.

Acceptance:

- `manifests/governance-maturity.yaml` labels trust score, blast radius, and
  stochastic review spawning as `advisory`/`observe`, not `blocking`.
- `cos architecture readiness` reports the maturity labels for those checks.
- A future change that claims these primitives are blocking must add tests proving
  blocking behavior.

## P2 — Follow-up backlog

Not in this sprint:

- ~~Full ADR-126 lifecycle metadata for every hook.~~ Done for the current `.claude/settings.json` projection: 116/116 runtime hooks covered.
- True consumer `core` projection with <=12 hooks. The maintainer repo still projects a larger surface and readiness warns honestly.
- Historical report cleanup for legacy SDD topic-key mentions; runtime docs now use `planning/{change-name}/...` and legacy fallbacks remain documented in `rules/engram-organization.md`.
- Full cost/savings dashboard.

Those remain the next sprint after readiness stops producing false confidence.

## Validation

```bash
python3 -m pytest tests/unit/test_active_primitive_index.py tests/unit/test_cos_architecture_readiness.py tests/unit/test_engram_client.py tests/unit/test_engram_lifecycle.py -q
python3 -m py_compile scripts/active_primitive_index.py scripts/cos_architecture_readiness.py lib/engram_client.py lib/engram_lifecycle.py
scripts/cos-architecture-readiness --json
python3 -m pytest tests/contracts/test_primitive_runtime_reality.py tests/contracts/test_primitive_lifecycle_manifest.py -q
```
