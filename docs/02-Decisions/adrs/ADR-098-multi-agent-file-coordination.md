---
adr: 98
title: Multi-Agent File Coordination
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted/implemented text with explicit partial/deferred scope
partial_remaining: metric (yet to be added) shows >5% blocked-edit rate.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-098 — Multi-Agent File Coordination

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-04-30
**Author**: Maintainer
**Related**: ADR-089 (multi-session git coordination — sibling layer for git index),
ADR-072 (test lane taxonomy — sprint that surfaced the problem),
ADR-088 (provenance trailer)

## Status

Accepted. Implemented and reservation-checked 2026-04-30 (slot reserved via
`scripts/reserve_adr_slot.py` to prevent the same number-collision pattern
ADR-089 documents).

## Context

ADR-089 solves coordination at the **git-index level**: two sessions can't
both run `git commit --only -- file` at the same time and corrupt each
other's staged scope. That layer locks `.cognitive-os/runtime/git-index.lock/`.

ADR-089 does **not** solve **file-level edit coordination**. A real failure
observed during the resource-governance sprint (2026-04-30):

1. Session A (this orchestrator) edited `tests/conftest.py` to add a
   quarantine-injection pass.
2. Session B (parallel window, different agent) reverted the same file via
   `git checkout HEAD --` or equivalent while editing surrounding code.
3. Session A's edit was silently lost. The new `tests/quarantine.yaml` file
   survived (no name collision); modifications to existing files did not.

Three structural failures combined:
- **No file-level lock**: git-coop only covers index ops, not working-tree edits.
- **No introspection registry**: B had no visible way to know A was mid-edit.
- **No response protocol**: even if B detected the conflict, the literature
  on "what should agent B do" is undefined for this codebase.

This ADR adds the missing layer.

## Decision

A **file-level edit-coordination layer** built on the same atomic-mkdir
primitive as ADR-089 git-coop, with a **rich YAML schema** so other
sub-agents can introspect and choose a response.

### Architecture

| Component | File | Role |
|---|---|---|
| Primitive | `scripts/edit-coop.sh` | acquire/release/check/status/heartbeat/release-mine commands. Mkdir atomic, PID-based stale, idempotent re-acquire. |
| Enforcement | `hooks/edit-lock-pre-tool.sh` | PreToolUse[Edit\|Write] hook. Reads tool_input.file_path, calls edit-coop acquire, exits 2 with structured response on conflict. |
| Introspection | `skills/coordination-status/SKILL.md` | Sub-agents invoke before plan to see who is editing what; read-only. |
| Response template | `templates/edit-conflict-response.md` | Boilerplate for sub-agents on conflict (4 options: park / read-only / negotiate / escalate). |
| Tests | `tests/unit/test_edit_coop.py` | 12 behavioral tests: acquire, idempotency, stale, status, bypass, metadata, heartbeat, path safety. |

### Lock metadata schema (rich, by design)

The yaml is **deliberately verbose** so any sub-agent reading it can decide
how to respond without asking the holder:

```yaml
session_id: "<COGNITIVE_OS_SESSION_ID or fallback>"
agent_id: "<COS_AGENT_ID>"
agent_role: "<orchestrator | sub-agent | hook>"
worktree: "<absolute path of git worktree>"
pid: <holding process PID>

target_file: "<repo-relative path>"
intent: "exclusive-edit | shared-read | append-only"
since: "<ISO8601>"
heartbeat: "<ISO8601, refreshed periodically>"
expires_at: "<ISO8601 = since + COS_EDIT_LOCK_TTL>"

purpose: "<free-form: why I'm editing this>"
related_adr: "<ADR-NNN if applicable>"
related_files: ["<other files I'm editing as a unit>"]

allows_concurrent_read: true|false
on_conflict_other_agent_should: "park | retry | negotiate | escalate"
status: "active | parking | released | stale"
```

The schema is extended via `_write_meta()` in edit-coop.sh; consumers should
treat unknown fields as informational and never fail on absence.

### Response protocol (the "data-rich semaphore")

