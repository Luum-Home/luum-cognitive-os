# Engram Cloud Docker Sync Manual Test

This manual test proves the ADR-141 cloud path without using the operator's real
Engram home directory. It starts the local Docker Compose Engram Cloud profile,
enrolls two project scopes, saves one observation per scope, syncs both through
`scripts/engram-sync.sh --cloud`, and verifies that Postgres received scoped
cloud chunks.

## What this test proves

- `docker/cos-worker/docker-compose.yml` can run `cos-engram-cloud-db` and
  `cos-engram-cloud` locally.
- `scripts/cos-engram-cloud-enroll` can enroll project-scoped cloud sync targets
  without printing token values.
- `scripts/engram-sync.sh --cloud` calls `engram sync --cloud --project` and
  writes `sync_mode: "engram-cloud"` audit rows.
- Multiple project scopes can sync to the same local cloud server without using
  `--cloud --all`.

## What this test does not prove

- It does not prove authenticated production token rotation. The local smoke
  uses `ENGRAM_CLOUD_INSECURE_NO_AUTH=1`.
- It does not prove automatic conflict resolution. Engram Cloud conflict
  handling remains propose-only/operator-judged.
- It does not prove Shape-B distributed locking or multi-maintainer governance.

## One-command smoke

```bash
scripts/cos-engram-cloud-docker-smoke --json
```

Expected shape:

```json
{
  "status": "pass",
  "server": "http://127.0.0.1:18080",
  "projects": ["luum-agent-os", "cos-consumer-e2e-drill"],
  "cloud_chunks": [
    {"project": "cos-consumer-e2e-drill", "chunks": 1, "observations": 1},
    {"project": "luum-agent-os", "chunks": 1, "observations": 1}
  ]
}
```

The script uses a temporary `HOME` and temporary
`COGNITIVE_OS_RUNTIME_DIR`, so it does not write to the operator's normal Engram
database or runtime audit log. It tears down Docker resources by default.

Use `--keep` only when debugging container state:

```bash
scripts/cos-engram-cloud-docker-smoke --keep --json
```

## Expanded manual drill

```bash
export COS_WORKSPACE="$PWD"
export ENGRAM_CLOUD_ALLOWED_PROJECTS="luum-agent-os,cos-consumer-e2e-drill"
export ENGRAM_CLOUD_INSECURE_NO_AUTH=1
export ENGRAM_CLOUD_PORT=18080

docker compose -f docker/cos-worker/docker-compose.yml \
  --profile engram-cloud up -d cos-engram-cloud-db cos-engram-cloud

tmp_home="$(mktemp -d)"
tmp_runtime="$(mktemp -d)"

HOME="$tmp_home" COGNITIVE_OS_RUNTIME_DIR="$tmp_runtime" \
  scripts/cos-engram-cloud-enroll \
    --server http://127.0.0.1:18080 \
    --project luum-agent-os \
    --json

HOME="$tmp_home" \
  engram save "compose cloud sync proof os" \
    "compose profile e2e proof for luum-agent-os" \
    --type discovery \
    --project luum-agent-os \
    --scope project \
    --topic proof/engram-cloud/compose-os

HOME="$tmp_home" COGNITIVE_OS_RUNTIME_DIR="$tmp_runtime" \
  ENGRAM_PROJECT_SCOPE=luum-agent-os \
  scripts/engram-sync.sh --cloud

HOME="$tmp_home" COGNITIVE_OS_RUNTIME_DIR="$tmp_runtime" \
  scripts/cos-engram-cloud-enroll \
    --server http://127.0.0.1:18080 \
    --project cos-consumer-e2e-drill \
    --json

HOME="$tmp_home" \
  engram save "compose cloud sync proof consumer" \
    "compose profile e2e proof for consumer project" \
    --type discovery \
    --project cos-consumer-e2e-drill \
    --scope project \
    --topic proof/engram-cloud/compose-consumer

HOME="$tmp_home" COGNITIVE_OS_RUNTIME_DIR="$tmp_runtime" \
  ENGRAM_PROJECT_SCOPE=cos-consumer-e2e-drill \
  scripts/engram-sync.sh --cloud
```

Verify database evidence:

```bash
docker compose -f docker/cos-worker/docker-compose.yml \
  --profile engram-cloud exec -T cos-engram-cloud-db \
  psql -U engram -d engram -c \
  "select project_name, count(*) chunks, sum(observations_count) observations from cloud_chunks group by project_name order by project_name;"
```

Expected:

```text
      project_name      | chunks | observations
------------------------+--------+--------------
 cos-consumer-e2e-drill |      1 |            1
 luum-agent-os          |      1 |            1
```

Verify COS audit rows:

```bash
tail -n 10 "$tmp_runtime/agent-audit-trail.jsonl"
```

Expected rows include:

- `event: "engram-cloud-enroll-completed"`
- `event: "engram-cloud-sync-completed"`
- `audit_class: "sync"`
- `sync_mode: "engram-cloud"`
- separate `engram_project_scope` values for both projects

Cleanup:

```bash
docker compose -f docker/cos-worker/docker-compose.yml \
  --profile engram-cloud down -v
rm -rf "$tmp_home" "$tmp_runtime"
```

## Testcontainers lane

The repository also has an opt-in testcontainers lane:

```bash
COS_RUN_ENGRAM_CLOUD_CONTAINERS=1 \
  bash scripts/pytest-with-summary.sh -- tests/integration/test_engram_cloud_docker.py -q -ra
```

This lane validates the wrapper inside a container and validates that the
Engram Cloud Compose profile renders. The one-command smoke above is the
stronger sync proof because it exercises real `engram cloud serve` plus
`engram sync --cloud --project`.
