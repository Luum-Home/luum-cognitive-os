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

