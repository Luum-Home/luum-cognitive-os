<!-- SCOPE: both -->
---
name: doc-sync
version: 1.0.0
description: Synchronize documentation that became stale after code changes
invocation: /doc-sync
last-updated: 2026-03-22
audience: project
platforms: ["claude-code"]
prerequisites: []
---

# Doc Sync — Stale Documentation Updater

## Purpose

When source code changes (controllers, entities, configs, routes, use cases), the `doc-sync-detector.sh` hook marks related documentation as potentially stale. This skill reads those markers and updates the affected docs.

## Invocation

```
/doc-sync
```

## Procedure

### 1. Read stale entries

Read `.cognitive-os/metrics/stale-docs.jsonl`. Each line is:
```json
{"timestamp": "...", "changed_file": "...", "stale_docs": ["..."], "change_type": "controller|entity|config|usecase|route|hook|rule|docker"}
```

If the file is empty or doesn't exist, report "No stale docs detected" and exit.

### 2. Group by documentation file

Group all entries by `stale_docs` target. This avoids updating the same doc multiple times. For each unique doc file, collect all the source files that triggered staleness.

### 3. Update each stale document

For each stale doc:

1. **Read the documentation file** to understand its current content and structure
2. **Read each changed source file** that triggered the staleness
3. **Determine what changed**: compare the source code state with what the doc describes
4. **Update the doc** to reflect the current code reality:
   - For migration audits: update endpoint lists, entity schemas, completion status
   - For feature parity reports: update implementation status
   - For setup docs: update configuration references
   - For hook/rule docs: update descriptions, counts, behavior
   - For docker docs: update service definitions, ports, volumes
5. **Preserve doc structure**: maintain existing headings, formatting, and sections. Only update the content within relevant sections.

### 4. Clear processed entries

After successfully updating all docs, truncate `.cognitive-os/metrics/stale-docs.jsonl` to remove processed entries. If some updates failed, only remove the successfully processed entries.

### 5. Report

Output a summary:
```
## Doc Sync Report

Updated N documents based on M code changes:

| Document | Changes Applied | Source Files |
|----------|----------------|--------------|
| docs/migration-audit.md | Updated endpoint list | apps/wallet/infrastructure/controllers/wallet_controller.go |
| ... | ... | ... |

Remaining stale entries: X (if any failed)
```

## Edge Cases

- If a listed doc file no longer exists, skip it and log a warning
- If a source file no longer exists (was deleted), note the deletion in the doc update
- If the doc has no section relevant to the change, add a note at the end
- Never delete content from docs — only update or append

## Integration

- **Triggered by**: `doc-sync-detector.sh` PostToolUse hook (automatic detection)
- **Rule**: `doc-sync.md` warns at session end if stale docs exist
- **Metrics**: Entries in `.cognitive-os/metrics/stale-docs.jsonl`
