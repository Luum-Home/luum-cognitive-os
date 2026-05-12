---

adr: 141
title: Engram Cloud as Cross-Instance Replication Transport
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-engram-cloud-enroll
tier: maintainer
tags: [memory, engram, cloud, replication, air-gap, cloud-flows, sync]
---

# ADR-141: Engram Cloud as Cross-Instance Replication Transport

## Status

**Accepted — Implemented** as the replication strategy for Engram observations across COS instances. Local SQLite remains authoritative. Cloud is replication-only.

This ADR is **not** an adoption decision for Engram — Engram is already integrated (binary, `lib/engram_client.py`, `lib/engram_http_client.py`, `mcp-server/cos_mcp.py`, `packages/engram-sync/`). This ADR wires the upstream `engram cloud` feature (shipped April 2026) into the COS runtime without replacing any existing path.

## Context

COS workers and the maintainer machine currently share no live memory channel. The existing `packages/engram-sync/` package and `scripts/engram-sync.sh` implement git-jsonl sync: observations are exported to `.engram/exports/{project}.jsonl`, committed to the repo, and imported by other machines via `git pull`. This works for cross-device maintainer sync and doubles as an air-gap transport.

The upstream Engram project (Gentleman-Programming) shipped the `engram cloud` feature in April 2026 across branches `feat/integrate-engram-cloud`, `feat/memory-conflict-surfacing-cloud-sync`, and `fix/cloud-dashboard-mutation-read-model`. The upstream feature provides:

- `engram cloud config / enroll / upgrade` — bootstrap and token management
- `engram sync --cloud` — push project-scoped observations to the cloud server
- `engram cloud serve` — self-hosted cloud server on `:8080` with bearer-token + JWT auth
- Autosync via `ENGRAM_CLOUD_AUTOSYNC=1` + `ENGRAM_CLOUD_TOKEN` + `ENGRAM_CLOUD_SERVER`
- Conflict surfacing: `mem_save` returns `judgment_required: true` + per-candidate `judgment_id`; resolved via `mem_judge`

The [ADR-136](ADR-136-cross-instance-learning-runway.md) runway already introduced `cos-engram-bundle` and `cos-engram-import-propose` as portable evidence primitives. The `engram cloud` feature is the live-sync complement: bundle/import handles async evidence; cloud sync handles near-real-time worker↔central replication.

The [DX-first cloud flow bootstrap plan](../architecture/dx-cloud-flow-bootstrap-plan.md) requires cross-machine Engram daemon discovery as a named prerequisite for promoting a flow beyond `lab`. This ADR is the mechanism that satisfies that prerequisite.

## Decision

### 1. Three operating modes — no deprecation

COS supports three Engram sync modes simultaneously. No mode deprecates another.

| Mode | Trigger | Transport | Use case |
|---|---|---|---|
| `local-only` | `ENGRAM_CLOUD_AUTOSYNC` unset | None | Air-gap, offline maintainer, default for new installs |
| `git-jsonl` | `scripts/engram-sync.sh` invoked | Git + JSONL | Cross-device maintainer sync, air-gap fallback, always available |
| `engram-cloud` | `ENGRAM_CLOUD_AUTOSYNC=1` + token set | HTTP to `:8080` bearer-JWT | Worker↔central live replication |

`git-jsonl` mode (`scripts/engram-sync.sh`) is **not deprecated** and **not modified** by this ADR. It remains the recommended fallback for any deployment where `engram cloud serve` is unavailable or the operator prefers not to run a cloud server.

### 2. Local SQLite remains authoritative

The Engram daemon's local SQLite database at `~/.engram/engram.db` (or `ENGRAM_DB` override) is the single source of truth. Cloud sync is append-only replication: the cloud server stores copies; it does not overwrite the local DB. A worker that loses connectivity to the cloud server continues operating against its local DB; observations are queued for sync when connectivity is restored (upstream autosync behaviour).

### 3. Tenant isolation

Worker instances MUST set `ENGRAM_CLOUD_ALLOWED_PROJECTS` on the cloud server to restrict which project namespaces a given token may write. COS adds a client-side enforcement layer: before pushing an observation, `lib/engram_http_client.py` checks that the observation's `project` field matches the token's allowed projects. Mismatched observations are dropped with a warning logged to `.cognitive-os/runtime/agent-audit-trail.jsonl`.

The upstream `engram sync --cloud --all` flag (pushes all projects regardless of scope) is **disabled** in COS usage. The COS wrapper always passes the project scope explicitly.

### 4. Auth: project-scoped bearer tokens

Workers use project-scoped bearer tokens distinct from the maintainer's personal credentials. Token lifecycle:

