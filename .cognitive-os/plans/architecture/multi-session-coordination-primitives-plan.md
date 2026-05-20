# Multi-Session Coordination Primitives — Cross-IDE Implementation Plan

## Metadata

- **ADR**: `docs/02-Decisions/adrs/ADR-116-multi-session-coordination-primitives.md`
- **Scope**: OS core with consumer-project projection
- **IDEs / harnesses**: Claude Code, Codex, Kiro, human terminal, future IDEs through script contracts
- **Phase**: reconstruction
- **Owner model**: kernel scripts first, driver projections second

## Goal

Make concurrent sessions coordinate before they claim, commit, push, or mark work done. The end-state is per-session isolation plus a serialized landing queue; the immediate state is ledger, status, collision detection, and shared evidence.

## Acceptance criteria

1. Duplicate pending-task pickup is blocked by `.cognitive-os/tasks/active-claims.json`.
2. Work identity is stable across task claims, commits, and plan checkbox transitions.
3. Every supported IDE reads/writes the same local coordination files and does not fork policy logic.
4. Operators have one command for global coordination status.
5. Push-time duplicate work is blocked before reaching origin.
6. Per-session branches and a merge queue become the default route to `main`.
7. Engram records material claims/completions when available, with local ledgers remaining authoritative for enforcement.

## Batch 0 — Baseline quick wins already started

- [x] P1.1 task-claim ledger
  - **Deliverable**: `scripts/cos_task_claims.py`, `.cognitive-os/tasks/active-claims.json` schema, `.cognitive-os/sessions/events.jsonl` event emission.
  - **Projection**: called from `scripts/write_context_marker.py` when a pending task is taken.
  - **Verify**: `python3 -m pytest tests/unit/test_cos_task_claims.py -q` exits 0.

- [x] P3.3 coordination status CLI
  - **Deliverable**: `scripts/cos-coordination-status.py`, `scripts/cos-coordination-status.sh`, updated `skills/coordination-status/SKILL.md`.
  - **Verify**: `python3 scripts/cos-coordination-status.py --json | python3 -m json.tool` exits 0.

- [x] P4.2 push-time collision detection
  - **Deliverable**: `scripts/orchestrator_claim_gate.py` pre-push subject/patch-id collision check, `.githooks/pre-push`, `scripts/setup-git-hooks.sh`.
  - **Verify**: `python3 -m pytest tests/contracts/test_orchestrator_claim_gate.py -q` exits 0.

## Batch 1 — Work identity everywhere

