---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-089-multi-session-git-coordination.md
adr: ADR-089
status: accepted
reality_level: PARTIAL
provenance: On 2026-04-30, running concurrent Claude Code sessions against the same working tree produced four distinct failure modes in one day — a commit that pulled in 9 unrelated files staged by a parallel session (requiring a revert), repeated ADR-slot collisions requiring manual renumbering, phantom autocommits from a session with no visibility signal, and commits invisible until an explicit git log.
---

## Decision

Three coordination layers shipped in value-to-risk order. Layer 1 (high value, low risk): mandate `git commit --only -- <path>` (or explicit `-a` with stated intent) for all agent-driven commits, enforced by a new `PreToolUse[Bash]` hook `hooks/git-commit-scope-guard.sh` that runs advisory in single-session mode and enforcing in detected multi-session mode. Layer 2 (medium value/risk): a cooperative POSIX-`mkdir`-based lock (`scripts/git-coop.sh acquire`/`release`) around any `git add`/`commit`/`mv`/`rm`, with a 5-minute stale-lock TTL and 30-second acquire timeout. Layer 3 (medium value, low risk): atomic ADR-slot reservation (`scripts/reserve_adr_slot.py`) via `mkdir`-based reservation placeholders with a 30-minute TTL, replacing the read-`ls`-then-increment race.

## Why

Four concrete failure modes from one day of dogfooding two concurrent sessions (Session A drafting ADRs, Session B shipping ADR-081/086/test-lane work): (1) commit scope inflation — Session A's intended 1-file rename commit (`git mv` + bare `git commit -m`) pulled in 9 files Session B had staged in the same shared git index, requiring a revert (`4ef7dc1`) and a clean redo using `git commit --only --`; (2) ADR slot collisions — ADR-085 was claimed by both sessions within minutes, requiring renumbering to 086/087, then the same collision repeated at 088 (this very ADR was itself renumbered from a reserved 088 to 089 mid-drafting, becoming a live example of the failure it addresses); (3) phantom autocommits — commits with `X-COS-Session` trailers from Session B appeared in Session A's context with no signal Session A had another active session; (4) memory ghosts — Session B's commits stayed invisible to Session A until an explicit `git log`. Root-cause forensics ruled out all existing hooks (`auto-checkpoint.sh` can only shrink commit scope, never inflate it; sync hooks are scoped to unrelated paths) — the inflation is entirely explained by the shared mutable git index plus the absence of a pathspec on `git commit`.

## Consequences

Positive: Layer 1 eliminates scope inflation structurally — a commit contains exactly what was staged by that session regardless of index state; Layer 3 makes ADR-slot assignment atomic, eliminating the exact renumbering churn this ADR itself suffered; multi-session becomes an acknowledged first-class workflow rather than an unhandled edge case; lock contention becomes observable (the blocked session sees the holder's session ID and operation).

Negative/trade-offs: three new artifacts to write and test; lock acquire/release adds ~10-100ms per git operation (judged negligible against ~100ms git process overhead); the design is N-safe but not starvation-free for N>2 sessions (untested — today's incident was exactly 2 sessions); this ADR explicitly does not fix cross-session memory/awareness (deferred to ADR-071's domain) — it addresses only git coordination; `git commit --only --` is a less-common invocation form than plain `git commit <path>`, though the guard hook removes the need for operators to remember it.

## Status & current state

Accepted, executed 2026-04-30 by Session A. All three layers implemented same-day: `hooks/git-commit-scope-guard.sh` (Python 3 for scope analysis — macOS BSD sed was found unable to reliably tokenize quoted pathspecs), `scripts/git-coop.sh` (session-ID fallback to `shell-<PPID>` when `COGNITIVE_OS_SESSION_ID` unset), `scripts/reserve_adr_slot.py` (wraps a pre-existing but differently-shaped `scripts/adr_reserve.py` rather than reimplementing atomic reservation). Pre-check found Layer 3's underlying atomic-reservation logic already existed with a full test suite but a different lock path and CLI — the new script is a compatibility wrapper, not new fcntl logic. 25 new behavioral tests added across two test files, executing scripts as subprocesses to catch shell/Python integration issues that function-level unit tests would miss. `partial_remaining` in frontmatter defers extending slot-reservation beyond ADRs to other sequential-number artifact types "if collisions are observed there."

## Key links

ADR-082 (plan location convention — same root-cause class, shared mutable state without coordination), ADR-087 (ADR namespace consolidation — the slot-collision diagnosis that preceded this ADR), ADR-088 (provenance trailer via PPID chain — shipped concurrently by Session B, itself claimed the 088 slot this ADR had reserved, directly demonstrating the failure mode), ADR-072 (test lane taxonomy — the parallel work Session B was executing during the incident), ADR-071 (engram lifecycle — explicitly out of this ADR's scope), ADR-116 (Multi-Session Coordination Primitives — later, broader superset of coordination work building on this ADR's Layer 1-3 foundation). Commits: `a4ab471` (inflated), `4ef7dc1` (revert), `b9bba7a` (clean redo).
