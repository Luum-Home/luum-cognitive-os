<!-- SCOPE: os-only -->
<!-- TIER: 2 -->
# Capability Protection

> Prevent unintended feature loss during Cognitive OS refactors, cleanups, and consolidations.

## Rules

### Before Any Cleanup/Refactor of .cognitive-os/

1. **MUST** run `/capability-snapshot save` before making structural changes (deleting, merging, renaming, or reorganizing hooks, rules, skills, squads, or agents).
2. The snapshot creates a checkpoint in `.cognitive-os/checkpoints/` and in Engram.

### After Cleanup/Refactor

3. **MUST** run `/capability-snapshot diff` to compare current state against the pre-change snapshot.
4. Review the diff output for any REMOVED items.

### On REMOVED Items

5. Each removed capability **MUST** have an explicit justification:
   - **Replaced**: the capability was merged into another item (state which one)
   - **Deprecated**: the capability is no longer needed (state why)
   - **Duplicate**: an identical capability already exists elsewhere (state where)
6. If a removal cannot be justified, **MUST** restore it using `/capability-snapshot restore [item]`.

### Prohibited Without Snapshot

7. **DO NOT** bulk-delete files from `hooks/`, `.cognitive-os/rules/`, `.cognitive-os/skills/`, `.cognitive-os/squads/`, or `.cognitive-os/agents/` without a prior capability snapshot.
8. **DO NOT** rewrite `settings.local.json` hook registrations without verifying all hooks are preserved.
9. **DO NOT** rewrite `RULES-COMPACT.md` without verifying all rules are represented.
10. **DO NOT** rewrite `CATALOG.md` without verifying all skills are listed.

## Enforcement

- **Hook**: `pre-cleanup-snapshot.sh` (PreToolUse on Agent) detects cleanup intent and advises snapshot.
- **Skill**: `/capability-snapshot` provides save/diff/restore sub-commands.
- **Metrics**: detections logged to `.cognitive-os/metrics/capability-snapshots.jsonl`.

## Contextual Trigger

- When work relates to Capability Protection.
