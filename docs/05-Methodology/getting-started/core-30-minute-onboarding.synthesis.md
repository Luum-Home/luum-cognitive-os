---
type: methodology-synthesis
source: docs/05-Methodology/getting-started/core-30-minute-onboarding.md
provenance: "Step-by-step 30-minute onboarding path scoped to the small, default-visible core COS safety layer, deferring maintainer/lab surface until core signals are proven green."
---

## What it is
A 5-step guided path for a developer to validate the "core" Cognitive OS profile — a deliberately small, boring-safe default-visible layer (secrets, destructive operations, concurrent writes, branch safety, runtime reality checks) — before opting into maintainer/lab features.

## Key mechanics
- **Step 1 — inspect core surface:** `scripts/cos-adoption-profile --profile core`, `scripts/cos-preamble-budget --profile core`, `scripts/cos-session-start-budget --profile core`, `python3 scripts/active_primitive_index.py --tier core --json`. Expected: core surface is small enough to read, preamble estimate (including `AGENTS.md`) stays under the core token budget, and `SessionStart` has no lab hooks.
- **Step 2 — prove safety controls are honest:** `scripts/cos-runtime-hook-reality --fail-on-findings`, `scripts/cos-silent-failure-audit --fail-on-findings`, `python3 scripts/cos_architecture_readiness.py --json`. Expected: projected runtime hooks are represented in lifecycle metadata; shell degradation patterns are classified, not hidden.
- **Step 3 — verify WIP and recovery safety:** `scripts/cos-wip-safety-score`, `scripts/cos-recovery-drill --scenario all`. Expected: no orphan pre-agent snapshot markers, no hidden stashes, recovery drills pass or emit an explicit repair instruction.
- **Step 4 — seed dispatch/cost evidence offline:** `scripts/cos-dispatch-smoke --json` exercises the real dispatch metrics path without calling external model providers, appending one task-history record so cost/dispatch tooling stops operating against empty JSONL files.
- **Step 5 — run the local landing gate:** `bash scripts/cos-ci-local.sh quick`; expected to pass before push. The tracked pre-push hook uses the same runner once installed via `bash scripts/install-git-hooks.sh`.
- **Escalation rule:** if any command fails twice with the same signature, stop and fix the underlying primitive — do not silence the gate or add allowlist entries without a rationale, rollback command, and test.

## Relations & where used
- References `scripts/cos-adoption-profile`, `scripts/cos-preamble-budget`, `scripts/cos-session-start-budget`, `scripts/active_primitive_index.py`, `scripts/cos-runtime-hook-reality`, `scripts/cos-silent-failure-audit`, `scripts/cos_architecture_readiness.py`, `scripts/cos-wip-safety-score`, `scripts/cos-recovery-drill`, `scripts/cos-dispatch-smoke`, `scripts/cos-ci-local.sh`, `scripts/install-git-hooks.sh` — the concrete tool surface this path exercises.
- `AGENTS.md` — factored into the preamble-budget check in Step 1.
- Sits as the entry-level "getting-started" companion to deeper Methodology guides (harness adapters, queue routing) that assume this core surface is already validated.

## Status / caveats
- No explicit "last updated" date; framed as a general onboarding path rather than a point-in-time report.
- Assumes a "core" vs. "maintainer/lab" profile distinction that is defined elsewhere in the profile-tooling scripts, not in this document itself — readers relying solely on this doc will need `scripts/cos-adoption-profile` output to see what's actually excluded from core.
