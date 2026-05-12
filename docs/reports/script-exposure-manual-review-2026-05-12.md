# Script Exposure Manual Review — 2026-05-12

Source: `scripts/cos-script-exposure-audit --json` after ADR-283 refinement.
Manual verification excluded generated reports, ACC outputs, SPDX grandfather list, `.cognitive-os/plans/**`, JSON, and self-file matches.

## Numbers after manual review

| Bucket | Count | Manual interpretation |
|---|---:|---|
| P0-unrouted | 0 | No agentic primitive looks truly orphaned after live-reference check. |
| P0-route-undocumented | 10 | Reachable through hook or `scripts/cos`; needs route documentation or skill. |
| P0-promotion-candidate | 50 | Referenced by docs/tests/config/scripts but no direct skill/hook/router route. Needs promotion, demotion, or explicit internalization. |
| P1-zero-consumers | 12 | No live references found. Real loose-tool/archive candidates. |

## P1-zero-consumers — manual disposition

| Script | Manual disposition | Rationale |
|---|---|---|
| `scripts/cos-branch-lock` | archive-or-register | Wrapper has no live refs; backend `scripts/cos_branch_lock.py` is used by hooks and sibling wrapper. Keep backend, decide whether this CLI deserves a route. |
| `scripts/cos-claims.sh` | archive-or-revive | Old ADR-116 claims CLI; no live refs outside self/SPDX. Likely replaced by newer work/claim ledgers unless explicitly revived. |
| `scripts/cos-fingerprint.sh` | archive-or-revive | Old work-identity CLI; no live refs. Check whether `lib.work_identity` is still used before deleting adjacent support. |
| `scripts/cos-locks.sh` | archive | No live refs; likely superseded by edit/branch/session coordination primitives. |
| `scripts/cos-primitive-projection-fidelity` | archive-wrapper-or-register | Wrapper has no refs, but backend `scripts/primitive_projection_fidelity.py` is used by ACC/tests/docs. Keep backend; route wrapper only if desired UX. |
| `scripts/cos-project-registry-prune.sh` | demote-migration-or-archive | No live refs; sounds one-off maintenance. |
| `scripts/cos-validate` | register-or-archive-wrapper | Wrapper no live refs, but `scripts/cos_validate.py` appears in ADR/tests. Either add route/skill or remove stale wrapper. |
| `scripts/portable_ai_consumer_package.py` | archive-or-demote | No live refs; may be superseded by portable `.ai` overlay tooling. |
| `scripts/prelaunch-apply-rewrite` | archive | No live refs; appears part of old prelaunch rewrite trio. |
| `scripts/prelaunch-history-audit` | archive | No live refs; appears part of old prelaunch rewrite trio. |
| `scripts/prelaunch-rewrite-plan` | archive | No live refs; appears part of old prelaunch rewrite trio. |
| `scripts/primitive_service_headless_smoke.py` | register-manual-test-or-archive | No live refs; if still valuable, attach to manual test/release lane. |

## P0-route-undocumented — manual disposition

| Script | Manual disposition | Rationale |
|---|---|---|
| `scripts/_lib/session-id.sh` | document-internal-route | Shared library sourced by edit-lock hooks/scripts; no skill needed. Mark as internal primitive helper or document hook route. |
| `scripts/cos-agent-message` | sunset-or-document-route | Lifecycle says pending-sunset; has hook consumers. Prefer sunset/demotion unless still used operationally. |
| `scripts/cos-architecture-readiness` | document-router-route | Routed by `scripts/cos`; document command route or add skill if agents should call it directly. |
| `scripts/cos-doctor-harness.sh` | document-router-route | Routed by `scripts/cos doctor harness` and binary fallback; document route. |
| `scripts/cos-doctor-tools.sh` | document-hook/install-route | Hook/install-profile managed; os-only. No skill unless operator-facing. |
| `scripts/cos-merge-queue-worker.sh` | document-hook-route | Hook/worker primitive; should not be direct skill unless humans operate it. |
| `scripts/cos-session-coordination` | document-hook-route | Coordination primitive with hook exposure; document route. |
| `scripts/cos-validation-break.sh` | document-router-route | Routed via `scripts/cos`; os-only validation command. |
| `scripts/cos-validation-status.sh` | document-router-route | Routed via `scripts/cos`; os-only validation command. |
| `scripts/set-security-profile.sh` | document-install/hook-route | Install/profile managed with hook/test evidence; no direct skill unless security-profile skill exists. |

