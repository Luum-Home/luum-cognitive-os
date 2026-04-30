# ADR-043: Paperclip Local Daemon — Extract from Docker (D34 Partial)

**Date**: 2026-04-30
**Status**: Accepted
**Deciders**: Matias Améndola
**Relates to**: D34 (Docker→pip phase 3), ADR-002 (docker-pip phase 2), ADR-042 (Valkey local daemon)

---

## Context

Three services remained bound to `docker-compose.cognitive-os.yml` as mandatory
Docker containers: Paperclip, PostgreSQL (Langfuse-internal), and Valkey
(general-purpose Agent Bus pub/sub). Valkey was extracted in ADR-042.

Paperclip is the UI layer for Cognitive OS — an agent coordination platform
that exposes dashboards for SDD pipeline state, agent heartbeats, cost data,
and notifications. Its Docker path requires:

- OrbStack/Docker Desktop running (~1 GB RAM for VM)
- `docker compose up` before any dashboard push
- Two containers: `paperclip` (Node.js) + `paperclip-pg` (Postgres)

Unlike Valkey, Paperclip does **not** ship a standalone CLI binary installable
via Homebrew. Installation depends on npm (`@paperclip-ai/paperclip` or
similar). Because the binary is not universally available, the local daemon is
a **conditional path**: it activates when a Paperclip binary is found; when
absent, it exits 2 (graceful skip) and the system falls back to Docker or
continues without a dashboard.

---

## Decision

**Paperclip is managed by `scripts/cos-paperclip-local.sh` when a local
binary is available. Docker containers are demoted to `profiles: [legacy]`.**

Key choices:

1. **Binary detection**: checks for `paperclip` in PATH, then `npx paperclip`.
   If neither is found, exits 2 with install instructions — no packages are
   installed by the script.

2. **Port selection**: tries 3200 first (Paperclip default); falls back to
   3201 if 3200 is bound. The chosen port is written to
   `.cognitive-os/runtime/paperclip.port` for client discovery.

3. **Single-instance guard**: atomic `mkdir` lock (same pattern as
   `cos-valkey-local.sh` and `reaper-heartbeat.sh`) prevents duplicate daemons.

4. **`paperclip_client.py` updated** (`get_url()`): the port-file discovery
   path was already implemented in anticipation of this ADR. The function
   checks the port file, then env-configured URL, then the default
   `http://localhost:3200`.

5. **Docker containers demoted to `profiles: [legacy]`**: `paperclip` and
   `paperclip-pg` in `docker-compose.cognitive-os.yml` require explicit
   `--profile legacy` to start. They remain accessible for CI or machines
   without a local binary.

6. **No database migration**: the local daemon uses whatever database
   Paperclip discovers (SQLite by default, or env-configured). The Docker
   Postgres path is preserved under `profiles: [legacy]` for operators who
   need a persistent Postgres backend.

---

## Consequences

### Positive
- Session startup does not depend on Docker for the Paperclip dashboard
- Works on machines with a local Paperclip binary without Docker overhead
- `paperclip_client.py` auto-discovers the daemon via port file
- Docker path preserved for CI and machines without a binary

### Negative / Constraints
- Paperclip binary is not universally available (not on Homebrew). Machines
  without the binary will skip the local daemon (exit 2) and use Docker or
  run without a dashboard.
- The daemon is not supervised by launchd/systemd — it does not auto-restart
  across reboots.
- Node.js startup is slower than Redis (~15s timeout vs ~3s for Valkey).

### Rollback
To revert to Docker Paperclip:
```bash
docker compose -f docker-compose.cognitive-os.yml --profile legacy up -d paperclip paperclip-pg
bash scripts/cos-paperclip-local.sh --stop
```
Then set `PAPERCLIP_URL=http://localhost:3200`. No code changes needed —
`paperclip_client.py` will connect to the Docker container.

---

## Status of D34

| Service | D34 Status |
|---------|-----------|
| Valkey (Agent Bus) | **RESOLVED** — local daemon via `cos-valkey-local.sh` (ADR-042) |
| Paperclip | **PARTIAL** — local daemon script ready; Docker demoted to `profiles: [legacy]`; binary availability determines activation |
| PostgreSQL (Langfuse) | **RESOLVED** — local cluster via `cos-postgres-local.sh` (ADR-045) |

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/cos-paperclip-local.sh` | New — start/stop local daemon |
| `packages/ecosystem-tools/lib/paperclip_client.py` | `get_url()` already implements port-file discovery (no change needed) |
| `docker-compose.cognitive-os.yml` | `paperclip` + `paperclip-pg` services get `profiles: [legacy]` |
| `tests/integration/test_paperclip_local_daemon.py` | New — daemon lifecycle tests |
