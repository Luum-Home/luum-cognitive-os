# Cognitive OS vs Vanilla IDE Agents — Senior DX Review

## Status

Current evidence review — 2026-05-03. This document consolidates read-only
senior/Solutions Architect reviews plus the operator's concern that Cognitive OS
must be valuable beyond the primitives already provided by Claude Code, Codex,
Cursor, and similar IDE-agent runtimes.

## Source reports

This review consolidates the current two-agent read-only assessment plus the frozen raw snapshot in `docs/06-Daily/reports/dx-assessment-2026-05-02.md`. The raw report is intentionally preserved as evidence; this document is the product/DX synthesis.

## Executive verdict

Cognitive OS is not a better default for every coding-agent user. Vanilla IDE
agents win for low-risk, single-session feature work because they have almost no
setup cost and very little runtime ceremony.

Cognitive OS is justified when the risk model changes from "one developer asking
one agent to edit code" to "multiple agents, sessions, IDEs, models, branches,
and unattended workers touching real repositories." In that setting, the value is
not autocomplete quality; it is operational safety: evidence-backed claims,
protected landing, WIP preservation, cross-session coordination, memory, and
portable harness boundaries.

The product implication is strict:

- sell and default to a small `core` guardrail surface;
- keep team/maintainer/cloud controls opt-in by persona;
- keep meta-governance/lab systems invisible unless explicitly requested;
- make readiness fail or warn when the documented active surface undercounts the
  real projected runtime surface.

## Persona verdicts

| Persona | DX verdict | Recommended surface |
|---|---|---|
| Solo dev, one IDE/session, small repo | Vanilla Claude Code/Codex/Cursor usually wins. COS is too heavy unless reduced to a tiny safety pack. | `core` only, no lab, no dashboards, no broad SDD by default. |
| Solo maintainer swarm | Strong fit. One human can still create team-scale concurrency risk when running multiple IDEs, sessions, and agents. | `maintainer` with branch leases, claims, WIP recovery, memory, and protected publication. |
| Team using agents on shared repos | Promising if packaging is disciplined. Teams will reject 100+ visible rules/hooks, but value claim verification and protected landing. | `team` with runtime-safety and coordination; delivery structure by task complexity. |
| Cloud/headless agents | Strategically strong but must become boring infrastructure. Safe-mode, branch leases, protected publication, and persistent evidence matter. | strict/headless profile with fail-closed admission and single-writer publication. |
| Product/customer first contact | Wedge is real, but the repo currently feels like a framework. Lead with proof paths, not the full OS vocabulary. | five-minute core proof path. |

## What COS offers that vanilla does not

### 1. Cross-session and multi-agent safety

Vanilla IDE agents do not provide a project-level cross-session claim ledger,
branch writer lease, or file-write coordination contract by default.

Evidence anchors:

- `hooks/concurrent-write-guard.sh`
- `hooks/concurrent-write-guard-codex-proxy.sh`
- `scripts/cos_task_claims.py`
- `scripts/cos_branch_lease.py`
- `tests/unit/test_concurrent_write_guard_behavior.py`
- `tests/unit/test_multi_agent_coordination_primitives.py`

### 2. Evidence-backed claim verification

Prompting an agent to run tests is not the same as gating completion claims on
verifiable evidence. Claim verification is one of the clearest product wedges.

Evidence anchors:

- `hooks/orchestrator-claim-gate.sh`
- `hooks/plan-claim-validator.sh`
- `scripts/orchestrator_claim_gate.py`
- `scripts/verify_plan_claims.py`
- `docs/04-Concepts/architecture/claim-verification-matrix.md`
- `tests/contracts/test_orchestrator_claim_gate.py`

### 3. Local protected landing before remote branch protection

Remote branch protection is necessary but late. COS can block dangerous local
agent actions before they become commits or pushes.

Evidence anchors:

- `hooks/direct-main-guard.sh`
- `docs/04-Concepts/architecture/direct-main-policy.md`
- `docs/04-Concepts/architecture/protected-landing-contract.md`
- `tests/unit/test_direct_main_guard.py`

### 4. WIP preservation and recovery

Git stash and IDE local history exist, but agent-aware snapshot/reapply flows are
not standard vanilla behavior. This is valuable only if symmetric cleanup is
proved and default triggering is risk-based.

Evidence anchors:

- `hooks/pre-agent-snapshot.sh`
- `hooks/post-agent-snapshot-restore.sh`
- `hooks/session-start-stash-reapply.sh`
- `lib/snapshot_manager.py`
- `tests/integration/test_post_agent_snapshot_restore.py`
- `tests/integration/test_stash_reapply.py`

