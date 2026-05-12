---
adr: 42
title: Valkey Local Daemon — Extract from Docker (D34 Partial)
status: accepted
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-042: Valkey Local Daemon — Extract from Docker (D34 Partial)

**Date**: 2026-04-20
**Status**: Accepted
**Deciders**: Matias Améndola
**Relates to**: D34 (Docker→pip phase 3), ADR-002 (docker-pip phase 2)

---

## Relationship to ADR-018 and ADR-048

This ADR is a continuation of ADR-018 phase 3, not a reversal of the Docker-to-pip migration. Valkey is treated as a local or optional service because it cannot be replaced by a Python library without losing its runtime role. ADR-048 applies only when a Docker-backed fallback or reference container is used; the preferred local path remains non-Docker when available.

## Context

Three services remained bound to `docker-compose.cognitive-os.yml` as mandatory
(general-purpose Agent Bus pub/sub). This is tracked as debt item D34.

Running Docker for a single pub/sub daemon creates friction:
- Session startup blocks until Docker/OrbStack initialises
- Local dev on machines without Docker Desktop stalls
- The OrbStack VM requires ~1 GB RAM for a service that needs ~10 MB

Valkey is a Redis fork with a compatible wire protocol. The `redis` Python
package (already a project dependency) connects to either. The `redis-server`
binary ships with Homebrew's `redis` formula and is available on all developer
macOS machines.

---

## Decision

**Valkey for the Agent Bus is extracted to a local daemon managed by
`scripts/cos-valkey-local.sh`.**

Key choices:

1. **Binary preference**: `valkey-server` if installed; fall back to
   `redis-server` (Redis 7.x, fully protocol-compatible). The script detects
   the binary at runtime and documents missing binary — it never installs
   system packages.

2. **Port selection**: tries 6379 first; falls back to 6380 if 6379 is already
   bound (e.g., by Docker or another process). The chosen port is written to
   `.cognitive-os/runtime/valkey.port` for client discovery.

3. **Single-instance guard**: atomic `mkdir` lock (same pattern as
   `reaper-heartbeat.sh`) prevents duplicate daemons.

4. **Docker container demoted to `profiles: [legacy]`**: the `valkey` service
   in `docker-compose.cognitive-os.yml` is no longer started by default. It
   remains accessible via `--profile legacy` for CI environments without a
   local binary.

5. **`agent_bus.py` fallback chain updated** (`_resolve_valkey_url`):
   - Primary: env-configured URL (default `localhost:6379`)
   - Local daemon fallback: `localhost:6380` → `localhost:6379`
   - Docker (via `smart_infra.ensure_service`)
   - File-based FallbackBus

6. **`hooks/valkey-ensure.sh` updated**: prefers local daemon start over
   Docker start. Docker/OrbStack path retained as secondary fallback.

---

## Consequences

### Positive
- Session startup no longer depends on Docker for the Agent Bus
- Works on machines with only Homebrew redis installed
- RAM footprint reduced: ~10 MB for redis-server vs ~1 GB for OrbStack VM
- Daemon lifecycle is explicit and auditable (PID file + health metrics)

### Negative / Constraints
- Developers need `valkey-server` OR `redis-server` installed locally
  (`brew install valkey` or `brew install redis`). Missing binary produces a
  clear error with install instructions (exit 2).
- The daemon is not supervised by launchd/systemd — it does not auto-restart
  across reboots. `valkey-ensure.sh` at session start handles restarts.
- Data persistence is disabled (`--save "" --appendonly no`). Agent Bus data is
  ephemeral by design.

### Rollback
To revert to Docker Valkey:
```bash
docker compose -f docker-compose.cognitive-os.yml --profile legacy up -d valkey
bash scripts/cos-valkey-local.sh --stop
```
Then set `VALKEY_URL=redis://localhost:6379` (same as before). No code changes
needed — the fallback chain in `agent_bus.py` will connect to the Docker
container.

---

## Status of D34

| Service | D34 Status |
|---------|-----------|
| Valkey (Agent Bus) | **RESOLVED** — local daemon via `cos-valkey-local.sh` |
| PostgreSQL (Langfuse) | OPEN — Docker only (Langfuse dependency) |

separate session.

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/cos-valkey-local.sh` | New — start/stop local daemon |
| `lib/agent_bus.py` | `_resolve_valkey_url`, `_emit_local_daemon_metric`, updated `_connect` in both classes |
| `hooks/valkey-ensure.sh` | Local daemon preferred over Docker |
| `docker-compose.cognitive-os.yml` | `valkey` service gets `profiles: [legacy]` |
| `tests/integration/test_valkey_local_daemon.py` | New — daemon lifecycle tests |