When PreToolUse hook returns exit 2, the agent receives a structured message
with the holder's metadata and four named options:

| Option | When | Action |
|---|---|---|
| **PARK** | Default, non-urgent | Save planned edit as JSON sidecar in `.cognitive-os/runtime/parked-edits/`; switch to non-conflicting work. |
| **READ-ONLY** | Need info, not write | Read the file to inform other work; edit a different file. |
| **NEGOTIATE** | Partial overlap | Write request to `.cognitive-os/runtime/edit-negotiations/<their-session>/<your-session>.yaml`; holder reads on heartbeat. |
| **ESCALATE** | `critical-bugfix` priority only | Set `COS_BYPASS_EDIT_LOCK=1`, proceed; audit-logged. |

### Worktree integration

This layer **complements** worktrees, does not replace them. The recommended
workflow when spawning a second concurrent Claude on the same repo:

```bash
git -C luum-agent-os worktree add ../luum-agent-os--$(date +%s) -b session-$(date +%s)
cd ../luum-agent-os--*
claude    # second session works in physically distinct files
```

With a worktree, file-level conflicts become **physically impossible** between
sessions, and the lock layer becomes belt-and-suspenders insurance for edge
cases (sub-agents within a single session, hooks racing PostToolUse, etc.).

Without a worktree, the lock layer is the **only** defense.

### Stale handling

Identical to ADR-089:
- TTL: `COS_EDIT_LOCK_TTL` (default 1800s = 30 min, longer than git-coop's
  300s because edits are typically longer than git ops)
- Heartbeat: `COS_EDIT_LOCK_HEARTBEAT` (default 300s, refreshed by hook on
  each subsequent Edit/Write)
- Auto-clear: on next acquire, if lock dir exists but PID is dead OR
  heartbeat older than TTL → lock removed, takeover logged

### Bypass

`COS_BYPASS_EDIT_LOCK=1` skips all enforcement. Intended for:
- Critical bugfixes (rare)
- Unit tests of the edit-coop primitive itself
- Emergency recovery when stale detection misfires