### 5. Harness/provider normalization

Vanilla tools expose their own events and settings. COS can become valuable by
normalizing capability contracts across Claude Code, Codex, Cursor, Windsurf, and
CLI workers while being honest about degraded paths.

Evidence anchors:

- `pkg/hook/context.go`
- `internal/provider/`
- `manifests/harness-driver-capabilities.yaml`
- `docs/04-Concepts/architecture/harness-driver-parity.md`

## Current DX costs and risks

### Surface-area shock

Current local counts are maintainer-scale, not product-core scale:

| Surface | Current count |
|---|---:|
| `hooks/*.sh` | 186 |
| `.claude/settings.json` registered hook entries | 120 |
| unique registered hook commands | 118 |
| `skills/*/SKILL.md` | 159 |
| `rules/` files | 112 |
| `scripts/` files | 240 |
| `docs/` files | 544 |
| lifecycle manifest primitives | 4 |

A new user should not have to understand this surface to get value.

### Active-index undercount risk

ADR-127's active primitive index is directionally correct, but today it reads
`manifests/primitive-lifecycle.yaml`, which currently contains only four
primitives. That means `cos architecture readiness` can pass while the active
runtime still projects 120 Claude hook entries.

This is the next load-bearing gap. Readiness must report manifest coverage over
the projected runtime surface; otherwise it can produce false confidence.

### Hook latency is acceptable but not invisible

The system has latency tests and reports, but users experience overhead on tight
loops. Reducing the count of active hooks helps, but the per-tool-call budget must
also be measured by profile.

Required DX metric: p50/p95 hook-chain latency for `core`, `team`, and
`maintainer` profiles.

### Upstream overlap

Secret scanning, destructive command warnings, test execution, and formatting
checks overlap with GitHub, pre-commit, IDE tasks, and shell policy. COS should
frame these as local agent preflight complements, not unique product features.
Deep/broad variants should be team/maintainer, not core.

### Product narrative still risks "everything system"

Squads, dashboards, dogfood scorecards, primitive harvesters, broad observability,
and future control planes may be useful for maintainers. They should not dominate
first-contact docs or the default runtime.

## Core/lite default proposal

The sellable first-contact core should be boring and small:

1. install/status/update path;
2. direct-main/protected landing guard;
3. destructive git/rm guard;
4. local secret preflight complement;
5. evidence-backed claim validator;
6. minimal concurrent-write/task claim guard;
7. WIP/session recovery that proves symmetric cleanup;
8. harness settings driver;
9. compact status/readiness report;
10. first-run proof path.

Everything else starts as team, maintainer, or lab.

## KPIs that prove DX is improving

| KPI | Target |
|---|---:|
| Time to first protected run | p95 < 5 minutes human time; automated < 40 seconds |
| Core active hooks | <= 12 default-visible runtime primitives |
| Core startup context tax | < 3K tokens in empty session |
| Hook-chain p95 | core < 300ms; team < 800ms; maintainer < 1500ms |
| False-positive block rate | core < 5%; maintainer < 10% |
| Operator bypass rate | < 5% for core runtime-safety blockers |
| Claim verification integrity | > 95% of done/verified claims include evidence |
| Lab active by default | 0 |
| Primitive churn | created/promoted <= demoted/archived over rolling review windows |
| Portability parity | core smoke proof green on every advertised harness |

## Immediate implementation priorities

1. **Make ADR-126 cover the real runtime surface.** Seed lifecycle metadata from
   `cognitive-os.yaml`, `manifests/hook-quality.yaml`, skills, and rules. Add a
   contract that projected hooks are represented or explicitly allowlisted.
2. **Make ADR-127 detect undercoverage.** Active primitive index should include
   projected hook count, lifecycle-covered count, and coverage status.
3. **Implement ADR-124 distribution projection.** Generate/project settings by
   `core | team | maintainer | lab`, with `core` capped to the low-friction
   runtime-safety surface.
4. **Make ADR-125 enforceable.** Every projected hook needs a governance class;
   meta-governance must be absent from default projection.
5. **Create the core proof path.** Demonstrate: install → dangerous action
   blocked → false-done claim blocked → concurrent edit detected → status report.
6. **Keep vendor/model names out of product concepts.** Model IDs belong in
   provider/routing config, not in readiness gates, product plans, or default docs.

## Senior/Solutions Architect bottom line

If COS defaults to the current maintainer-scale surface, vanilla IDE agents will
feel dramatically better for most developers. If COS ships a true small core and
makes maintainer/lab power opt-in, it becomes a credible product: a guardrail and
coordination layer for agentic development rather than another heavy framework.
