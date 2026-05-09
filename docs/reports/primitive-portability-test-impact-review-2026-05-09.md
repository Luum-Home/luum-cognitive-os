# Primitive Portability Test Impact Review — 2026-05-09

## Status

Drafted after landing ADR-256/ADR-258 implementation slices and the hardened
`/primitive-authoring` gate. This is an impact map, not a claim that every listed
lane has been executed in full for the current commit.

## Scope

This review covers the test blast radius for the portable primitive architecture:

- `manifests/primitive-contracts.yaml` as canonical primitive contract registry;
- `.cognitive-os/metrics/primitive-interventions.jsonl` and
  `.cognitive-os/metrics/codebase-itinerary.jsonl` evidence streams;
- generated `.ai/` consumer overlay and adapter manifests;
- `scripts/cos adapters`, `scripts/cos observe primitives`, and projection
  fidelity reports;
- `/primitive-authoring` as the gate for future primitive creation;
- service/headless and consumer-fleet implications.

Architecture invariant under test:

> COS canonical internal registry != consumer `.ai` overlay.

The canonical source remains COS internals (`skills/`, `rules/`, `hooks/`,
`scripts/`, `manifests/primitive-contracts.yaml`). `.ai/` is generated consumer
packaging unless a future ADR explicitly changes that migration plan.

## Repository test inventory

Current file-level inventory:

| Lane/directory | Test files | Default behavior |
|---|---:|---|
| `tests/unit/` | 515 | Parallel, excludes benchmark marker by default |
| `tests/contracts/` | 104 | Parallel |
| `tests/integration/` | 103 | Serial, optional, Docker subset separated |
| `tests/behavior/` | 159 | Serial |
| `tests/audit/` | 62 | Parallel |
| `tests/hooks/` | 14 | Serial |
| `tests/chaos/` | 41 | Serial |
| `tests/red_team/` | 35 | Parallel with capped workers |
| `tests/e2e/` | 3 | Serial, optional |
| `tests/security/` | 3 | Not lane-listed in `.cognitive-os/test-lanes.yaml` |
| `tests/system/` | 2 | Parallel |
| `tests/architecture/` | 1 | Parallel |
| `tests/benchmark/` | 1 | Optional/cost/time sensitive |
| `tests/perf/` | 1 | Not lane-listed in `.cognitive-os/test-lanes.yaml` |
| root `tests/test_*.py` | 2 | Not lane-listed directly |

Keyword scan for primitive/portable/adapter/harness/evidence/service surfaces
found 203 likely affected test files:

| Lane | Likely affected files |
|---|---:|
| `tests/unit/` | 80 |
| `tests/contracts/` | 45 |
| `tests/behavior/` | 30 |
| `tests/integration/` | 17 |
| `tests/audit/` | 15 |
| `tests/hooks/` | 14 |
| `tests/chaos/` | 1 |
| `tests/red_team/` | 1 |

## Impact matrix

### P0 — Must stay green for any primitive-portability change

These are the immediate safety net for ADR-256/ADR-258 work.

| Surface | Why affected | Tests/commands |
|---|---|---|
| Primitive contract registry | Canonical contract shape, fidelity labels, proof tests | `python3 -m pytest tests/contracts/test_primitive_contract_registry.py tests/contracts/test_primitive_projection_fidelity.py -q` |
| Generated `.ai` overlay | Detects stale generated rows, missing `portable_contract`, wrong overlay/canonical boundary | `scripts/cos-portable-ai-overlay --check && python3 -m pytest tests/contracts/test_portable_ai_overlay.py tests/contracts/test_portable_ai_completion.py -q` |
| Adapter UX | `cos adapters` list/install/verify and adapter manifests | `python3 -m pytest tests/contracts/test_consumer_adapter_ux.py -q` |
| Primitive authoring gate | Ensures new primitives use reuse, ownership, contract, overlay, adapter, evidence rules | `python3 -m pytest tests/contracts/test_primitive_authoring_gate.py -q` |
| Intervention ledger | Blocks/warns/advisories must write schema-safe runtime evidence | `python3 -m pytest tests/contracts/test_primitive_intervention_ledger.py -q` |
| Codebase itinerary | Read/Grep/Glob/LS itinerary must remain content-free | `python3 -m pytest tests/contracts/test_codebase_itinerary.py -q` |
| Trace joiner / observable self-use | Joins evidence streams and summarizes primitive interventions | `python3 -m pytest tests/unit/test_trace_joiner.py tests/contracts/test_observable_primitive_self_use.py -q` |
| OpenCode projection claims | Prevents claiming runtime enforcement before native smoke proof | `python3 -m pytest tests/contracts/test_opencode_native_adapter_design.py -q` |
| Due diligence / radar claims | Prevents losing standards/radar basis for `.ai`, AGENTS.md, SKILL.md, ACP/MCP/A2A | `python3 -m pytest tests/contracts/test_portable_ai_due_diligence_addendum.py tests/contracts/test_portable_primitive_radar_entries.py -q` |

