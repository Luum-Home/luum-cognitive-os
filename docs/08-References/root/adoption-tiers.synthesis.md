---
type: reference-synthesis
source: docs/08-References/root/adoption-tiers.md
provenance: "Auto-generated reference mapping three concrete adoption tiers (lean/standard/strict) to exact hooks, primitives, and skills, so a new adopter can decide how much of the OS to enable without reading the full architecture."
---

## What it is

A generated (not hand-authored) reference document that maps three adoption tiers — **Lean**, **Standard**, **Strict** — to specific security profiles, hook lists, active library primitives, useful skills, setup commands, and measured per-turn overhead, plus a decision tree, tier-migration paths, and anti-patterns for when not to use the OS at all.

## Key mechanics

- **Decision tree**: routes on concurrent-session count and multi-IDE/multi-project usage, not headcount alone. Key rule: a single developer running two+ harnesses (e.g., Claude Code + Codex) simultaneously, or multiple sessions/sub-agents/projects at once, is classified **Strict**, not Lean — this is the document's central "solo maintainer swarm is Strict, not Lean" thesis.
- **Lean** (1 developer, 1 session): `minimal.json` profile, 116 hooks, 15–30 min setup. Prevents direct-to-main commits, destructive git ops, concurrent same-file writes, secret leaks in Edit/Write, lethal-tool-sequence combinations, unverified "done" claims, and WIP loss across restarts. Does **not** prevent cross-session duplicate claims, orphaned commits after rebase, or stale-session accumulation (needs Standard). ~116 hook fires/turn, no background daemons, Engram optional.
- **Standard** (2–5 developers or occasional parallel sessions): `standard.json` profile, 154 hooks, 45–90 min setup. Adds: preflight gate blocking dirty-worktree agent dispatch, atomic task-claim ledger (`lib/task_claim_ledger.py`), append-only session event bus (`lib/session_bus.py`), branch guard for sub-agents, FS reaper (archive-first stale-session cleanup), stash auto-reapply with provenance, Engram memory as claim source-of-truth, blast-radius and clarification gates, and a coordination-status CLI. Does not prevent concurrent main landings without a merge queue, cross-machine coordination, or chaos-level swarm races (needs Strict). ~154 hook fires/turn, one Engram daemon.
- **Strict** (5+ people, 5+ concurrent sessions, or the solo multi-IDE swarm persona): `paranoid.json` profile, 170 hooks, 2–4 hours setup. Adds: full merge queue (only `merge-to-main.sh` may advance main, flock-serialized), work-identity fingerprinting against last 200 origin/main commits, push-time and pre-commit content-hash collision detection, orphan-commit notifier writing to bus+Engram, plan-claim validator in block mode, stale-task watermarking, Engram advisory locks, default-on validation-capsule full mode (worktree isolation per ADR-109), a chaos-validation test lane, and guard-maturity enforcement (no hook may default to block without false-positive tests). At strict tier, `agent-prelaunch.sh` runs with `COS_PREFLIGHT_STRICT=1`, disabling ephemeral-path and read-only-role exemptions — every worktree race risk is BLOCK regardless of agent role. Does not prevent cross-machine coordination or remote-provider failure (needs vendor-native branch protection as primary guarantee, per ADR-116 §P2.2a).
- **Migration paths** are additive and reversible: swap the `settings.json` profile file, flip named boolean flags in `cognitive-os.yaml` under `multi_session:`, no database migrations or schema changes; rollback = flip flags back to false and remove hook registration.
- **Three explicit anti-patterns** (do not adopt the OS): (1) solo prototyping where iteration speed matters more than safety — signal is setting `COS_ALLOW_DESTRUCTIVE=1` repeatedly; (2) fully headless CI with no human to respond to blocking gates — signal is needing 10+ `COS_*=bypass` env vars; (3) an org that hard-prohibits pre-commit/pre-tool-use hooks — the OS will appear installed but its safety guarantees silently won't hold; verify with `hooks/self-install.sh` plus checking `hooks/session-sanity.sh` exit status.
- Comparison table consolidates hook counts, ADR-116/121/122/119/105 coverage, Engram requirement, merge-queue presence, chaos-validation presence, setup time, and rollback cost across all three tiers.

## Relations & where used

Grounded in ADR-105 (claim verification), ADR-116 (12 multi-session coordination primitives, P1.1–P5.2), ADR-119 (session filesystem reaper), ADR-121 (6 foundation-hardening invariants), ADR-122 (preflight refinements), ADR-123 (guard maturity/adaptive profiles). Cross-references `docs/09-Quality/root/hook-security-profiles.md` (profile design rationale), `docs/00-MOCs/entrypoints/getting-started.md`, and `docs/04-Concepts/architecture/cross-harness-authoring.md`.

## Status / caveats

**This is a generated file, not hand-authored** — the source's final line states: "Generated from e2ffb8e5e on 2026-06-12T17:50:19Z. Do not edit directly. Run `python3 scripts/render_adoption_tiers.py` to regenerate." Treat all specific hook counts (116/154/170), timing figures (e.g., "~400ms per sub-agent dispatch," "~600ms with --strict"), and file paths as accurate as of that generation timestamp/commit and subject to silent drift on the next regeneration. No internal inconsistency was found in the document itself.
