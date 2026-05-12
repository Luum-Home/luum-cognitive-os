# Manual Test — COS Instance Installer

## Purpose

Validate that Cognitive OS has a dedicated installer for operational SO
instances, separate from `scripts/cos_init.py` consumer-project projection.

## Preconditions

- Run from the Cognitive OS repository root.
- No provider API key is required.
- Docker is optional for the profile dry-run/write proof; Docker smoke remains a
  separate command.

## Steps

### 1. Contract tests

```bash
python3 -m pytest tests/contracts/test_cos_instance_profiles.py -q
```

Expected: all tests pass.

### 2. Local profile dry-run

```bash
scripts/cos-instance-init --profile local --dry-run --json
```

Expected:

- JSON output;
- `mode=dry-run`;
- profile is `local`;
- command does not write provider credentials.

### 3. Docker-headless profile dry-run

```bash
scripts/cos-instance-init --profile docker-headless --dry-run --json
```

Expected:

- JSON output;
- profile is `docker-headless`;
- file checks mention `docker/cos-worker/docker-compose.yml` and
  `scripts/cos-headless-service-drill`.

### 4. Write into a disposable workspace

```bash
TMP="$(mktemp -d /tmp/cos-instance-init.XXXXXX)"
git archive HEAD | tar -x -C "$TMP"
scripts/cos-instance-init --project-dir "$TMP" --profile local --write --json
scripts/cos-instance-init --project-dir "$TMP" --profile docker-headless --write --json
find "$TMP/.cognitive-os/instances" -maxdepth 3 -type f | sort
rm -rf "$TMP"
```

Expected files:

```text
.cognitive-os/instances/local/commands.md
.cognitive-os/instances/local/instance.json
.cognitive-os/instances/docker-headless/commands.md
.cognitive-os/instances/docker-headless/instance.json
```

### 5. Planned profiles stay write-blocked

```bash
TMP="$(mktemp -d /tmp/cos-instance-init-planned.XXXXXX)"
git archive HEAD | tar -x -C "$TMP"
scripts/cos-instance-init --project-dir "$TMP" --profile host-cli-bridge --write --json || true
rm -rf "$TMP"
```

Expected: output status is `write-blocked`.

### 6. Optional Docker smoke

```bash
scripts/cos-headless-service-drill --json
```

Expected: `ok=true` when Docker is available and the worker image can run.