- Provisioned by the maintainer via `scripts/cos-engram-cloud-enroll` (see §5).
- Injected into the worker environment as `ENGRAM_CLOUD_TOKEN`; never hardcoded in scripts.
- Scoped to one `ENGRAM_CLOUD_ALLOWED_PROJECTS` value per token.
- Rotated by re-running `scripts/cos-engram-cloud-enroll --rotate`.

The maintainer's personal token (from `engram cloud enroll` run on the maintainer machine) is never shared with workers.

### 5. Bootstrap wrapper: `scripts/cos-engram-cloud-enroll`

A thin COS wrapper around `engram cloud enroll / upgrade` that:

1. Calls `engram cloud config --server "$ENGRAM_CLOUD_SERVER"` to set the server endpoint.
2. Calls `engram cloud enroll` with the project scope.
3. Prints the resulting token as `ENGRAM_CLOUD_TOKEN=<value>` for capture into CI secrets or `.env` files (never persisted by the script itself).
4. Optionally calls `engram cloud upgrade` when a new Engram binary is available.

The wrapper adds nothing beyond what `engram cloud enroll` provides except for the project-scope enforcement and the output format that matches the worker environment variable convention from ADR-139.

### 6. Existing engram-sync hooks: additive `--cloud` flag

The `packages/engram-sync/hooks/` scripts that currently invoke `engram-sync.sh` are modified to conditionally append `--cloud` when `ENGRAM_CLOUD_AUTOSYNC=1` is set:

```bash
SYNC_FLAGS=""
[ "${ENGRAM_CLOUD_AUTOSYNC:-0}" = "1" ] && SYNC_FLAGS="--cloud"
"$PROJECT_DIR/scripts/engram-sync.sh" $SYNC_FLAGS
```

This is the **only** change to the existing sync hooks. The git-jsonl export continues to run regardless of whether `--cloud` is appended; the `--cloud` flag is additive, not a replacement.

### 7. Conflict surfacing reuses the propose-only contract

When `mem_save` returns `judgment_required: true` (upstream conflict-surfacing mechanic), the COS runtime treats it as equivalent to the propose-only contract from ADR-134 / ADR-135 / ADR-138: the agent surfaces the conflict to the operator, the operator resolves it via `mem_judge`. No new mechanism is introduced.

The `judgment_id` from each conflicting candidate is used to call `mem_judge` once per candidate. The maintainer or automated triage resolves the conflict; resolution is logged to `.cognitive-os/runtime/agent-audit-trail.jsonl` with event type `engram_conflict_resolved`.

### 8. Audit bridge to ADR-142

Every cloud sync operation appended to the canonical audit JSONL (`.cognitive-os/runtime/agent-audit-trail.jsonl`) as follows:

```json
{
  "ts": "<ISO-8601>",
  "event": "engram_cloud_sync",
  "direction": "push|pull",
  "project": "<project-name>",
  "observation_count": 0,
  "conflicts_surfaced": 0,
  "mode": "local-only|git-jsonl|engram-cloud"
}
```

This row is the bridge ADR-142 uses for its compliance audit surface. A deployment in `local-only` mode still appends rows with `mode: local-only` and `observation_count: 0`, confirming the mode is active and intentional rather than simply absent.

### 9. `engram_project_scope` in the flow contract

The flow contract schema (ADR-138) gains an `engram_project_scope` field (see §Schema extension) that names the project namespace the flow's workers write to. Cloud sync pushes observations only within this scope; the audit row carries the scope for compliance correlation.

## Schema extension to ADR-138

```yaml
engram_project_scope: stable project slug matching ENGRAM_CLOUD_ALLOWED_PROJECTS
air_gapped_compatible: true|false  # can the flow operate in local-only mode?
```

`air_gapped_compatible: false` is a gate: flows that require live cloud sync cannot be deployed in air-gapped environments. This field is consumed by ADR-142's air-gap surface definition.

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| [ADR-071](ADR-071-engram-lifecycle-evolution.md) | **Extends.** ADR-071 governs Engram daemon lifecycle. Cloud sync adds a replication layer on top; the daemon lifecycle is unchanged. |
| [ADR-136](ADR-136-cross-instance-learning-runway.md) | **Complements.** Bundle/import (ADR-136) is async evidence exchange; cloud sync is near-real-time replication. Both coexist. |
| [ADR-138](ADR-138-flow-contract-schema.md) | **Extended.** Two new fields added: `engram_project_scope`, `air_gapped_compatible`. |
| [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) | **Follows.** `ENGRAM_CLOUD_TOKEN` is managed under the caller-supplied credential model; never shared across instances. |
| [ADR-140](ADR-140-cross-os-containerized-deployment.md) | **Composes with.** The `cos-engram-proxy` sidecar in the Compose stack is the cloud server when self-hosted. |
| [ADR-142](ADR-142-compliance-audit-air-gapped-surface.md) | **Feeds.** The audit bridge rows (§8) are consumed by ADR-142's compliance surface. |

