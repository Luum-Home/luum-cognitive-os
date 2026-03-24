# Capability Snapshot

> Protect against feature loss during Cognitive OS refactors and cleanups.

## Problem

When restructuring, cleaning up, or consolidating Cognitive OS components (hooks, rules, skills, squads, agents), capabilities can be accidentally removed. Without a baseline to compare against, these losses go undetected until something breaks.

## Solution

The capability snapshot system provides three operations:

1. **Save** (`/capability-snapshot save`): Takes a full inventory of all Cognitive OS components and persists it as a checkpoint file and in Engram.
2. **Diff** (`/capability-snapshot diff`): Compares current state against the latest snapshot and reports additions, removals, modifications, and unregistered hooks.
3. **Restore** (`/capability-snapshot restore [item]`): Recovers a removed item from git history using the snapshot as reference.

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| Skill | `.cognitive-os/skills/capability-snapshot/SKILL.md` | Skill definition with save/diff/restore sub-commands |
| Hook | `.cognitive-os/hooks/pre-cleanup-snapshot.sh` | PreToolUse hook that detects cleanup intent and advises snapshot |
| Rule | `.cognitive-os/rules/capability-protection.md` | Mandatory snapshot before/after cleanup rule |
| Checkpoints | `.cognitive-os/checkpoints/capability-snapshot-*.json` | Persisted snapshot files |
| Metrics | `.cognitive-os/metrics/capability-snapshots.jsonl` | Hook detection log |

## What Gets Snapshotted

- **Hooks**: filename, registered status in settings.json, matcher, description
- **Rules**: filename, presence in RULES-COMPACT.md, first heading
- **Skills**: directory name, SKILL.md presence, name and description from frontmatter
- **Squads**: filename, squad name
- **Agents**: filename, agent name
- **Counts**: metrics files, test files, doc files
- **Config**: phase, loading strategy, budget from cognitive-os.yaml

## Workflow

```
1. Before cleanup:   /capability-snapshot save
2. Do the cleanup/refactor
3. After cleanup:    /capability-snapshot diff
4. If removals:      Justify each or /capability-snapshot restore [item]
```

## Hook Behavior

The `pre-cleanup-snapshot.sh` hook fires on Agent tool calls (PreToolUse) when:
- The agent prompt contains cleanup keywords: "cleanup", "delete", "remove", "merge", "consolidate", "refactor cognitive-os"
- AND the prompt references Cognitive OS scope: "cognitive-os", "hooks", "skills", "rules", etc.

It does NOT block -- it emits an advisory message recommending `/capability-snapshot save`.

It skips the advisory if a snapshot was taken within the last hour.

## Engram Integration

Snapshots are saved to Engram with topic key `cognitive-os/capability-snapshot/{timestamp}` for cross-session persistence and recovery.
