<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Doc Sync Rule

## Session End Warning

At session end, if `.cognitive-os/metrics/stale-docs.jsonl` has entries, the orchestrator MUST:

1. Count the number of stale doc entries
2. Warn the user:
   > "There are N stale documentation entries pending. Run `/doc-sync` to update affected docs before closing."
3. If the user chooses to skip, the entries persist for the next session

## When Code Changes Affect Docs

The `doc-sync-detector.sh` hook automatically detects when source file edits (*.go, *.ts, *.java) affect documentation. The mapping:

| Code Pattern | Affected Docs |
|-------------|---------------|
| `*/infrastructure/controllers/*` | migration-audit.md, feature-parity-report.md |
| `*/domain/entities/*` | migration-audit.md |
| `*/config/*` | docs/05-Methodology/setup/ |
| `*/application/use*cases/*` | migration-audit.md, feature-parity-report.md |
| `*.module.ts`, `routes.go` | migration-audit.md |
| `hooks/*` | .cognitive-os/docs/05-Methodology/root/hooks.md, overview.md |
| `.cognitive-os/rules/*` | .cognitive-os/docs/05-Methodology/root/rules.md, overview.md |
| `docker-compose*.yml` | docs/05-Methodology/setup/docker-architecture.md |

## Integration

- **Hook**: `hooks/doc-sync-detector.sh` (PostToolUse on Edit|Write)
- **Skill**: `/doc-sync` reads stale entries and updates docs
- **Metrics**: `.cognitive-os/metrics/stale-docs.jsonl`

## Contextual Trigger

- When work relates to Doc Sync Rule.
