# Automation: Doc Sync & Coverage Watcher

Two automation systems that keep documentation accurate and test coverage tracked.

## System 1: Doc Sync (Stale Documentation Detector)

Detects when code changes make documentation stale, and provides a skill to update them.

### Components

| Component | Path | Purpose |
|-----------|------|---------|
| Hook | `hooks/doc-sync-detector.sh` | PostToolUse on Edit/Write — detects stale docs |
| Skill | `.cognitive-os/skills/doc-sync/SKILL.md` | `/doc-sync` — reads stale entries, updates docs |
| Rule | `.cognitive-os/rules/doc-sync.md` | Session-end warning if stale docs exist |
| Metrics | `.cognitive-os/metrics/stale-docs.jsonl` | Append-only log of stale doc detections |

### How It Works

1. Agent edits a source file (*.go, *.ts, *.java)
2. `doc-sync-detector.sh` fires as PostToolUse hook
3. Hook classifies the change type (controller, entity, config, usecase, route, hook, rule, docker)
4. Hook maps the changed file to related documentation files
5. If related docs exist, appends an entry to `stale-docs.jsonl`
6. At session end, the doc-sync rule warns if there are pending stale entries
7. Running `/doc-sync` reads, groups, and updates all stale docs

### File-to-Doc Mapping

| Code Pattern | Affected Documentation |
|-------------|----------------------|
| `*/infrastructure/controllers/*` | migration-audit.md, feature-parity-report.md |
| `*/domain/entities/*` | migration-audit.md |
| `*/config/*` | docs/setup/ |
| `*/application/use*cases/*` | migration-audit.md, feature-parity-report.md |
| `*.module.ts`, `routes.go` | migration-audit.md |
| `hooks/*` | .cognitive-os/docs/hooks.md, overview.md |
| `.cognitive-os/rules/*` | .cognitive-os/docs/rules.md, overview.md |
| `docker-compose*.yml` | docs/setup/docker-architecture.md |

### Stale Entry Format

```json
{
  "timestamp": "2026-03-22T10:30:00Z",
  "changed_file": "wallet/<consumer-service-2>/apps/wallet/infrastructure/controllers/wallet_controller.go",
  "stale_docs": ["docs/backend-go/migration-audit.md"],
  "change_type": "controller"
}
```

### Deduplication

Same file + same docs combo within 60 seconds is not re-logged to prevent noise during iterative edits.

## System 2: Test Coverage Watcher

Automatically checks coverage when Go source files are edited and tracks coverage trends.

### Components

| Component | Path | Purpose |
|-----------|------|---------|
| Hook (updated) | `.claude/hooks/auto-test-on-edit.sh` | Runs tests AND coverage on edit |
| Hook (updated) | `hooks/coverage-gate.sh` | Phase-aware coverage gate on commit/push |
| Metrics | `.cognitive-os/metrics/coverage-baseline.jsonl` | Coverage trend tracking per service |
| Config | `.cognitive-os/cognitive-os.yaml` | `quality.coverage.minimum` threshold |

### How It Works

1. Agent edits a Go file in `apps/`
2. `auto-test-on-edit.sh` runs tests, then runs `go test -coverprofile` for the service
3. Parses coverage percentage from output
4. Reads threshold from `cognitive-os.yaml` (default: 80%)
5. Compares with last recorded coverage from `coverage-baseline.jsonl`
6. Warns if coverage dropped or is below threshold
7. Saves current coverage to baseline

### Phase-Aware Coverage Gate

The `coverage-gate.sh` hook behaves differently based on the project phase in `cognitive-os.yaml`:

| Phase | Behavior |
|-------|----------|
| `reconstruction` | WARN only — don't block during rebuilding |
| `stabilization` | WARN + suggest adding tests |
| `production` | BLOCK commit if below threshold |
| `maintenance` | BLOCK commit if below threshold |

### Coverage Baseline Format

```json
{
  "timestamp": "2026-03-22T10:30:00Z",
  "service": "wallet",
  "coverage": "85.3",
  "threshold": 80
}
```

### Inspecting Coverage Trends

```bash
# Last 10 coverage entries
tail -10 .cognitive-os/metrics/coverage-baseline.jsonl | jq .

# Coverage by service
cat .cognitive-os/metrics/coverage-baseline.jsonl | jq -s 'group_by(.service) | map({service: .[0].service, latest: .[-1].coverage, count: length})'
```

## Registration

Both systems are registered in `.claude/settings.local.json`:

- `doc-sync-detector.sh`: PostToolUse hook on `Edit|Write` matcher
- `auto-test-on-edit.sh`: PostToolUse hook on `Edit|Write` matcher (existing, updated)
- `coverage-gate.sh`: PostToolUse hook on `Bash` matcher (existing, updated)
