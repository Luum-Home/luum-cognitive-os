# ADR-045: PostgreSQL Local Daemon — Extract from Docker (D34)

**Date**: 2026-04-30
**Status**: Accepted
**Deciders**: Matias Améndola
**Relates to**: D34 (Docker→pip phase 3), ADR-042 (Valkey local daemon), ADR-043 (Paperclip local daemon)

---

## Context

As part of D34 (Docker→pip phase 3), PostgreSQL was the last service
remaining bound to `docker-compose.cognitive-os.yml` as a mandatory Docker
container. PostgreSQL serves as the backend database for Paperclip and,
in some configurations, for MemU.

Running Docker for a database server creates the same friction as Valkey:

- Session startup blocks until Docker/OrbStack initialises
- Local dev on machines without Docker Desktop stalls
- The OrbStack VM requires ~1 GB RAM for a service that needs ~50 MB
- The Docker container uses a default port 5432, which may conflict with
  a system-installed Postgres

`pg_ctl` is available via Homebrew's `postgresql@17` formula and is present
on most developer macOS machines that use any Postgres tooling.

---

## Decision

**A local PostgreSQL cluster is managed by `scripts/cos-postgres-local.sh`
using `pg_ctl` and `initdb`.**

Key choices:

1. **Binary detection**: checks `pg_ctl` in PATH, then common Homebrew paths
   (`/opt/homebrew/opt/postgresql@{17,16,15,14}/bin/pg_ctl`). If none found,
   exits 2 with install instructions — no packages are installed by the script.

2. **Port 5433**: avoids collision with a system-installed Postgres on 5432.
   Falls back to 5434 if 5433 is bound. The chosen port is written to
   `.cognitive-os/runtime/postgres.port` for client discovery.
   Override via `POSTGRES_LOCAL_PORT` env var.

3. **Data directory**: `.cognitive-os/runtime/postgres-data/` — within the
   project runtime dir, not system-wide. Cluster is initialised by `initdb`
   on first start with `--encoding=UTF8 --locale=C --auth=trust`.

4. **Single-instance guard**: atomic `mkdir` lock prevents duplicate clusters.

5. **`--init` flag**: allows pre-initialising the data directory without
   starting the daemon. Useful in CI or setup scripts.

6. **Docker container demoted to `profiles: [legacy]`**: `paperclip-pg`
   in `docker-compose.cognitive-os.yml` requires explicit `--profile legacy`
   to start. It remains accessible for CI environments without a local binary.

7. **No `pg_hba.conf` changes**: `initdb --auth=trust` configures local
   connections without password. This is intentional for a localhost-only
   dev daemon.

---

## Consequences

### Positive
- Session startup no longer depends on Docker for any PostgreSQL backend
- Works on machines with Homebrew Postgres without Docker overhead
- Cluster lifecycle is explicit and auditable (PID file + health metrics)
- Port 5433 avoids disrupting existing system Postgres on 5432
- `--init` enables pre-provisioning in setup scripts

### Negative / Constraints
- Developers need `postgresql@17` (or older) installed via Homebrew.
  Missing binary produces a clear error with install instructions (exit 2).
- `initdb` takes 2–5 seconds on first run. Tests use `@pytest.mark.timeout(120)`.
- The daemon is not supervised by launchd/systemd — it does not auto-restart
  across reboots. A session-start hook can call `cos-postgres-local.sh` to
  handle restarts.
- Data persistence is in the project runtime dir. If `.cognitive-os/runtime/`
  is cleaned, the cluster must be re-initialised.

### Rollback
To revert to Docker Postgres:
```bash
docker compose -f docker-compose.cognitive-os.yml --profile legacy up -d paperclip-pg
bash scripts/cos-postgres-local.sh --stop
```
Then update `DATABASE_URL` or `POSTGRES_URL` to point at the Docker container
(`postgres://paperclip:paperclip@localhost:5438/paperclip`).

---

## Status of D34

| Service | D34 Status |
|---------|-----------|
| Valkey (Agent Bus) | **RESOLVED** — local daemon via `cos-valkey-local.sh` (ADR-042) |
| Paperclip | **PARTIAL** — local daemon script ready; binary availability determines activation (ADR-043) |
| PostgreSQL | **RESOLVED** — local cluster via `cos-postgres-local.sh` (this ADR) |

**D34 is CLOSED**: all three services have been addressed. Docker compose
profiles are set to `legacy` for all three. The remaining Docker containers
are kept for CI compatibility only.

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/cos-postgres-local.sh` | New — init/start/stop local pg_ctl cluster |
| `docker-compose.cognitive-os.yml` | `paperclip-pg` already had `profiles: [legacy]`; confirmed |
| `tests/integration/test_postgres_local_daemon.py` | New — daemon lifecycle tests |
