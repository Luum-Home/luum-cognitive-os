# ADR Implementation Reconciliation — 2026-05-05

## Scope

Reviewed the current ADR ledger, all ADRs that were reported as needing
attention, and the additional ADR files that appeared in the worktree during
parallel agent work on May 5.

Sources used:

- `scripts/adr_implementation_ledger.py`
- `scripts/audit_adrs.py`
- ADR files under `docs/adrs/`
- `manifests/adr-closure-metadata.yaml`
- implementation files declared in ADR frontmatter
- targeted contract/unit/audit tests listed below

## Result

Current reconciled ledger after local implementation/reconciliation:

| State | Count | Meaning |
|---|---:|---|
| implemented | 147 | ADR scope has implementation evidence or explicit implemented status with required paths present. |
| absorbed | 11 | Intent is covered by later decisions/architecture. |
| deferred | 3 | Program or future capability intentionally not closed as one implementation. |
| obsolete | 3 | No longer active because the context changed. |
| superseded | 2 | Replaced by another ADR. |
| pending | 1 | New in-development ADR from another agent, not safe to take over in this session. |

Attention count: **1**, and it is intentionally not ours: `ADR-164-host-cli-bridge-security-boundary` appeared with untracked/modified implementation artifacts from another agent. Its worktree surfaces include host-CLI bridge ADR/architecture/manual-test/manifest files, so it should be reconciled by that agent or after explicit handoff.

`scripts/audit_adrs.py --json` reports no failures:

- scanned: 159
- with frontmatter: 36
- failures: 0

## Implemented in This Pass

| ADR | Implemented scope | Key evidence | Caveat |
|---|---|---|---|
| ADR-052 | No-cost offline provider benchmark harness. | `docs/benchmarks/provider-quality-smoke.yaml`, `scripts/benchmark-providers`, `scripts/benchmark_providers.py`, `tests/unit/test_provider_benchmark_and_optimizer.py` | Real provider adapters and LLM-as-judge remain explicit future opt-in work. |
| ADR-053 | Human-reviewed dispatch auto-optimizer proposal generation. | `lib/dispatch_optimizer.py`, `scripts/auto-tune-routing`, `scripts/auto_tune_routing.py`, `tests/unit/test_provider_benchmark_and_optimizer.py` | Proposals are not auto-applied; dispatch integration remains a future reviewed step. |

## Reconciled by Existing Evidence

These ADRs were not missing implementation; their closure metadata or status
heuristics were stale:

| ADR | Reconciled status | Evidence/caveat |
|---|---|---|
| ADR-065 | Implemented by evidence. | `/radar-update` skill, `scripts/radar_merge.py`, and radar merge unit coverage exist; remaining curation is operational. |
| ADR-069 | Implemented by evidence. | Research-first rule, decision tracker, and audit tests exist; one stale research report was explicitly marked deferred for operator triage. |
| ADR-072 | Accepted/implemented classification fixed. | Ledger now lets `Accepted` status win over incidental “reserved” prose in the body. |
| ADR-113 | Implemented by evidence. | Validation lock cleanup, validation break/status scripts, capsule support, and unit/integration coverage exist. |
| ADR-151 | Implemented for consumer availability manifest/classification scope. | Manifest must be maintained as script roles change. |
| ADR-152 | Implemented for shell/CI projection and local-surface defaults. | Structural projection is proven; not universal shell runtime parity. |
| ADR-154 | Implemented for multi-IDE structural projection. | No native lifecycle-hook parity claim for those IDEs. |
| ADR-156 | Implemented for Qwen Code structural projection. | No account-backed Qwen runtime proof. |
| ADR-157 | Implemented for Kimi Code CLI structural projection. | No authenticated Kimi CLI execution proof. |
| ADR-160 | Implemented for rules/MCP structural projection and Kiro design scope. | Kiro native lifecycle runtime remains planned. |
| ADR-161 | Implemented for remote ingress/provider boundary and inventory scope. | Concrete remote ingress/provider adapters remain follow-up work. |
| ADR-162 | Implemented for task lifecycle contract scope. | Full queue/worker/PR runtime enforcement remains service-control-plane follow-up work. |

## Test and Ledger Corrections

- The ACC contract failure was kept strict rather than relaxed: newly discovered service-control-plane/support surfaces were classified explicitly in `manifests/primitive-consumer-availability.yaml`, bringing ACC new debt to zero.
- `decision_state_from_status()` now recognizes `implemented` and gives `accepted` precedence over incidental body text containing `reserved`.
- `implementation_state()` now treats frontmatter `status: implemented` plus present `implementation_files` as implemented.
- `manifests/adr-closure-metadata.yaml` now closes ADR-065, ADR-069, and ADR-113 as `evidence-only` instead of stale `deferred`.

## Validation

```bash
python3 -m pytest   tests/unit/test_provider_benchmark_and_optimizer.py   tests/unit/test_adr_implementation_ledger.py   -q
# 14 passed in 0.42s

python3 -m pytest   tests/unit/test_provider_benchmark_and_optimizer.py   tests/unit/test_adr_implementation_ledger.py   tests/unit/test_radar_merge.py   tests/integration/test_validation_status_break.py   tests/audit/test_decision_tracking_convention.py   tests/audit/test_doc_paths_tracked.py   tests/audit/test_research_reports_format.py   -q
# 62 passed, 5 skipped after marking the stale cos-init research decision as explicitly deferred

python3 scripts/audit_adrs.py --json
# failures: 0

python3 scripts/adr_implementation_ledger.py --json
# attention_count: 1 (ADR-164 in another agent's worktree scope)
```

## Remaining Non-Implementation Buckets

These are not current “missing implementation” findings:

- deferred: ADR-118, ADR-121, ADR-123. These are phase/program umbrellas, not atomic features to implement blindly in this session.
- pending: ADR-164. It is in active parallel-agent development and should not be overwritten here.
- superseded: ADR-011, ADR-084.
- obsolete: ADR-017, ADR-022, ADR-058.
- absorbed: 11 older ADRs covered by later architecture/decision records.

## Next Work

1. Let the ADR-164 owner finish or explicitly hand off host-CLI bridge security-boundary artifacts before reconciling that ADR.
2. If the user wants ADR-118/121/123 advanced, split each program into concrete phase slices with separate acceptance criteria before implementation.
3. Keep ACC strict: new scripts/hooks should receive explicit consumer availability classification or projection proof.
4. Add real provider adapters to ADR-052 only behind an explicit no-surprise-cost boundary.
5. Wire ADR-053 proposals into dispatch only after operator-reviewed routing policy semantics are accepted.
