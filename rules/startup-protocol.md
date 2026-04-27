<!-- SCOPE: both -->

# Session Startup Protocol

## Purpose

Prevent writing new ADRs/plans without consulting existing ones, prevent work on
already-resolved items, and prevent drift between declared config and runtime
implementation. Every new session (and every engineer joining the project) must
load the minimum context needed to act responsibly before executing non-trivial
work.

This rule formalizes what was previously tribal knowledge: the 5-step context
check that the orchestrator performs before committing to a direction.

## Mandatory Steps (before any non-trivial work)

### 1. Memory context

Run `mem_search` against Engram for the project (`luum-cognitive-os`) to load
prior decisions, open threads, and the last session summary. Follow the Engram
protocol in `rules/ROADMAP.md` / CLAUDE.md: `mem_context` -> `mem_search` ->
`mem_get_observation` for the full body of relevant topics.

Goal: learn what was decided, what was deferred, and what is in-flight — BEFORE
you propose anything new.

### 2. Plans <-> ADRs cross-reference

List `.cognitive-os/plans/features/` and cross-reference against `docs/adrs/`.
Any time you are about to draft a new ADR or new plan, check whether:
- an existing plan already covers this scope (extend it, don't duplicate)
- an existing ADR already decided this question (extend it with an addendum
  rather than superseding it blindly)

User quote (2026-04-21): "si hubiera hecho esto hoy, habria consultado
hook-architecture-v2.md, stabilization-mega-plan.md y
token-optimization-masterplan.md ANTES de escribir ADR-027/028 — y
probablemente los ADRs habrian sido addenda, no docs nuevos."

### 3. Work queue state

Read `.cognitive-os/work-queue.json`. Ignore `completed_this_sprint[]` — that is
history. Inspect `live`, `parked`, `blocked`, and any equivalent buckets to
understand what is currently in progress, what is paused, and why.

If the task you are about to start overlaps with a live or parked item, HALT
and reconcile before acting.

### 4. Runtime validator

Run `python3 scripts/cos-config-audit.sh` (aka `cos-config-audit.sh --json` for
machine consumption). This compares `cognitive-os.yaml` declarations against
actual wiring in hooks/scripts/lib and reports each section as IMPL / PARTIAL /
ASPIR.

Goal: know which parts of the config are actually enforced before you rely on
them, and avoid writing specs that assume behaviour that is not wired.

### 5. Triggered — only then execute

Once steps 1-4 are done (or explicitly skipped under the rules below), state a
brief "context check" summary to the user, then execute. Do not start by
writing code or drafting ADRs.

## When the protocol is NOT required

- **Trivial edits**: single-file typo fixes, cosmetic renames, obvious
  one-liner corrections covered by `rules/adaptive-bypass.md`.
- **Follow-up within the same active work item**: if you are already inside a
  task that consulted context at the start, additional turns within the same
  task do not re-run the protocol — the hook's advisory output at session
  start is sufficient reminder.
- **Read-only questions**: purely informational queries ("what does X do?")
  that will not produce changes.

For everything else (new plan, new ADR, new hook, new rule, refactor, migration,
cross-service work) the protocol is mandatory.

## Escalation

If the protocol check surfaces unresolved conflicts — e.g. an existing plan
already covers the task you are about to do, or the validator reports the
subsystem you were about to extend as ASPIR — HALT and reconcile before
proceeding. Options:

1. Extend the existing plan/ADR with an addendum rather than creating a new one.
2. Update `.cognitive-os/work-queue.json` to reflect the merge.
3. Ask the user to confirm the direction before spending tokens on new
   artifacts.

Do NOT silently override. Do NOT create parallel docs. Do NOT ignore PARTIAL /
ASPIR validator rows without noting them.

## Enforcement

- `hooks/session-startup-protocol.sh` (SessionStart, advisory) emits a compact
  5-line context summary at session start so the orchestrator is reminded of
  the current state before the first user prompt.
- Registered in the `standard` security profile and the default efficiency
  profile (see `scripts/set-security-profile.sh` and
  `scripts/apply-efficiency-profile.sh`).
- Advisory only — the hook never blocks session start. If a dependency is
  missing (e.g. `cos-config-audit.sh`), it degrades gracefully.

## Contextual Trigger

Always active at session start. Reviewed after compaction (compaction resets
context; the orchestrator must re-consult Engram and the validator summary
before resuming substantive work).