- [x] P1.2 commit `work_id` trailer (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: commit message trailer `X-COS-Work-ID: <hash>` generated from task fingerprint or explicitly supplied by operator.
  - **Files**: `scripts/commit_provenance.py`, commit-message hook/projection files, tests under `tests/unit/` or `tests/contracts/`.
  - **Verify**: creating a COS-attributed test commit includes both `X-COS-Session` and `X-COS-Work-ID`.

- [x] P4.1 pre-commit patch-id dedupe (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: staged diff patch-id comparison against recent `origin/main`.
  - **Files**: `scripts/orchestrator_claim_gate.py` or dedicated importable helper.
  - **Verify**: staged duplicate diff returns block/skip finding; unique diff passes.

- [x] P4.4 atomic plan-checkbox transition proof (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: plan transition parser emits/validates `work_id` plus `(verified: ...)` proof.
  - **Files**: `scripts/verify_plan_claims.py`, `hooks/plan-claim-validator.sh`, tests.
  - **Verify**: high-stakes `[x]` without proof blocks; verified line passes; parser false positives remain covered.

## Batch 2 — Stale-task and event bus completion

- [x] P1.3 event bus watcher contract (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: documented JSONL schema and optional `tail` watcher that summarizes `claim`, `complete`, and `conflict` events.
  - **Files**: `scripts/cos_task_claims.py`, new tests, docs.
  - **Verify**: claim/complete/conflict events append valid JSONL rows.

- [x] P1.4 stale-task watermark (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: task reaper detects declared outputs landed in `main` and marks pending tasks completed/superseded even if completed by another session.
  - **Files**: `scripts/so-reaper.sh` or Python helper, active-task tests.
  - **Verify**: fixture pending task with output present in `origin/main` changes status without PID dependency.

## Batch 3 — Retrospective safety telemetry

- [x] P3.1 orphan-commit notifier (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: post-reset/rebase/pull/session-start scanner for unreachable commits not in main.
  - **Files**: new importable scanner or extension to coordination status; session hook projection.
  - **Verify**: synthetic unreachable commit appears in report and status command.

- [x] P3.2 `git reset --hard` protection (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: PreToolUse Bash gate / shell wrapper that snapshots reflog, stashes WIP with provenance, and requires explicit operator approval.
  - **Files**: hook, tests, generated settings projections.
  - **Verify**: raw reset with WIP blocks; approved controlled reset records snapshot.

- [x] P4.3 stash provenance and auto-reapply policy (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: stash metadata schema and SessionStart reapply/suggest behavior.
  - **Files**: pre-agent snapshot path, session init/resume hooks, tests.
  - **Verify**: COS-created stash records session/task; next matching SessionStart surfaces action.

## Batch 4 — Cross-IDE projection

- [x] Claude Code projection (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: `.claude/settings.json` and generator invoke claim/status/collision gates at matching lifecycle points.
  - **Verify**: generator test proves hook path inclusion.

- [x] Codex projection (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: `.codex/hooks.json` or documented Codex fallback invokes the same script contracts where Codex exposes hook points.
  - **Verify**: Codex projection test or documented manual smoke proves status and pre-push fallback.

- [x] Kiro projection (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: `.kiro/hooks/*.kiro.hook` call shared scripts for session init/stop, pre-shell gates, and post-agent checks where supported.
  - **Verify**: static projection test checks script references and executable paths.

- [x] Human terminal projection (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: `.githooks/pre-push`, shell wrappers, and docs support non-IDE usage.
  - **Verify**: setup-git-hooks integration tests remain green.

## Batch 5 — Structural isolation

- [x] P2.1 local direct-main policy
  - **Deliverable**: `hooks/direct-main-guard.sh` blocks autonomous agents/sub-agents from direct commits on `main`/`master`, warns operator commits by default, and supports `COS_OPERATOR_MAIN_POLICY=block|warn|allow`.
  - **Verify**: direct-main guard tests cover agent block, operator warn, operator block, and feature-branch no-op.

- [x] P2.1 session branch default-on workflow (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: SessionStart creates/switches to `<harness>/session-<id>` branch unless disabled by explicit config.
  - **Verify**: SessionStart fixture starts from main and ends on session branch with provenance metadata.

- [x] P2.2 merge queue / landing pipeline (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: single landing command serializes merges into `main`, runs gates, and records result.
  - **Verify**: two session branches landing concurrently serialize; second waits or aborts with clear message.

- [x] P2.2a vendor-neutral protected landing boundary (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: provider adapter/status contract for protected landing across GitHub, GitLab, Gitea/Forgejo, Bitbucket, bare Git/server hooks, and unknown remotes; no dependency on `gh`.
  - **Verify**: docs/tests prove GitHub is optional; direct push to `main` is rejected by the strongest available layer, or local-only fallback is explicitly reported.

- [x] P2.3 validation capsule full mode alignment (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: normal session branch behavior and validation capsule isolation share worktree/landing contracts.
  - **Verify**: validation capsule tests and new session-branch tests pass together.

## Batch 6 — Engram shared evidence

- [x] P5.1 Engram claims/completions protocol (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: stable topics `claims/<task-id>` and `work/<work-id>` for material claims and completions.
  - **Verify**: when Engram is available, claiming/completing material work persists a memory observation; local ledger still works without Engram.

- [x] P5.2 Engram advisory locks (closed: transferred to ADR-116/ADR-121 follow-up backlog; not closed as implementation completion; verified: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md)
  - **Deliverable**: optional `lock/<resource>` topic convention with TTL metadata and local fallback.
  - **Verify**: session B detects a live advisory lock before touching resource; stale TTL allows takeover.

## Rollout order

1. Keep Batch 0 enabled in warn/block mode according to current reconstruction tolerance.
2. Land Batch 1 before relying on dedupe across commits and plans.
3. Land Batch 2 before declaring pending-task state trustworthy.
4. Land Batch 4 before claiming cross-IDE parity.
5. Land Batch 5 before claiming main-branch races are structurally eliminated.
6. Land Batch 6 after local file contracts are stable.

## Risks

- Subject-based push collision can false-positive. Mitigation: block with explicit remediation instructions rather than auto-dropping commits.
- Work ID must be stable but not overfit to exact wording. Use normalized title, deliverables, expected outputs, and verify commands.
- IDE hook surfaces differ. The portable contract is the script interface; projection is best-effort per driver.
- Engram availability varies. Never make memory availability the only enforcement path.

## Validation command set

```bash
python3 -m py_compile scripts/cos_task_claims.py scripts/cos-coordination-status.py scripts/orchestrator_claim_gate.py scripts/write_context_marker.py
bash -n scripts/cos-coordination-status.sh .githooks/pre-push scripts/setup-git-hooks.sh
python3 scripts/cos-coordination-status.py --json | python3 -m json.tool
python3 scripts/orchestrator_claim_gate.py --mode pre-push --command 'git push' --json
python3 -m pytest tests/unit/test_cos_task_claims.py tests/contracts/test_orchestrator_claim_gate.py -q
python3 -m pytest tests/integration/test_setup_git_hooks_path.py::test_pre_push_hook_skips_feature_branches tests/integration/test_setup_git_hooks_path.py::test_pre_push_hook_allows_main_and_tag_pushes -q
```
