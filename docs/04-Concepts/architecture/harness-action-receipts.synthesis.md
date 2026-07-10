---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-action-receipts.md
provenance: "Codex Desktop emits harness-specific final-response directives (e.g. ::git-commit{cwd=...}) that must not be confused with COS agentic primitives or safety boundaries; a vendor-neutral receipt vocabulary was needed."
---

## What it is
Vendor-neutral contract, "harness action receipt", for recording Git/workflow actions reported by an agent harness (e.g. Codex `::git-*{...}` directives) without letting harness UI directives become safety boundaries or COS primitives.

## Key mechanics
- Trust ladder: `advisory` (directive/chat claim, unverified) → `observed` (local git state check confirms it) → `verified` (COS hook/governed runner emitted it) → `authoritative` (merge queue/protected landing/provider-native advanced state).
- Non-negotiable rule: a final-response directive is never a safety boundary — real safety comes from `git diff --cached`/`git status`, PreToolUse/Git hooks, pre-commit/pre-push checks, branch writer leases, merge queue, protected landing.
- Schema `harness-action-receipt.v1`: fields `event_type` (e.g. `vcs.stage`, `vcs.commit`, `vcs.push`, `vcs.pr.create`, `vcs.merge.land`), `domain`, `action`, `provider`, `source`, `trust`, `project_dir`, `branch`, `timestamp`, optional `files`/`commit_sha`/`remote`/`protected_branch`/`governed_path`/`queue_entry_id`/`bypass_reason`/`evidence`.
- Implemented baseline: `lib/harness_action_receipts.py`, `scripts/cos-action-receipt` (subcommands `emit`, `parse-codex`, `stats`, `report`), `tests/unit/test_harness_action_receipts.py`; appends to `.cognitive-os/metrics/vcs-actions.jsonl`.
- Promotion rules implemented: `vcs.stage`→observed via `git diff --cached --name-only`; `vcs.commit`→observed via `HEAD`; `vcs.branch.create`→observed via current branch; `vcs.push`→observed via matching remote SHA, →verified via pre-push refs, →authoritative via provider API `accepted=true`.
- Composes with existing primitives: `scripts/git-coop.sh`, `hooks/git-commit-scope-guard.sh`, `hooks/direct-main-guard.sh`, `hooks/destructive-git-blocker.sh`, `hooks/pre-commit-gate.sh`, `scripts/merge-to-main.sh`/`lib/merge_queue.py`, `lib/event_bus.py`, `scripts/cos_branch_lease.py`.
- Storage surfaces by trust: `.cognitive-os/metrics/vcs-actions.jsonl` (all), `.cognitive-os/sessions/events.jsonl` (verified/authoritative only by default), session git-context.json, docs/dashboard (all, labeled).
- Phased rollout: Phase 0 docs-only; Phase 1 local receipt writer (implemented); Phase 2 existing-primitive integration (implemented for local shell/script surfaces: `git-commit-scope-guard.sh`, `direct-main-guard.sh`, `merge-to-main.sh`, `git-context-capture.sh`); Phase 3 harness directive adapters (Codex parsing); Phase 4 dashboard/ACC visibility.

## Relations & where used
ADR-190 (decision record), Protected Landing Contract, ADR-116 (multi-session coordination), Harness Driver Parity, Codex Governed Tool Layer, ADR-064, ADR-189.

## Status / caveats
Phase 1 baseline implemented; enforcement behavior unchanged (receipts are telemetry only). Remaining hardening: redaction modes for public reports, first-class provider adapters, mirroring `cos_lib.merge_queue` events, post-commit/post-push hook adapters.
