# Session Handoff — 2026-05-04

> ADR-143/144 closure landed; remaining ADR implementation backlog audited against repo evidence.

## Headline

This session closed the immediate May 3 validation-drift problem by landing
ADR-143 and ADR-144, then audited the remaining ADR backlog with a bias toward
repo evidence over ADR prose. The important conclusion: **closure discipline and
hook-projected rule enforcement are now implemented; the next execution wave is
cloud-flow runway first, then stash/concurrency hardening and doc reconciliation.**

## What landed in main

| SHA | Subject | Notes |
|---|---|---|
| `1d454bbe` | `feat: add closure discipline gate` | ADR-143, `cos_closure_discipline_audit.py`, quick-CI/capsule integration, stale validator fixes. |
| `cb37eef6` | `fix: enforce hook-projected rule exclusions` | ADR-144, `skill-router-bash-gate.sh`, projection-contract audit and behavior tests. |
| `d7a4c6be` | `test: harden audit allowlists for preserved worktrees` | Follow-up for preserved worktree credential-reference audit and generated skill catalog drift. |
| `325797ab` | `feat(skill): add /deps-update skill (audience: os)` | Aligns `/deps-update` with ADR-144 bash-gate redirect and updates full/compact skill catalogs. |

All four commits were pushed to `origin/main`. Direct pushes from `main` were
blocked by `direct-main-guard`; operator-requested bypass was used with explicit
reason strings.

## Validation evidence captured

### ADR-143 / ADR-144 closure

```bash
scripts/cos-closure-discipline-audit --fail-on-findings --json
# status: pass, finding_count: 0

bash scripts/cos-ci-local.sh quick
# passed: 15, failed: 0, skipped: 1

python3 -m pytest tests/audit/test_hook_enforced_exclusions.py \
  tests/behavior/test_skill_router_bash_gate.py -q
# 6 passed

python3 -m pytest tests/audit/test_skills_contracts.py -k deps-update -q
# 4 passed
```

### Backlog audit probes

```bash
bash scripts/_lib/settings-driver-claude-code.sh --check
# OK: .claude/settings.json is in sync with canonical harness.hooks

bash scripts/_lib/settings-driver-codex.sh --check
# OK: .codex/hooks.json is in sync with canonical harness.hooks

python3 -m pytest tests/integration/test_harness_agnostic_skill_run.py \
  tests/integration/test_project_settings_generation.py -q --tb=short
# 32 passed

python3 -m pytest tests/integration/test_cos_agent_spawn.py \
  tests/integration/test_portability_demo.py -q --tb=short
# 12 passed

python3 -m pytest tests/red_team/portability/test_concurrent-write-guard.py \
  tests/red_team/portability/test_concurrent-write-guard-codex-proxy.py \
  tests/red_team/portability/test_claim-validator.py \
  tests/red_team/portability/test_symlink-mutation-guard.py \
  tests/unit/test_concurrent_agent_safety_status.py -q --tb=short
# 29 passed

python3 -m pytest tests/unit/test_cos_task_claims.py \
  tests/unit/test_merge_queue.py tests/unit/test_session_lifecycle.py -q --tb=short
# 39 passed
```

## ADR reality matrix