## Acceptance Criteria

1. `scripts/cos-engram-cloud-enroll` exists, is executable, and calls `engram cloud enroll` with project-scope enforcement. It does not embed any token value.
2. `packages/engram-sync/hooks/` scripts conditionally pass `--cloud` when `ENGRAM_CLOUD_AUTOSYNC=1`, and do not modify the git-jsonl export path.
3. `git-jsonl` mode (`scripts/engram-sync.sh` without `--cloud`) continues to work with `ENGRAM_CLOUD_AUTOSYNC` unset.
4. A cloud sync operation appends a row to `.cognitive-os/runtime/agent-audit-trail.jsonl` with the fields defined in §8.
5. The first flow's `flow_contract.yaml` includes `engram_project_scope` and `air_gapped_compatible`.

## Border Cases

- **No `engram cloud serve` available.** `ENGRAM_CLOUD_AUTOSYNC` is unset; mode is `local-only` or `git-jsonl`. No error; audit rows confirm the mode.
- **Conflict in the same observation key from two workers.** `mem_save` returns `judgment_required: true`. The COS runtime logs the conflict and surfaces it to the operator. Workers do not retry the conflicting write autonomously.
- **Worker loses connectivity mid-session.** Upstream autosync queues the push; local SQLite continues authoritative. The audit row for the failed push is written with an `error` field when connectivity is restored and the queue drains.
- **`engram sync --cloud --all` called by an operator directly.** COS does not block direct CLI usage; the restriction applies only to COS-orchestrated sync calls from hooks and flow scripts.
- **Air-gapped deployment.** `air_gapped_compatible: true` in the flow contract. The flow uses `git-jsonl` or `local-only` mode. No cloud server required.

## Consequences

**Positive.**

- Workers share observations with the central instance in near-real-time without polling a git repo or exchanging bundles manually.
- The git-jsonl path survives as an air-gap fallback, so no deployment is forced to depend on a cloud server.
- Conflict surfacing reuses the propose-only contract already understood by maintainer and agents; no new mechanic is introduced.
- The audit bridge (§8) connects Engram sync events to the existing JSONL audit trail, making cloud memory state inspectable without a dashboard.

**Negative / risk.**

- `engram cloud serve` is a new operational dependency when `engram-cloud` mode is active. The operator is responsible for availability; COS does not manage the server lifecycle.
- Project-scoped token management adds operational overhead. `scripts/cos-engram-cloud-enroll` minimises this; token rotation is manual.
- The upstream `engram cloud` feature is April 2026 vintage. Breaking changes in the upstream API require updates to `scripts/cos-engram-cloud-enroll` and potentially to `lib/engram_http_client.py`.

**Of not making this commitment.**

- Workers must rely on bundle/import (ADR-136) for cross-instance memory, which is async and manual. The cross-machine Engram discovery prerequisite in the bootstrap plan remains unmet, blocking flow promotion beyond `lab`.

## Cross-references

- [ADR-071](ADR-071-engram-lifecycle-evolution.md) — Engram daemon lifecycle; unchanged.
- [ADR-136](ADR-136-cross-instance-learning-runway.md) — bundle/import; async complement to live sync.
- [ADR-138](ADR-138-flow-contract-schema.md) — flow contract schema; new fields defined here.
- [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) — credential posture; `ENGRAM_CLOUD_TOKEN` follows caller-supplied model.
- [ADR-140](ADR-140-cross-os-containerized-deployment.md) — Compose stack; `cos-engram-proxy` sidecar.
- [ADR-142](ADR-142-compliance-audit-air-gapped-surface.md) — compliance surface; consumes audit bridge rows.
- `lib/engram_client.py`, `lib/engram_http_client.py` — existing Engram wrappers.
- `packages/engram-sync/` — existing git-jsonl sync package; hooks modified additively.
- `scripts/engram-sync.sh` — existing sync script; unchanged except `--cloud` passthrough.
- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — cross-machine Engram discovery prerequisite this ADR satisfies.

## Operational Guide

### What changes for the operator

Before this ADR, cloud workers had no live memory channel to the
maintainer machine. Cross-instance memory required manual bundle/import
cycles via `scripts/engram-sync.sh` (git-jsonl mode), which is async
and requires git push/pull.

After this ADR, three Engram sync modes coexist; no mode deprecates
another:

