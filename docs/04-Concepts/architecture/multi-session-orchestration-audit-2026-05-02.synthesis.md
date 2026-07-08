---
type: concept-synthesis
source: docs/04-Concepts/architecture/multi-session-orchestration-audit-2026-05-02.md
provenance: "Audit of documented-vs-implemented status for primitives coordinating multiple IDEs, sessions, worktrees, and agents."
---

## What it is
Verdict (2026-05-02): Cognitive OS already has real coordination primitives (session identity, git-index coordination, file edit locks, claim verification, agent bus monitoring, sprint manifests, stash leak alarms, harness projection). Missing layer is not another launcher but a unifying Concurrent Agent Safety Layer composing them into a ledger, resource leases, reconciliation, and cross-session status.

## Key mechanics
Status matrix (primitive -> implementation -> status):
- Bilateral claim verification (ADR-105): `lib/orchestrator_verify.py`, `hooks/claim-validator.sh`, `hooks/plan-claim-validator.sh`, `hooks/orchestrator-claim-gate.sh` — Real, recently expanded, wired in both `.claude/settings.json` and `.codex/hooks.json`.
- Git-index coordination (ADR-089): `scripts/git-coop.sh`, `hooks/git-commit-scope-guard.sh` — Real.
- File edit coordination (ADR-098): `scripts/edit-coop.sh`, `hooks/edit-lock-pre-tool.sh`, `hooks/concurrent-write-guard.sh` — Real in Claude (now wired in `PreToolUse Edit|Write` via `scripts/_lib/settings-driver-claude-code.sh`); Codex lacks the Edit/Write matcher surface.
- Session identity: `hooks/session-init.sh`, `.cognitive-os/sessions/`, `.active-sessions.lock` — Real.
- Stash leak alarm (ADR-106): `scripts/stash-leak-alarm.sh` — Real detector, dispatch integration partial.
- Plan closure validation: `hooks/plan-claim-validator.sh`, `scripts/verify_plan_claims.py` — Partial cross-harness (limited by Codex).
- Provenance markers (ADR-088): `scripts/write_context_marker.py` — Real, needs end-to-end enforcement review.
- Agent bus monitoring: `lib/agent_bus.py`, `lib/agent_bus_metrics.py`, `scripts/orchestrator.py` — Real, not full control plane.
- Sprint orchestration (ADR-036): `scripts/cos_sprint.py`, `lib/sprint_test_aggregator.py` — Real MVP.
- Concurrent Agent Safety Layer (ADR-108): composed from pieces above, no single composer — Missing unified layer.
- Agent Work Ledger, Resource Lease (ADR-108): not unified runtime primitives — Aspirational.
- Read-only safety status composer: `lib/concurrent_agent_safety_status.py`, `scripts/cos_concurrent_status.py` — Real initial slice; observation only (lists active sessions, edit/git/plan locks, stash alarm state, claim-gate status, agent bus heartbeats, missing provenance/closure evidence; emits single JSON).
- Cross-session reconciler: status composer exists, divergence policy/reconciliation loop incomplete — Partial.
- Squad runtime coordination: docs/skills only, no confirmed session-level coordinator — Dormant.

Do-not-rebuild list: extend `git-coop.sh`/`git-commit-scope-guard.sh`, `edit-coop.sh`/`edit-lock-pre-tool.sh`, `orchestrator_verify.py`/`orchestrator_claim_gate.py`, `agent_bus.py`/`agent_bus_metrics.py`, `cos_sprint.py`/`sprint_test_aggregator.py`, settings drivers — do not create parallel implementations.

## Relations & where used
ADR-105, ADR-089, ADR-098, ADR-106, ADR-088, ADR-108, ADR-111, ADR-028; verification commands: `pytest tests/contracts/test_orchestrator_claim_gate.py`, `tests/unit/test_concurrent_agent_safety_status.py`, `tests/unit/test_edit_coop.py tests/unit/test_git_coop.py`, `tests/integration/test_concurrent_agent_same_file.py tests/behavior/test_plan_false_done_gate.py tests/behavior/test_stash_leak_alarm.py`.

## Status / caveats
Next milestone: turn the read-only status payload into a reconciler policy comparing divergent plan/claim/provenance state without mutating state (no auto-repair yet).