| ADR | Current reality | Evidence | Next action |
|---|---|---|---|
| ADR-137 Operational Trajectory | Partial. Direction is accepted; runtime evidence still missing. | `manifests/federation-triggers.yaml` exists, but no `framing_a_flows_active` counter and no first flow exercising Framing A. | Add flow counter and require framing-exercise statement in first flow. |
| ADR-138 Flow Contract Schema | Not implemented yet. | Missing `manifests/flow-contract-schema.yaml`, `scripts/cos-flow-register.sh`, first flow contract. ADR says manifest can land lazily with first flow. | Implement schema + register audit first. |
| ADR-139 Account-Agnostic Runtime | Policy only; enforcement pending. | `credential_source`, `billing_identity`, `provider_capabilities` are ADR fields but no flow register gate exists. | Enforce through ADR-138 register audit. |
| ADR-140 Cross-OS Container Worker | Not implemented. | Missing `docker/cos-worker/docker-compose.yml`. | Add worker Compose stack and container smoke test. |
| ADR-141 Engram Cloud Replication | Not implemented in ADR shape. | Missing `scripts/cos-engram-cloud-enroll`; no `ENGRAM_CLOUD_AUTOSYNC` wrapper evidence. | Add enroll wrapper, local-only fallback, sync audit row. |
| ADR-142 Compliance/Audit/Air-gap | Policy only; implementation pending. | Missing `scripts/cos-audit-archive`, `docs/architecture/gdpr-erasure-procedure.md`, flow schema fields. | Add audit archive and GDPR doc after schema exists. |
| ADR-116 Multi-Session Coordination | Partially implemented. | Task ledger, merge queue, session lifecycle, coordination status, work inventory, content-hash dedupe, and work identity exist; 39 targeted tests passed. Names differ from ADR (`work_identity.py` vs `work_fingerprint.py`). | Reconcile ADR/docs to actual names and close remaining primitives. |
| ADR-117 Stash Reversibility | Incomplete, as ADR says. | R1 exists; missing `lib/stash_ops.py` and `hooks/_lib/stash_lock.sh`; budget/lock/audit not universally enforced. | Implement R2-R4 and add stash-operation contract tests. |
| ADR-106 Multi-Session Safety | Partial. | Stash alarm, plan claim validator, orchestrator gate, claim verifiers exist. `scripts/plan-lock.sh` and explicit provenance trailer guard are missing. | Decide/fix claim-gate scope regression; add plan lock/provenance surfaces or update ADR. |
| ADR-108 Concurrent-Agent Safety Layer | Slices exist; umbrella layer incomplete. | Concurrent status composer and Codex/Claude projection tests pass; no unified Agent Work Ledger / Resource Lease runtime. | Promote slices into explicit composer/ledger contract. |
| ADR-111 Core/Consumer Boundary | Mostly implemented; docs drift. | ADR says implemented; projection tests pass. `docs/business/master-plan-checklist.md` still has ADR-111 checkbox open. | Reconcile master-plan checkbox with evidence. |
| ADR-123 Operational Stability | Early slices only. | `scripts/cos-status.sh` and `tests/behavior/test_cos_status.py` exist/pass; maturity/profile/repair/status phases remain unchecked in plan. | Continue phase plan: friction report → guard maturity → adaptive profiles → repair CLI. |
| ADR-132 Solo-Swarm vs Multi-Maintainer Fork | Exploration only. | ADR explicitly has no implementation acceptance criteria. | No technical implementation until strategic trigger fires. |
| ADR-064 Harness-Agnostic COS | More implemented than stale docs say. | `bin/cos-skill`, `bin/cos-agent`, Codex/bare adapters, settings drivers, demo script exist; targeted tests passed. | Reconcile stale docs and add/rename final harness parity contract if needed. |

## Concrete next execution order

### Step 1 — Close the flow substrate (ADR-138 first)

Deliverables:

- `manifests/flow-contract-schema.yaml`
- `scripts/cos-flow-register.sh`
- `tests/audit/test_flow_contract_schema.py` or equivalent
- ADR/docs update that clarifies the lazy-manifest rule is now materialized

Acceptance criteria:

```bash
python3 -m pytest tests/audit/test_flow_contract_schema.py -q
scripts/cos-flow-register.sh --check --contract path/to/valid/flow_contract.yaml
scripts/cos-flow-register.sh --check --contract path/to/invalid/flow_contract.yaml
# invalid contract exits non-zero with missing/invalid field names
```

### Step 2 — Register first lab flow

Deliverables:

- `skills/vuln-remediation-flow/SKILL.md`
- `skills/vuln-remediation-flow/flow_contract.yaml`
- `docs/architecture/vuln-remediation-flow.md`
- `manifests/federation-triggers.yaml` gains `framing_a_flows_active` or an equivalent counter

Acceptance criteria:

```bash
scripts/cos-flow-register.sh --check --contract skills/vuln-remediation-flow/flow_contract.yaml
python3 -m pytest tests/audit/test_flow_contract_schema.py -q
```

### Step 3 — Add cloud premises enforcement

Deliverables:

- ADR-139 fields enforced by flow register gate
- `docker/cos-worker/docker-compose.yml`
- `scripts/cos-engram-cloud-enroll`
- `scripts/cos-audit-archive`
- `docs/architecture/gdpr-erasure-procedure.md`

Acceptance criteria:

```bash
python3 -m pytest tests/audit/test_flow_contract_schema.py -q
python3 -m pytest tests/behavior/test_cos_audit_archive.py -q
bash scripts/cos-engram-cloud-enroll --help
```

Container smoke can be manual if Docker is unavailable locally, but the manual
path must be documented before claiming ADR-140 closed.

### Step 4 — Fix ADR-106 claim-gate ambiguity

Finding:

`tests/contracts/test_orchestrator_claim_gate.py::test_commit_message_archive_claim_fails_when_source_present`
currently fails because `orchestrator_claim_gate.py` scopes commit-message
verification to `RESULT:`, `STATUS:`, or explicit `done ...` lines. A plain
commit message `archived hooks/foo.sh` is ignored. This was introduced to reduce
ADR-133 false positives, but it leaves an old contract test stale or exposes a
real enforcement gap.

Decision needed:

- Option A: Keep scoped semantics and update the test to use `STATUS: archived hooks/foo.sh`.
- Option B: Re-block plain high-stakes commit subjects when they name concrete paths.

Do not silently choose by accident; this is a policy tradeoff between false
positives and claim safety.

### Step 5 — Close ADR-117 R2-R4

Deliverables:

- `lib/stash_ops.py`
- `hooks/_lib/stash_lock.sh`
- stash budget warning/enforcement path
- audit rows in `.cognitive-os/metrics/stash-ops.jsonl`
- contract tests for no anonymous stash, no `git stash pop`, apply-by-name, lock, budget

### Step 6 — Reconcile docs drift

Targets:

- ADR-064 implementation plan and harness transparency status: mark existing
  `cos-skill`, `cos-agent`, Codex/bare adapters, settings drivers as real.
- Master plan ADR-111 checkbox: either mark done with evidence or rewrite to
  name the actual remaining gap.
- ADR-116: align `work_identity.py` / `pre-commit-content-hash-dedupe.sh` names
  with ADR terminology.

## Known open risk

The cloud-flow runway should not be implemented by adding more default-visible
runtime surface. ADR-133 still applies: first flow stays `lab`, produces
propose-only output, and cannot promote to `core`/`team` until evidence exists.

## How to pick up next

```bash
# Verify clean state
git status --short

# Re-run current high-signal checks
bash scripts/_lib/settings-driver-claude-code.sh --check
bash scripts/_lib/settings-driver-codex.sh --check
scripts/cos-closure-discipline-audit --fail-on-findings --json

# Start Step 1
$EDITOR docs/adrs/ADR-138-flow-contract-schema.md
$EDITOR manifests/flow-contract-schema.yaml
$EDITOR scripts/cos-flow-register.sh
```

## 2026-05-04 Codex continuation

The ADR-137+ review was preserved as
[`docs/reports/adr-137-plus-implementation-review-2026-05-04.md`](reports/adr-137-plus-implementation-review-2026-05-04.md)
and linked from `docs/README.md` and
`docs/business/master-plan-checklist.md`.

The short implementation classification remains:

| ADR | Saved state |
|---|---|
| ADR-137 | Partial / accepted trajectory. Needs first Framing-A flow evidence. |
| ADR-138 | Next implementation target. Needs schema manifest, register script, tests, and first lab contract. |
| ADR-139 | Flow enforcement pending on ADR-138 fields. |
| ADR-140 | Not implemented; needs `docker/cos-worker/docker-compose.yml`. |
| ADR-141 | Not implemented; requires upstream Engram Cloud pinning before wrapper work. |
| ADR-142 | Not implemented; requires audit-row inventory, archive helper, and GDPR procedure. |
| ADR-143 | Implemented; targeted validation passed. |
| ADR-144 | Implemented; targeted validation passed. |

Current implementation order agreed in-session:

1. Materialize ADR-138 first.
2. Register the first lab `vuln-remediation-flow` contract.
3. Enforce ADR-139/141/142 fields through the flow register gate.
4. Add ADR-140 container worker surface after the contract can validate it.
5. Only mark an ADR implemented after executable or documented evidence exists.
