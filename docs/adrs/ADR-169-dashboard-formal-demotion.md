---

adr: 169
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - dashboard/ARCHIVED.md
  - hooks/_lib/registration-allowlist.txt
  - cognitive-os.yaml
  - scripts/_lib/settings-driver-claude-code.sh
tier: maintainer
---
# ADR-169 — Dashboard Formal Demotion

## Status

Accepted.

### Addendum — 2026-05-05 (same day)




## Context


>

The `dashboard/` directory was last modified 2026-03-29 (two days after the deprecation decision) and reached approximately 30% of a usable admin surface: app skeleton, two routes (`/rules`, `/skills`), three components, an API client stub.


- 3 of 8 documented mappings were REAL (Singularity inbox, Safety mesh blocks, Retry queue resilience).
- 4 of 8 mappings were PARTIAL: hooks present and tested, but **not registered in `.claude/settings.json`**, so they fired zero times per session.
- 1 of 8 mappings was MISSING (cos packages → skills marketplace; no API method, no hook).
- The dashboard's unique territory (rules / skills / stat-card views) was real but small.


## Decision

1. **`dashboard/` is formally demoted to archived.** A `dashboard/ARCHIVED.md` notice is added. Files are preserved on disk (not deleted) so the demotion is reversible if the falsifiable claim below fires.
   - `cognitive-os.yaml > harness.hooks` gains six entries.
   - `hooks/_lib/registration-allowlist.txt` is extended with five new entries.
   - `scripts/_lib/settings-driver-claude-code.sh` adds the six hooks to its SessionStart, PostToolUse Agent, and Stop projection groups.
   - All six hooks project as `async: true` so they never block the session.

## Acceptance Criteria

2. `dashboard/ARCHIVED.md` exists and is the first file a reader of `dashboard/` should encounter.
3. Nothing else in the repo imports from `dashboard/app`, `dashboard/components`, or `dashboard/lib`. (Verified pre-commit: zero matches under `docs/`, `scripts/`, `hooks/`, `lib/`, `packages/`, `rules/`.)
5. `bash -n scripts/_lib/settings-driver-claude-code.sh` passes.
6. `python3 -c "import yaml; yaml.safe_load(open('cognitive-os.yaml'))"` parses without error after the insertion.

## Border Cases

- **Someone clones the repo and runs the dashboard.** They will see `ARCHIVED.md` as the most recently-touched file and the deprecation notice. `node_modules/` and `.next/` are gitignored, so they will need to `npm install` before anything could run — at which point they should read the notice and stop.

## Consequences

**Positive.**

- The architectural intent declared on 2026-03-27 is finally enacted. The deprecation is no longer maintainer cache — it is filesystem-visible.
- The 2026-05-05 audit's falsifiable claim is preserved as a tripwire: if the integration goes silent, the demotion is revisited.

**Negative / trade-offs.**


## Operational Guide

### What changes for the operator

Before this ADR, the `dashboard/` directory was present with no clear signal of its status — only maintainer cache knowledge indicated it was deprecated. Hooks that should have been wiring lifecycle events were present on disk but not registered in `.claude/settings.json`, so they fired zero times per session.

After this ADR:

| Surface | Before | After |
|---|---|---|
| `dashboard/` directory | No demotion signal; appeared active | `dashboard/ARCHIVED.md` is the first visible file; demotion is filesystem-visible |
| Six unregistered hooks | Present but never firing | Registered in `cognitive-os.yaml`, `hooks/_lib/registration-allowlist.txt`, and projected via `scripts/_lib/settings-driver-claude-code.sh` |
| Dashboard imports | Potentially imported by other code | Zero imports verified under `docs/`, `scripts/`, `hooks/`, `lib/`, `packages/`, `rules/` |

### What this answers (and what it doesn't)

**Answers:**
- "Is the dashboard still supported?" — No. `dashboard/ARCHIVED.md` is the canonical signal.
- "Were the hooks that were supposed to fire actually wired?" — After this ADR, yes: the six hooks are registered as `async: true` in the SessionStart, PostToolUse Agent, and Stop groups.
- "Can the demotion be reversed?" — Yes: `dashboard/` is preserved on disk (not deleted) and the falsifiable claim section defines exactly what would trigger a revisit.

**Does not answer:**
- "What the dashboard was building toward" — see ADR-132 and ADR-133 for the architectural context, and `docs/runbooks/run-cos-in-docker.md` for the external-evaluator path that replaced it.

### Daily operational pattern

No daily action required. The demotion is a one-time decision. Operators should:
1. Treat any code referencing `dashboard/app`, `dashboard/components`, or `dashboard/lib` as importing from an archived surface — those paths must be removed or redirected.
2. If the falsifiable claim conditions break (integration goes silent for a defined period), revisit this ADR per §Falsifiable Claim.

### Reading guide for cold readers

1. Read `dashboard/ARCHIVED.md` first — it is the in-tree demotion notice.
2. Read §Decision to understand which six hooks were wired and where they were registered.
3. Read §Falsifiable Claim to understand what conditions would require revisiting the demotion.
4. Read ADR-133 (expansion-without-monsterization) and ADR-172 (multi-surface UI architecture) for the broader UI doctrine that replaced the dashboard's intended role.

## Alternatives rejected

- **Delete `dashboard/` outright.** Rejected: loss of architectural exploration evidence; demotion should be reversible if the falsifiable claim fires.

## Falsifiable Claim

The dashboard demotion holds while **all** of the following remain true. If any breaks for the indicated duration, this ADR must be revisited:


If conditions 1–3 hold for one calendar year, the demotion is judged correct and `dashboard/` may be deleted in a follow-up ADR.

## Cross-references

- [`dashboard/ARCHIVED.md`](../../dashboard/ARCHIVED.md) — the in-tree demotion notice.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — the maintainer-cache transferability frame this ADR addresses.
- [ADR-133](ADR-133-expansion-without-monsterization.md) — lab-first promotion contract; the wiring-not-resurrection path satisfies its requirements.
- [`docs/runbooks/run-cos-in-docker.md`](../runbooks/run-cos-in-docker.md) — the external-evaluator path that does not depend on the dashboard.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