| Mode | When to use |
|---|---|
| `local-only` | Default. Air-gap, offline, or new installs. |
| `git-jsonl` | Cross-device maintainer sync or air-gap fallback. Always available. |
| `engram-cloud` | Worker↔central live replication. Requires `engram cloud serve`. |

To enable cloud mode:
```bash
export ENGRAM_CLOUD_AUTOSYNC=1
export ENGRAM_CLOUD_TOKEN=<project-scoped-token>
export ENGRAM_CLOUD_SERVER=http://localhost:8080
bash scripts/cos-engram-cloud-enroll  # provision project-scoped token
```

The git-jsonl export continues to run even when `--cloud` is active;
cloud sync is additive.

### What this answers (and what it doesn't)

**Answers:**
- "Is cloud sync active for this session?" — Check
  `agent-audit-trail.jsonl` for rows with `event: engram_cloud_sync`
  and `mode: engram-cloud`. A row with `mode: local-only` and
  `observation_count: 0` confirms cloud sync is intentionally off.
- "Did a conflict occur during sync?" — Look for
  `event: engram_conflict_resolved` in the audit trail. The row
  carries the judgment outcome.
- "Is this flow air-gap compatible?" — Read `air_gapped_compatible`
  in the flow contract. `false` means live cloud sync is required.

**Does not answer:**
- `engram cloud serve` availability or uptime. COS does not manage
  the cloud server lifecycle; the operator is responsible.
- Token rotation schedule. Rotate by re-running
  `scripts/cos-engram-cloud-enroll --rotate`. COS does not enforce a
  rotation cadence.

### Daily operational pattern

1. **Air-gapped / default**: nothing to do. Git-jsonl sync runs on
   session-end hooks automatically; cloud sync is inactive.
2. **Cloud-enabled**: start `engram cloud serve` (or point to a
   remote server via `ENGRAM_CLOUD_SERVER`), then set
   `ENGRAM_CLOUD_AUTOSYNC=1` in the worker environment.
3. After a sync session, verify observations are replicating:
   ```bash
   grep "engram_cloud_sync" .cognitive-os/runtime/agent-audit-trail.jsonl | tail -5
   ```
4. Conflict resolution: if `mem_save` returns `judgment_required:
   true`, the runtime surfaces the conflict via `mem_judge` calls.
   No manual intervention required for the happy path.

### When sources disagree

If a worker's observations are not appearing on the central instance:

1. Check `ENGRAM_CLOUD_AUTOSYNC` and `ENGRAM_CLOUD_TOKEN` are set in
   the worker environment.
2. Verify the worker's `ENGRAM_CLOUD_ALLOWED_PROJECTS` matches the
   flow's `engram_project_scope`.
3. Check the audit trail for `direction: push` rows with an `error`
   field — this indicates a queued push that failed. Connectivity
   restored → the queue drains automatically.
4. If cloud is unavailable, fall back to git-jsonl:
   `bash scripts/engram-sync.sh` (no `--cloud` flag).

The local SQLite database (`~/.engram/engram.db`) is always
authoritative. The cloud is replication-only; it does not overwrite local.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_139_141_142_cloud_surfaces.py tests/unit/test_cos_engram_cloud_enroll_and_audit_archive.py -q
```

## Implementation Evidence

- Implemented in `scripts/cos-engram-cloud-enroll`: project-scoped wrapper around `engram cloud config/enroll/upgrade`, with dry-run/JSON modes and audit-trail rows.
- Implemented in `scripts/engram-sync.sh`: explicit `--cloud` mode invokes `engram sync --cloud --project "$SCOPE"` and never calls `--cloud --all`.
- Implemented in `packages/engram-sync/hooks/engram-auto-sync.sh`: `ENGRAM_CLOUD_AUTOSYNC=1` adds cloud sync after the existing git-jsonl export path.
- Implemented in `docker/cos-worker/docker-compose.yml`: local `engram-cloud` profile with Postgres/pgvector database and `cos-engram-cloud` service running `engram cloud serve`.
- Implemented in `scripts/cos-engram-cloud-docker-smoke`: repeatable local proof that starts the Compose profile, enrolls `luum-agent-os` and `cos-consumer-e2e-drill`, saves one observation per project using a temporary Engram home, syncs each project through `scripts/engram-sync.sh --cloud`, and verifies project-scoped rows in `cloud_chunks`.
- Validated by `tests/audit/test_adr_139_141_142_cloud_surfaces.py`, `tests/unit/test_cos_engram_cloud_enroll_and_audit_archive.py`, and optional testcontainers lane `tests/integration/test_engram_cloud_docker.py`.
- Manual proof documented in `docs/09-Quality/manual-tests/engram-cloud-docker-sync.md`.
