---

adr: 184
title: Manager-of-Managers Daemon — Authoritative Single-Writer for Critical Surfaces
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
extends: [ADR-163]
implementation_files:
  - scripts/cosd                            # existing minimal control-plane wrapper; extend for daemon mode
  - scripts/cos_daemon.py
  - lib/intent_arbiter.py
  - hooks/cosd-intent-submit.sh
  - tests/integration/test_cosd_daemon.py
tier: maintainer
tags: [concurrency, daemon, governance, postmortem-2026-05-05, refines-ADR-163]
---
# ADR-184: Manager-of-Managers Daemon — Authoritative Single-Writer for Critical Surfaces

## Status

**Accepted.** First implementation landed as a local file-queue daemon for ADR identity arbitration. Long-horizon refinement of ADR-163 (cos-instance-installer).
ADR-184 generalizes the daemon role from instance-provisioning into a
**single-writer authority** for COS-critical paths, addressing the
structural concurrency gap exposed by the
2026-05-05 cross-session collision.

This ADR is intentionally **separate** from the ADR-182/183/185 v1 critical
path. Those ADRs are hook/library contracts that run in today's IDE-embedded
session model. ADR-184 now ships a local `cosd` file-queue daemon for ADR
identity arbitration; broader registry/settings/release ownership remains
future expansion.

## Context

ADR-182 (branch ownership lock) and ADR-183 (cross-session event log)
together prevent the most damaging collisions and surface peer activity.
But they remain *peer-to-peer* coordination layers: each session is
still a sovereign writer to the filesystem and git.

Some paths in COS are sensitive enough that *no* multi-writer pattern
is acceptable. Examples:

- `manifests/agentic-primitive-registry.lock.yaml` (sha256-locked
  registry — race produces corrupt lock).
- ADR sequence numbering (tonight's ADR-171/173/179 collisions
  demonstrate the risk).
- `.claude/settings.json` (generated; concurrent regeneration races).
- Release tags and version files.

For these paths, the architecturally clean solution is a **daemon
process** that holds exclusive write access. Other processes submit
*intent* and await arbitration.

ADR-163 already declares an instance installer with daemon-like
properties (`scripts/cos-instance-init`, separation from
`scripts/cos_init.py`). ADR-184 extends that role.

## Decision

Introduce **`cosd`** — the COS daemon — as an opt-in long-running
process with the following responsibilities and contract:

### Responsibilities

The daemon is the authoritative writer for:

1. **ADR sequence and ownership**: anyone wanting a new ADR number, ADR
   filename, or ADR tombstone authorization submits intent; daemon assigns or
   rejects atomically.
2. **`manifests/agentic-primitive-registry.lock.yaml`**: daemon
   serializes mutations.
3. **`.claude/settings.json`** regeneration: daemon owns the projection
   pipeline. Sessions request a regen; daemon produces it.
4. **Release tag / version bump**: daemon is the only path that updates
   `VERSION`, `pyproject.toml` version, and pushes tags.
5. **Cross-instance federation** (future, ADR-136 territory).

Other paths (skill files, hook scripts, test files, reports, etc.) remain
free-write by sessions; the daemon is not a bottleneck for routine work.

ADR prose remains session-authored, but ADR identity is daemon-arbitrated:

- number reservation;
- canonical filename;
- tombstone authorization;
- rename from reserved filename to final filename;
- rejection of tombstones for active or claimed ADR numbers.

This distinction matters because the incident was not only "two sessions picked
the same next number"; it was also "one session replaced active semantic
ownership with a generic tombstone." `cosd` must arbitrate that ownership layer
even if it does not write the entire ADR body.

### Contract

Sessions interact with the daemon via:

- **Submission**: write a JSON intent to `.cognitive-os/cosd/intents/<id>.json`.
- **Polling or notification**: daemon writes
  `.cognitive-os/cosd/results/<id>.json` when arbitrated.

Schema for an intent (example: ADR number request):

```json
{
  "id": "intent-2026-05-05-184-request",
  "kind": "adr-number-request",
  "session_id": "1778012502-40406-0062edf8",
  "submitted_at": "2026-05-05T23:55:00Z",
  "context": {
    "topic": "rules auto-derive routing",
    "filename_stem": "rules-auto-derive-routing"
  }
}
```

Schema for an ADR tombstone request:

```json
{
  "id": "intent-2026-05-05-184-tombstone",
  "kind": "adr-tombstone-request",
  "session_id": "1778012502-40406-0062edf8",
  "submitted_at": "2026-05-05T23:58:00Z",
  "context": {
    "adr_number": 171,
    "reason": "Rejected integration surface removed",
    "candidate_filename": "ADR-171-tombstone.md"
  }
}
```