Recommended P0 bundle:

```bash
scripts/cos-portable-ai-overlay --check && \
python3 -m pytest \
  tests/contracts/test_primitive_contract_registry.py \
  tests/contracts/test_primitive_projection_fidelity.py \
  tests/contracts/test_portable_ai_overlay.py \
  tests/contracts/test_portable_ai_completion.py \
  tests/contracts/test_consumer_adapter_ux.py \
  tests/contracts/test_primitive_authoring_gate.py \
  tests/contracts/test_primitive_intervention_ledger.py \
  tests/contracts/test_codebase_itinerary.py \
  tests/contracts/test_observable_primitive_self_use.py \
  tests/contracts/test_opencode_native_adapter_design.py \
  tests/contracts/test_portable_ai_due_diligence_addendum.py \
  tests/contracts/test_portable_primitive_radar_entries.py \
  tests/unit/test_trace_joiner.py \
  -q
```

### P1 — Required before moving from generated overlay to physical/canonical migration

Run these before any future ADR that physically moves primitives into `.ai/`,
changes generator semantics, changes adapter fidelity, or makes new enforcement
default-on.

| Surface | Risk | Tests/commands |
|---|---|---|
| All primitive lifecycle metadata | Generated overlay walks hooks/skills/rules/scripts/manifests; lifecycle drift can silently change hundreds of rows | `python3 -m pytest tests/contracts/test_primitive_lifecycle_manifest.py tests/unit/test_active_primitive_index.py tests/unit/test_primitive_usage_map.py tests/unit/test_primitive_row_audit.py -q` |
| Harness/projection coverage | Adapter claims must not exceed actual harness capability | `python3 -m pytest tests/contracts/test_primitive_harness_coverage_contract.py tests/contracts/test_primitive_harness_partials_contract.py tests/contracts/test_primitive_harness_partial_ratchets.py tests/behavior/test_harness_audit.py -q` |
| Hooks and lifecycle behavior | Evidence ledgers and adapters touch hook lifecycle assumptions | `python3 -m pytest tests/audit/test_hooks_contracts.py tests/behavior/test_hook_architecture.py tests/behavior/test_hook_triggers.py tests/hooks/ -q` |
| Skill/rule packaging | `.ai` overlay and primitive authoring depend on SKILL.md/rule contracts | `python3 -m pytest tests/audit/test_skills_contracts.py tests/audit/test_rules_enforcement.py tests/contracts/test_skill_router_invariant.py tests/contracts/test_rule_router_invariant.py -q` |
| Consumer projection | Consumer projects must not receive stale or overclaiming projection | `python3 -m pytest tests/behavior/test_consumer_project_projection.py tests/unit/test_consumer_fleet_audit.py tests/contracts/test_consumer_adapter_ux.py -q` |
| Service/headless mode | Primitive evidence must work outside IDE lifecycle where claimed | `python3 -m pytest tests/behavior/test_service_mode_readiness_gate.py tests/unit/test_service_mode_readiness_gate.py tests/integration/test_headless_service_drill.py -q` |
| Runtime/blocking safety | Blocking hooks must preserve bypasses, false-positive controls, metrics | `python3 -m pytest tests/unit/test_destructive_git_block.py tests/chaos/test_destructive_rm_blocker.py tests/unit/test_runtime_hook_reality.py -q` |
| CLI routing | New `scripts/cos` routes can collide with existing command dispatch | `python3 -m pytest tests/behavior/test_cos_team_cli.py tests/behavior/test_cos_agent_daemon_cli.py tests/behavior/test_cos_work_inventory.py -q` |

### P2 — Broad local confidence before merge/release

After P0/P1 pass, use the existing lane policy rather than manually assembling a
large command:

```bash
make test-laptop
```

This is the laptop-friendly broad lane: capped workers, no Docker, no cost, no
integration/e2e/chaos. It is the right confidence pass for multi-file primitive
changes after targeted suites pass.

### P3 — Explicit slow/stateful gates before release or canonical migration

Use these only when the change affects install, harness drivers, service mode,
provider/runtime behavior, session lifecycle, Docker/testcontainers, or public
release claims.

```bash
make test-laptop-integration
make test-ci-default
make test-release
```

Interpretation:

- `make test-laptop-integration`: serial non-Docker integration lane.
- `make test-ci-default`: broad non-Docker pre-merge confidence.
- `make test-release`: CI default + integration + Docker/e2e explicit.

## High-risk affected test clusters

### 1. Primitive registry and generated overlay

Representative tests:

- `tests/contracts/test_primitive_contract_registry.py`
- `tests/contracts/test_primitive_projection_fidelity.py`
- `tests/contracts/test_portable_ai_overlay.py`
- `tests/contracts/test_portable_ai_completion.py`
- `tests/contracts/test_primitive_authoring_gate.py`
- `tests/unit/test_primitive_row_audit.py`
- `tests/unit/test_primitive_usage_map.py`

Failure meaning: canonical registry shape, lifecycle harvesting, or generated
`.ai` rows have drifted.

### 2. Runtime evidence and observable self-use

Representative tests:

- `tests/contracts/test_primitive_intervention_ledger.py`
- `tests/contracts/test_codebase_itinerary.py`
- `tests/contracts/test_observable_primitive_self_use.py`
- `tests/unit/test_trace_joiner.py`
- `tests/behavior/test_concurrency_safety_ledgers.py`

Failure meaning: COS can no longer answer “what did the agent inspect, what
primitive intervened, and what effect did it have?” without leaking content.

### 3. Hooks, blocking behavior, bypasses, and metrics

Representative tests:

- `tests/audit/test_hooks_contracts.py`
- `tests/audit/test_hook_disable_env.py`
- `tests/audit/test_hook_latency_budget.py`
- `tests/hooks/`
- `tests/unit/test_destructive_git_block.py`
- `tests/chaos/test_destructive_rm_blocker.py`

Failure meaning: hook lifecycle, bypass semantics, latency, or destructive-action
protections have regressed.

### 4. Harness/IDE adapter fidelity

Representative tests:

- `tests/contracts/test_consumer_adapter_ux.py`
- `tests/contracts/test_opencode_native_adapter_design.py`
- `tests/contracts/test_primitive_harness_coverage_contract.py`
- `tests/integration/test_harness_adapter_dispatch.py`
- `tests/integration/test_codex_harness_adapter_dispatch.py`
- `tests/integration/test_harness_driver_parity.py`

Failure meaning: COS may be overclaiming enforcement in a harness/IDE or
projecting primitives inconsistently.

### 5. Consumer-fleet and install/update behavior

Representative tests:

- `tests/behavior/test_consumer_project_projection.py`
- `tests/unit/test_consumer_fleet_audit.py`
- `tests/integration/test_fresh_install_canary.py`
- `tests/integration/test_self_install.py` if present in the local branch/future lane
- `scripts/cos-consumer-fleet-audit --json`

Failure meaning: generated overlay or adapter behavior may affect downstream
projects differently than COS claims.

### 6. Service/headless mode

Representative tests:

- `tests/behavior/test_service_mode_readiness_gate.py`
- `tests/unit/test_service_mode_readiness_gate.py`
- `tests/integration/test_headless_service_drill.py`
- `tests/integration/test_service_health.py`
- `tests/contracts/test_service_control_plane_contracts.py`

Failure meaning: primitives are still IDE-bound despite service/headless claims,
or service control-plane boundaries are unsafe.

## Review method used

Commands used for this inventory:

```bash
find tests -type f \( -name 'test_*.py' -o -name '*_test.py' \)
sed -n '1,260p' .cognitive-os/test-lanes.yaml
sed -n '1,220p' .cognitive-os/test-resource-policy.yaml
rg -n "primitive|portable|adapter|harness|overlay|trace|ledger|itinerary|opencode|consumer|skill|hook|rule|cosd|service|projection" tests -S
```

## Immediate recommendation

For current ADR-256/ADR-258 work, keep this as the default merge validation
bundle until the architecture stabilizes:

```bash
scripts/cos-portable-ai-overlay --check && \
python3 -m pytest \
  tests/contracts/test_primitive_authoring_gate.py \
  tests/contracts/test_portable_ai_completion.py \
  tests/contracts/test_consumer_adapter_ux.py \
  tests/contracts/test_primitive_contract_registry.py \
  tests/contracts/test_primitive_projection_fidelity.py \
  tests/contracts/test_primitive_intervention_ledger.py \
  tests/contracts/test_codebase_itinerary.py \
  tests/contracts/test_observable_primitive_self_use.py \
  tests/unit/test_trace_joiner.py \
  -q
```

Before any canonical `.ai` migration ADR, upgrade the validation requirement to:

```bash
make test-laptop
make test-laptop-integration
```

and run Docker/e2e only if install/service claims change:

```bash
make test-release
```