## P0-promotion-candidate — manual disposition summary

| Disposition | Count | Scripts |
|---|---:|---|
| add-skill-or-existing-skill-consumer | 15 | `scripts/acc_pipeline.py`, `scripts/cos-active-primitive-index`, `scripts/cos-adapter-compile`, `scripts/cos-adoption-profile`, `scripts/cos-ci-local.sh`, `scripts/cos-core-skills-check.sh`, `scripts/cos-doctor-memory-lifecycle.sh`, `scripts/cos-new-adr`, `scripts/cos-runtime-hook-reality`, `scripts/cos-session-start-budget`, `scripts/cos-silent-failure-audit`, `scripts/cos-wip-safety-score`, `scripts/create-release.sh`, `scripts/security_red_team.py`, `scripts/proof-drill-select` |
| document-install-or-operator-route | 8 | `scripts/cos-bootstrap.sh`, `scripts/cos-credential-safe-run`, `scripts/cos-record-onboarding.sh`, `scripts/cos-weekly-config-audit.sh`, `scripts/cos_init.py`, `scripts/setup.sh`, `scripts/uninstall.sh`, `scripts/upgrade.sh` |
| demote/internal-backend | 17 | `scripts/cos_boring_reliability.py`, `scripts/cos_architecture_readiness.py`, `scripts/cos_closure_discipline_audit.py`, `scripts/cos_new_adr.py`, `scripts/cos_instance_init.py`, `scripts/cos_recovery_drill.py`, `scripts/portable_ai_overlay.py`, `scripts/promote_lifecycle_primitives_to_contracts.py`, `scripts/test_skip_registry.py`, `scripts/cos-preamble-budget`, `scripts/cos-dispatch-smoke`, `scripts/cos-engram-bundle`, `scripts/cos-export-consumer-evidence`, `scripts/cos-federation-trigger-audit`, `scripts/cos-import-consumer-evidence`, `scripts/cos-registry-lock`, `scripts/cos-tier-claim-audit` |
| demote/lab-demo-or-migration | 5 | `scripts/demo-first-run-onboarding.sh`, `scripts/demo-portability-proof.sh`, `scripts/cos-demotion-loop-audit`, `scripts/cos-doctrine-proposer`, `scripts/cos-self-improvement-loop` |
| keep-as-policy-gate-but-document | 5 | `scripts/cos-boring-reliability`, `scripts/cos-closure-discipline-audit`, `scripts/cos-lab-first-gate`, `scripts/cos-manifest-tier-claim-audit`, `scripts/cos-self-improvement-discipline-gate` |

## Recommended next implementation order

1. Fix P1 first: archive/demote/register 12 zero-consumer tools. This should reduce real loose-tool debt.
2. Add or update skills for the 15 high-signal P0 promotion candidates.
3. Document routes for 10 routed P0s in the relevant skills/ADR/manual docs so they stop being ambiguous.
4. Demote/internalize backend/demo/migration scripts in lifecycle metadata so they no longer appear as agentic primitives requiring skills.

## Implementation follow-up — 2026-05-12

Implemented in the follow-up slice:

- P1 zero-consumer scripts were added to `manifests/primitive-readiness-script-overrides.yaml` as `role: archive` so they no longer appear as active maintainer-tool exposure debt.
- The 10 routed P0 scripts were recorded in `manifests/script-exposure-dispositions.yaml` with `resolution: documented_route`; `scripts/cos-script-exposure-audit` now resolves them as `OK-documented-route` without pretending they have skill consumers.
- Two skills now provide explicit skill consumers for high-signal operator/maintainer scripts:
  - `skills/cos-maintainer-operations/SKILL.md`
  - `skills/cos-install-operations/SKILL.md`
- Internal backend, lab/demo, and policy-gate scripts from this review were added to `manifests/primitive-readiness-script-overrides.yaml` so they no longer appear as `agentic-primitive` rows requiring skill exposure.

Post-implementation audit:

```text
scripts total: 543
P0: 0
P1: 0
P2: 348
P3: 61
OK: 134
OK-documented-route: 10
```

Remaining P2 rows are maintainer tools with consumers but no skill consumer. They are not the P0/P1 exposure gap addressed by this review.
