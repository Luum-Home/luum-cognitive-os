---
type: quality-synthesis
source: docs/09-Quality/manual-tests/engram-cloud-docker-sync.md
provenance: "Manual test proving the ADR-141 Engram Cloud sync path end-to-end via local Docker Compose, without touching the operator's real Engram home directory."
---

## What it is
A manual test proving the ADR-141 Engram Cloud path (multi-scope sync of Engram observations to a Postgres-backed cloud server) works end-to-end using a local Docker Compose profile, isolated `HOME`/runtime dirs, and two separate project scopes — without ever touching the operator's real Engram database.

## Key mechanics
- **One-command smoke**: `scripts/cos-engram-cloud-docker-smoke --json` starts the compose stack, enrolls two project scopes (`luum-agent-os`, `cos-consumer-e2e-drill`), saves one observation each, syncs both via `scripts/engram-sync.sh --cloud`, and verifies Postgres `cloud_chunks` rows. Uses temp `HOME`/`COGNITIVE_OS_RUNTIME_DIR` and tears down Docker by default (`--keep` to retain for debugging).
- **Expanded manual drill**: explicit steps — `docker compose ... --profile engram-cloud up -d cos-engram-cloud-db cos-engram-cloud`, `scripts/cos-engram-cloud-enroll --server ... --project ... --json` (per scope), `engram save ...` (per scope), `scripts/engram-sync.sh --cloud` with `ENGRAM_PROJECT_SCOPE` set, then a `psql` query against `cloud_chunks` grouped by `project_name`, and an audit check via `tail .../agent-audit-trail.jsonl` for `engram-cloud-enroll-completed` / `engram-cloud-sync-completed` events tagged `audit_class: sync`, `sync_mode: engram-cloud`.
- **Testcontainers lane** (opt-in): `COS_RUN_ENGRAM_CLOUD_CONTAINERS=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_engram_cloud_docker.py -q -ra` — validates the wrapper inside a container and that the Compose profile renders; the one-command smoke is called out as the *stronger* proof since it exercises real `engram cloud serve` + `engram sync --cloud --project`.

## Relations & where used
Uses `docker/cos-worker/docker-compose.yml` (`--profile engram-cloud`, services `cos-engram-cloud-db`/`cos-engram-cloud`) — the same compose file exercised by `cos-instance-installer.md`'s `docker-headless` profile. Directly tied to ADR-141 and Engram's multi-project cloud sync feature (`scripts/cos-engram-cloud-enroll`, `scripts/engram-sync.sh --cloud`).

## Status / caveats
Source explicitly scopes what is NOT proven: no authenticated production token rotation (local smoke uses `ENGRAM_CLOUD_INSECURE_NO_AUTH=1`), no automatic conflict resolution (Engram Cloud conflict handling remains propose-only/operator-judged), and no Shape-B distributed locking or multi-maintainer governance. These are load-bearing scope boundaries, preserved verbatim above.
