<!-- SCOPE: both -->
<!-- TIER: 2 -->

# Engram API Safety — Never Mutate Production Daemon for Discovery

## Purpose

The engram daemon at port 7437 stores the project's persistent memory in a local SQLite database (`~/.engram/engram.db`). This database has no revision history, no undo mechanism, and no rollback capability — a single overwrite permanently replaces the original observation content. This rule prevents accidental data destruction during API exploration or testing.

## Rule

- **NEVER** run `PATCH`, `POST`, or `DELETE` requests against the production engram daemon at port 7437 for the purpose of API exploration, curl experiments, or testing.
- **NEVER** issue ad-hoc `curl -X PATCH http://127.0.0.1:7437/...` commands against real observation IDs.
- **ALWAYS** spawn a sandboxed daemon on an alternate port with a temporary data directory when you need to test mutating endpoints.
- The only approved client for `PATCH /observations/<id>` in production code is `lib/engram_http_client.py`, which is typed, reviewed, and never used for ad-hoc exploration.
- Read-only production operations are safe: `GET /health`, `GET /search`, `GET /observations/<id>`, and `GET /stats` do not modify data and may be called freely.

## Rationale

On 2026-04-27, observation #13283 was accidentally overwritten during HTTP API discovery. The original content was partially reconstructed from a git commit and session preview but could not be restored verbatim. Engram stores observations as rows in SQLite; there is no version history, no tombstone mechanism, and no differential backup at the row level. A single `PATCH` call overwrites the `content` column with no prior snapshot.

The production DB at `~/.engram/engram.db` is a singleton with no staging equivalent. Any exploration that requires testing mutating endpoints must use a sandboxed instance.

## How to Explore Safely

Spawn a sandboxed daemon on an alternate port with a temporary data directory:

```bash
TMPDIR=$(mktemp -d)
ENGRAM_DATA_DIR="$TMPDIR" <engram-bin> serve 7438 &
PROBE_PID=$!
# Wait for daemon to start
sleep 1
# Seed test observations via CLI
ENGRAM_DATA_DIR="$TMPDIR" engram save "test obs" "test content" --type manual
# Now probe safely — this is not production data
curl -X PATCH http://127.0.0.1:7438/observations/1 \
  -H 'Content-Type: application/json' \
  -d '{"content":"test overwrite"}'
# Tear down when done
kill $PROBE_PID
rm -rf "$TMPDIR"
```

Key properties of the sandbox:
- Alternate port (7438 or any free port) — the production daemon at 7437 is untouched.
- `ENGRAM_DATA_DIR` set to a temp directory — observations are throwaway.
- `PROBE_PID` tracked for clean teardown — no daemon leaks.

## Safe Production Operations

The following read-only endpoints are safe to call against the production daemon at port 7437 at any time:

| Verb | Endpoint | Safe? |
|------|----------|-------|
| GET | `/health` | Yes — no side effects |
| GET | `/search?q=...` | Yes — read-only |
| GET | `/observations/<id>` | Yes — read-only |
| GET | `/stats` | Yes — read-only |
| PATCH | `/observations/<id>` | No — overwrites content permanently |
| POST | `/observations` | No — creates permanent records |
| DELETE | `/observations/<id>` | No — destroys data permanently |

## Tooling

`lib/engram_http_client.py` is the only approved production caller for `PATCH /observations/<id>`. It:
- Requires at least one field to be specified (raises `ValueError` on empty PATCH as a programming-error guard).
- Is used exclusively by `lib/engram_lifecycle.py` for in-place reinforcement updates.
- Logs at debug level; never raises on network failure.

Do not use `engram_http_client.update_observation()` for arbitrary experimentation. Its sole purpose is lifecycle reinforcement.

## Examples

### Good

```bash
# Test PATCH against sandboxed daemon only
TMPDIR=$(mktemp -d)
ENGRAM_DATA_DIR="$TMPDIR" engram serve 7438 &
curl -X PATCH http://127.0.0.1:7438/observations/1 -d '{"content":"safe test"}'
kill %1; rm -rf "$TMPDIR"
```

```python
# Production code uses the typed client, never raw curl
from lib.engram_http_client import update_observation
result = update_observation(obs_id, content=new_content)
```

### Bad

```bash
# NEVER: direct PATCH against production port 7437
curl -X PATCH http://127.0.0.1:7437/observations/13283 \
  -d '{"content":"test"}'
```

```bash
# NEVER: exploration without sandbox
curl -X DELETE http://127.0.0.1:7437/observations/1
```

## Related

- `lib/engram_http_client.py` — the only approved production client for PATCH
- `lib/engram_lifecycle.py` — uses `engram_http_client.update_observation()` in `reinforce()`
- `docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md` — addendum 2026-04-27 documents the incident
- `rules/credential-management.md` — related data-protection conventions
