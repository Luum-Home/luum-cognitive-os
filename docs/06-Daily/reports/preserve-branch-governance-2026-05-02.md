# Preserve Branch Governance Report — 2026-05-02

> Status: diagnostic report
> Scope: `codex/preserve-*` branch lifecycle and safety governance
> Related: [ADR-110](../adrs/ADR-110-preserve-branch-governance.md), [Preserve Branch Lifecycle](../architecture/preserve-branch-lifecycle.md)

## Executive Summary

Automatic preservation branches are useful. They prevented work loss during concurrent-agent activity by keeping WIP reachable even when the active `main` branch moved. However, the current preservation flow is under-governed: a preserved commit can exist in Git without being an ancestor of `HEAD`, and mixed-scope preservation branches can combine unrelated work in one archive.

The correct policy is:

> Preserve automatically; reintegrate manually and selectively; delete only after proof.

## Current Evidence

At the time of this report, the repository had seven local preserve branches:

- `codex/preserve-agentic-safety-wip-20260502`
- `codex/preserve-concurrent-safety-wip-20260502b`
- `codex/preserve-concurrent-testbed-wip-20260502`
- `codex/preserve-lethal-trifecta-wip-20260502b`
- `codex/preserve-local-wip-20260502`
- `codex/preserve-rollback-planning-wip-20260502`
- `codex/preserve-validation-capsule-wip-20260502`

The critical lesson came from the concurrent-agent safety testbed:

- commit `004e4ae4` existed;
- it was not an ancestor of `HEAD` after preservation/concurrent cleanup;
- the files were therefore absent from the active branch;
- restoration required a deliberate cherry-pick, producing `0b6931f5`.

Commit existence was not enough. The required proof was ancestry plus file presence in `HEAD`.

## Failure Modes

| Failure mode | Why it matters | Required control |
|---|---|---|
| Preserve branch without manifest | Operator cannot tell intent, owner, status, or safe next action. | Manifest required for every `codex/preserve-*` branch. |
| Mixed-scope preserve branch | Selective restore becomes error-prone and can pull unrelated changes. | Doctor flags multiple change categories. |
| Commit exists but is not ancestor of `HEAD` | Work appears safe but is not active. | Doctor reports not-integrated preserve tips. |
| Preserve branch already integrated | Branch remains as stale operational noise. | Doctor marks delete candidate after proof. |
| Manual reintegration without evidence | Reintroduces stale or unrelated WIP. | Restore/cherry-pick must be selective and validated. |

## Scope Decision

This governance must apply to both the SO repository and consumer projects. The SO owns the primitive and proof suite; consumer projects get a projected policy through `--project-dir`, `--branch-pattern`, manifest location, and strict mode.

## Recommendation

Implement Preserve Branch Governance:

1. ADR-110 defines the policy.
2. `docs/04-Concepts/architecture/preserve-branch-lifecycle.md` defines lifecycle states.
3. `scripts/cos-doctor-preserve.sh` reports missing manifests, mixed-scope branches, integrated branches, non-ancestor tips, and delete candidates.
4. Tests prove all five required scenarios automatically.

## Acceptance Criteria

```bash
python3 -m pytest tests/behavior/test_cos_doctor_preserve.py -v
bash scripts/cos-doctor-preserve.sh --json
```

Manual inspection is not sufficient for this governance layer.