The daemon grants the request only if no active ADR file or live claim owns the
number. If the number is active, the daemon returns `status=rejected` with the
owning filename or claim holder.

Result:

```json
{
  "id": "intent-2026-05-05-184-request",
  "status": "granted",
  "decision": {
    "adr_number": 179,
    "reserved_filename": "ADR-179-rules-auto-derive-routing.md"
  },
  "decided_at": "2026-05-05T23:55:00.123Z"
}
```

### Daemon liveness

`cosd` runs as a per-machine background process started by the operator
(`bash scripts/cosd start`). If absent, sessions degrade to ADR-182 +
ADR-183 mode (peer coordination only). The daemon is not required for
routine work; it is required for the specific high-stakes surfaces it
owns.

ADR-184 v1 is intentionally narrow. The active protection layer is now:

- ADR-182 branch ownership locks;
- ADR-183 cross-session event visibility;
- ADR-185 directed audit/implementation messages;
- local guards for ADR numbering/tombstone workflows;
- `cosd` arbitration for ADR number reservation and tombstone authorization.

The daemon does **not** yet arbitrate every critical surface listed above.
Registry-lock, settings-regeneration, and release/version intents must be added
as separate intent kinds with source-level proof and tests.

### Failure modes

If the daemon crashes mid-arbitration:

- Existing intent files remain on disk.
- A supervisor (`launchd`/`systemd` socket activation, or a simple
  cronjob) restarts it.
- On restart, the daemon replays unprocessed intents.
- Idempotency: each intent has a unique `id`; re-processing produces
  the same result.

If the daemon is intentionally not running:

- Operator-only escape hatch: env var
  `COSD_BYPASS=1` allows direct write, with a stderr warning logged
  to engram.

## Acceptance Criteria

1. `scripts/cosd` (executable) exists with `start`, `stop`, `status`
   sub-commands.
2. `lib/intent_arbiter.py` exposes the arbitration loop with at least
   two handled intent kinds (`adr-number-request`, `adr-tombstone-request`)
   verifiable
   end-to-end.
3. `hooks/cosd-intent-submit.sh` is invoked when a session needs to
   request a critical write; the hook is documented as a wrapper
   sessions call from inside their workflow.
4. Tests: integration test starts a daemon in the test environment,
   submits two competing ADR-number intents from two synthetic
   sessions, asserts that they are assigned distinct numbers atomically,
   validates that no two intents receive the same number, and verifies that a
   tombstone request for an active ADR number is rejected.
5. Operator can run `bash scripts/cosd status` and see: PID, uptime,
   intent queue depth, last 10 arbitrations.
6. Daemon respects a kill-switch; can be stopped without losing intent
   files.

## Border Cases

- **No daemon running, session needs an ADR number or tombstone**: degraded
  mode. Session uses ADR-182/183/185 plus the local
  `session_coordination.py` and `adr_tombstone.py` guards. Direct
  directory-listing fallback is warning-only and must not tombstone an active
  ADR number without explicit operator override.
- **Daemon hangs**: TTL on intents (e.g. 60 s); session retries or
  escalates.
- **Operator runs cosd on a different machine** (future, federation):
  out of scope for this ADR; ADR-136 territory.
- **Intent file from a long-dead session**: daemon skips intents older
  than 1 hour and emits a "skipped-stale" log entry.

## Consequences

### Positive

- Tonight's ADR-171/173/179 collisions become structurally impossible:
  any agent or session wanting to author or tombstone an ADR submits an intent;
  daemon assigns a fresh number or rejects a tombstone that would erase active
  semantic ownership.
- The `agentic-primitive-registry.lock.yaml` race is eliminated.
- Future federation (ADR-136) gains a natural integration point.
- Refines ADR-163's instance-installer into a richer single-writer
  authority.

### Negative

- Significant new infrastructure (~2-4 weeks of work to a usable
  state).
- Daemon process management complexity (start/stop/restart).
- Some operations gain latency (round-trip via daemon).
- Adds a new "must-be-running" agentic primitive for critical surfaces;
  bypass via `COSD_BYPASS=1` exists but introduces an audit gap.
- Per-machine only in v1; cross-machine in a future ADR.

### Neutral

- The daemon is opt-in. Existing ADR-182 and ADR-183 protect against
  the most common conflicts without it.
- Most COS work (skills, hooks, tests, reports) does not require daemon
  arbitration; the daemon is a narrow authority over a small surface.

## Operational Guide

### What changes for the operator

Before this ADR, ADR number assignment, ADR tombstone authorization, and
`agentic-primitive-registry.lock.yaml` mutations were peer-to-peer: each
session guarded its own writes with ADR-182/183, but two sessions could
still collide when both needed the next ADR number at the same time.

After this ADR, `cosd` is the single writer for these high-stakes
surfaces. Sessions submit intents and wait for arbitration; the daemon
assigns or rejects atomically.