Every bypass is logged to `.cognitive-os/runtime/edit-locks-audit.jsonl`
(future hook; currently at the agent's discretion to log).

## Consequences

### Positive

- **Concurrent edits stop silently overwriting each other.** The 2026-04-30
  failure mode is structurally prevented when both sides honor the layer.
- **Sub-agents become coordination-aware.** A sub-agent reading the lock
  YAML can see purpose/related_adr/intent and make informed decisions
  rather than retrying or failing blindly.
- **Sibling to ADR-089.** Same primitive, same idiom, same TTL/stale model.
  Contributors learning one understand the other.
- **Worktree-friendly.** Lock layer is additive; worktrees handle the easy
  case (no shared working tree), locks handle the hard case (shared tree
  with multiple agents).

### Negative

- **Performance cost on every Edit/Write**: ~30ms latency per tool call for
  the PreToolUse hook (mkdir + sed + python json parse). Bounded; survives
  the latency-budget rules.
- **Stale-lock recovery requires correct PID semantics.** A session that
  forks/exits cleanly without releasing leaks a lock until TTL fires (30
  min). Mitigation: `release-mine` on session-end hook (recommended,
  registered separately).
- **Negotiation is advisory.** Holder may ignore negotiation requests.
  This is intentional — automated mediation is a deeper problem (see
  Alternatives rejected: CRDT).

### Neutral

- **Schema is verbose**. ~15 fields per lock. The verbosity is the feature
  (rich introspection); compactness is not a goal here.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| **Bigger TTL on git-coop, hope it covers file edits** | Edits aren't index ops; locking the index doesn't prevent two `Edit` calls on the same file in the working tree. Different problem. |
| **flock(2) on the actual file** | Linux-only, doesn't work on macOS BSD; doesn't survive across processes that don't share the descriptor. |
| **CRDT / Operational Transform** | Sobreingeniería at current agent volume (2-4 concurrent). Becomes attractive at >10 concurrent agents with frequent same-file edits — defer until evidence. See Discussion below. |
| **Sandbox-per-agent (Docker)** | Highest isolation, highest overhead. Recommended for hosted multi-tenant futures, not for local single-user multi-window today. |
| **One-agent-at-a-time discipline** | Doesn't survive a real workflow with one human + multiple agents (sub-agents, hooks, parallel windows). |

### CRDT discussion (carry-forward)

CRDT/OT is the right answer when:
- N >> 4 concurrent writers on the same file
- Edits are stream operations (insert/delete) not file replacements
- Latency of lock acquisition becomes a bottleneck
- Convergence guarantees matter more than serialization order

For this SO at 2-4 concurrent agents editing whole-file replacements, lock +
worktree is the lower-overhead correct choice. Predicted re-evaluation
trigger: when concurrent-agent count crosses 10 OR when a lock-contention
metric (yet to be added) shows >5% blocked-edit rate.

The closest production analog of CRDT-for-code-agents is Replit's
Multiplayer (OT layer over git commits). Anthropic Claude Code, OpenAI
Agents SDK, Devin, Cursor, and CrewAI all use lock-or-sandbox today.

## Verification

```bash
# 1. The primitive works (12 behavioral tests)
.venv/bin/python -m pytest tests/unit/test_edit_coop.py -v

# 2. PreToolUse hook syntax-clean
bash -n hooks/edit-lock-pre-tool.sh

# 3. Acquire/release round-trip from CLI
bash scripts/edit-coop.sh acquire tests/example.py "demo purpose" exclusive-edit
bash scripts/edit-coop.sh check  tests/example.py    # → OWN
bash scripts/edit-coop.sh status                     # → JSON with the lock
bash scripts/edit-coop.sh release tests/example.py
bash scripts/edit-coop.sh check  tests/example.py    # → FREE

# 4. Conflict detection across simulated sessions
COGNITIVE_OS_SESSION_ID=A bash scripts/edit-coop.sh acquire tests/example.py
COGNITIVE_OS_SESSION_ID=B bash scripts/edit-coop.sh check tests/example.py
# expected exit 2, "HELD by session=A"
COGNITIVE_OS_SESSION_ID=A bash scripts/edit-coop.sh release tests/example.py
```

Expected: all 12 unit tests green, all CLI round-trips behave as documented.

## Migration notes

Layered rollout, no schema migration required:

| Layer | Default behavior | Opt-out |
|---|---|---|
| `scripts/edit-coop.sh` | available; not invoked unless something calls it | n/a |
| `hooks/edit-lock-pre-tool.sh` | NOT registered yet — Phase A ships the primitive only | (n/a — opt-in) |
| `skills/coordination-status` | invocable via slash command | n/a |

**Phase A (this commit)**: ship primitive + skill + template + tests.
Hook NOT registered, so behavior is opt-in (sub-agents call edit-coop
directly).

**Phase B (next minor)**: register `edit-lock-pre-tool.sh` as
PreToolUse[Edit|Write] in the standard efficiency profile after observing
zero false-positive rate over a release cycle.

**Phase C (when needed)**: add `release-mine` to session-end hook chain so
lock leaks are bounded by session-end timestamp instead of TTL.

## References

- ADR-089 — multi-session git coordination (the primitive this builds on)
- ADR-088 — provenance trailer (sister coordination layer)
- ADR-072 — test lane taxonomy (the sprint that surfaced this gap)
- `scripts/git-coop.sh` — the atomic-mkdir + PID-stale primitive reused here
- `scripts/edit-coop.sh` — Layer 4 implementation
- `hooks/edit-lock-pre-tool.sh` — PreToolUse enforcement (Phase B)
- `skills/coordination-status/SKILL.md` — introspection skill
- `templates/edit-conflict-response.md` — sub-agent decision template
- `tests/unit/test_edit_coop.py` — 12 behavioral tests
- `.cognitive-os/runtime/edit-locks/` — lock registry path
- 2026-04-30 incident: ADR-098 sprint silently overwritten by parallel session
  (motivating example for this layer)
