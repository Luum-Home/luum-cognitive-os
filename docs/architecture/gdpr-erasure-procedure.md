# GDPR Erasure Procedure for Engram and COS Audit Trails

This procedure implements the ADR-142 privacy surface for flows that use
Engram local storage, Engram Cloud sync, or append-only COS audit rows.

## Scope

- Engram observations in local SQLite.
- Engram Cloud observations when `ENGRAM_CLOUD_AUTOSYNC=1`.
- COS audit rows in `.cognitive-os/runtime/agent-audit-trail.jsonl`.
- Archived audit copies produced by `scripts/cos-audit-archive`.

## Non-goals

- The helper does not delete append-only audit evidence automatically.
- The helper does not bypass legal hold, security incident retention, or SOC 2
  retention requirements.

## Procedure

1. Identify the data subject and the relevant `tenant_id`.
2. Search Engram for observations that contain subject data.
3. Export an evidence snapshot before mutation when legal retention requires it.
4. Delete or redact matching local Engram observations using the Engram MCP
   admin/API tools available in the installed version, or perform a documented
   DB-level erasure under maintenance mode. Current Engram v1.15.x does not
   expose documented local or cloud delete CLI subcommands.
5. If Engram Cloud sync is active, remove the affected observation through the
   cloud server's supported admin/API path for the installed version, or rebuild
   the cloud store from redacted local state. Do not document or automate a
   nonexistent CLI command.

6. Append an erasure audit row with `audit_class: privacy`, the `tenant_id`, the
   observation ID, and the operator/session that performed the erasure.
7. If compressed archives exist, record whether the archive is under legal hold
   or whether a new redacted archive must supersede it.

## Required audit row shape

```json
{
  "timestamp": "2026-05-04T00:00:00Z",
  "event": "observation_erased",
  "audit_class": "privacy",
  "tenant_id": "flow-id-launch-timestamp",
  "observation_id": "123",
  "operator": "maintainer-or-service-account",
  "outcome": "pass"
}
```

The erasure row is retained even when the erased observation content is removed.
It proves that the erasure happened without retaining the erased content.

## Verification

```bash
scripts/cos-audit-archive --dry-run --json
```