For the operator this means:

- Start the daemon once per machine: `bash scripts/cosd start`.
- Check status at any time: `bash scripts/cosd status` (shows PID,
  uptime, intent queue depth, last 10 arbitrations).
- Stop it gracefully: `bash scripts/cosd stop` (intent files remain on
  disk and are replayed on restart).
- If the daemon is not running, sessions fall back to ADR-182/183/185
  peer coordination plus local guards. Direct ADR-number reservation
  still warns (via stderr) that daemon arbitration is unavailable.

The escape hatch `COSD_BYPASS=1` allows a direct write without daemon
arbitration; it logs a warning to Engram. Use only when `cosd` is
unavailable and the operator accepts the collision risk.

### What this answers (and what it doesn't)

**Answers:**
- "Who assigned ADR number X?" — Query the daemon intent log:
  `bash scripts/cosd status` → last 10 arbitrations, or inspect
  `.cognitive-os/cosd/results/` for granted intents.
- "Why was a tombstone request rejected?" — The daemon rejects if an
  active ADR file or live claim owns the number. The result file at
  `.cognitive-os/cosd/results/<intent-id>.json` carries `status:
  rejected` and the owning filename.
- "Is the daemon running?" — `bash scripts/cosd status` exits 0 if
  alive; non-zero if not running.

**Does not answer:**
- Cross-machine coordination. `cosd` is per-machine in v1. ADR-136
  federation is the future cross-machine path.
- Whether the ADR *prose* is correct. `cosd` arbitrates identity
  (number, filename, tombstone authorization); content review is the
  operator's concern.

### Daily operational pattern

1. `bash scripts/cosd start` at the beginning of a multi-session work
   day (or add it to a login script).
2. Sessions that need an ADR number call `hooks/cosd-intent-submit.sh`;
   the hook submits the intent and polls for the result. No operator
   action required in the happy path.
3. If a session gets `status: rejected`, it means another session holds
   the claim. Read the rejection reason and coordinate with the other
   session.
4. At end of day: `bash scripts/cosd stop`. Intent files are retained;
   restart resumes from the queue.

### When sources disagree

If a session claims "ADR-N was granted to me" but the daemon result file
shows a different session or a rejection:

1. The daemon result file at `.cognitive-os/cosd/results/<intent-id>.json`
   is authoritative.
2. If the result file is absent (daemon crashed mid-arbitration), restart
   `cosd`; it replays unprocessed intents from `.cognitive-os/cosd/intents/`.
3. If two sessions both have a granted result for the same ADR number
   (should not happen but possible if `COSD_BYPASS=1` was used), the
   session that committed first in git history takes precedence; the other
   must re-request a number.

## Alternatives rejected

- **Add cosd responsibilities to git pre-receive hook**: only catches
  pushes; many of the contended surfaces (lock manifest regen,
  settings projection) happen pre-commit.
- **Use an existing service** (e.g. Engram daemon, Phoenix server) as
  the arbiter: violates separation of concerns. Engram is a memory
  layer; Phoenix is observability. Critical-surface arbitration
  deserves its own process.
- **Distributed consensus** (Raft, etcd): massive overkill for
  per-machine coordination. Rejected for v1; reconsiderable when
  ADR-136 federation matures.
- **Make every session sequential** (lock file forces all sessions to
  serialize): kills the multi-session productivity the operator gains
  from running parallel IDE tabs. Rejected.

## Falsifiable Claim

ADR-184 is correct if, in a 180-day window after daemon adoption: (a)
zero ADR number collisions are observed, (b) zero
`agentic-primitive-registry.lock.yaml` corruption events are observed,
(c) `.claude/settings.json` regeneration races become 0 % of
incidents, and (d) the daemon's mean intent-arbitration latency stays
under 200 ms at 99th percentile.

If any of (a)–(c) happen even once with the daemon running and
healthy, the design is broken and ADR-184 must be revisited. If (d) is
exceeded, a performance optimization or alternative architecture is
required.

## Cross-References

- `docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md` —
  origin incident.
- ADR-163 — cos-instance-installer (precursor; ADR-184 extends).
- ADR-182 — branch ownership lock (independent; works with or without
  cosd).
- ADR-183 — cross-session event log (cosd consumes this log to inform
  arbitration).
- ADR-185 — directed audit findings queue (cosd consumes blocking findings
  before granting critical writes).
- `docs/04-Concepts/architecture/cross-session-coordination-ledger.md` — local degraded
  coordination path before cosd is available.
- ADR-136 — cross-instance learning runway (cosd is the per-machine
  unit that ADR-136 federation interconnects).
- ADR-088 — commit_provenance (cosd commits carry their own provenance
  marker `X-COS-Origin: kind=cosd`).

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

