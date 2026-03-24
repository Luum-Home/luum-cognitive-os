# /capability-snapshot

> Protect against feature loss during refactors/cleanups. Snapshot all Cognitive OS capabilities, diff to detect losses, restore removed items.

---
description: "Snapshot, diff, and restore Cognitive OS capabilities to prevent feature loss during refactors"
triggers: ["/capability-snapshot"]
---

## Instructions

This skill has three sub-commands: `save`, `diff`, and `restore`. Parse the user's invocation to determine which to run.

- `/capability-snapshot save` — take a full snapshot
- `/capability-snapshot diff` — compare current state against latest snapshot
- `/capability-snapshot restore [item]` — restore a removed item from the latest snapshot

---

## Sub-command: save

Take a complete inventory of all Cognitive OS capabilities and persist it.

### Step 1: Scan Hooks

Read all `.sh` files in `.cognitive-os/hooks/`. For each file:
- **filename**: the `.sh` filename
- **registered**: check if the filename appears in `.claude/settings.local.json` — yes/no
- **matcher**: if registered, extract the matcher value from settings.local.json
- **description**: read the first comment line (line starting with `#` after the shebang) as description

### Step 2: Scan Rules

Read all `.md` files in `.cognitive-os/rules/` (exclude `RULES-COMPACT.md`). For each file:
- **filename**: the `.md` filename
- **in_rules_compact**: check if the filename (without extension) appears in `RULES-COMPACT.md` — yes/no
- **heading**: extract the first `#` heading from the file

### Step 3: Scan Skills

Read all subdirectories in `.cognitive-os/skills/` (exclude `CATALOG.md` and `auto-generated/`). For each directory:
- **dirname**: the directory name
- **has_skill_md**: check if `SKILL.md` exists in the directory — yes/no
- **name**: extract from SKILL.md frontmatter (the `# /name` line)
- **description**: extract from SKILL.md frontmatter (`description:` field)

### Step 4: Scan Squads

Read all `.yaml` files in `.cognitive-os/squads/`. For each file:
- **filename**: the `.yaml` filename
- **squad_name**: extract from YAML `name` field or derive from filename

### Step 5: Scan Agents

Read all `.md` files in `.cognitive-os/agents/`. For each file:
- **filename**: the `.md` filename
- **agent_name**: extract from first `#` heading or derive from filename

### Step 6: Count Supplementary Files

- **metrics_files**: count `.jsonl` files in `.cognitive-os/metrics/`
- **test_files**: count files in `.cognitive-os/tests/`
- **doc_files**: count `.md` files in `.cognitive-os/docs/`

### Step 7: Record Config

Read `cognitive-os.yaml` and extract:
- **phase**: current project phase
- **loading_strategy**: from context optimization settings if present
- **budget**: from cost tracking settings if present

### Step 8: Persist Snapshot

Build a JSON object with all the above data plus a `timestamp` field (ISO 8601).

1. Save to file: `.cognitive-os/checkpoints/capability-snapshot-{YYYYMMDD-HHMMSS}.json`
2. Save to Engram with:
   - `topic_key`: `cognitive-os/capability-snapshot/{YYYYMMDD-HHMMSS}`
   - `project`: project name from cognitive-os.yaml
   - `type`: `config`
   - `title`: `Capability snapshot {YYYYMMDD-HHMMSS}`

### Step 9: Report

Output a summary:
```
Snapshot saved: X hooks, Y rules, Z skills, W squads, V agents
Metrics: M files | Tests: T files | Docs: D files
Phase: {phase}
Saved to: .cognitive-os/checkpoints/capability-snapshot-{timestamp}.json
```

---

## Sub-command: diff

Compare current state against the latest snapshot to detect changes.

### Step 1: Load Latest Snapshot

Look for the most recent file in `.cognitive-os/checkpoints/capability-snapshot-*.json` (sort by filename descending). If none found, try Engram: `mem_search(query: "cognitive-os/capability-snapshot", project: "{project}")`.

If no snapshot exists, report: "No snapshot found. Run `/capability-snapshot save` first."

### Step 2: Scan Current State

Perform the same scan as the `save` sub-command (Steps 1-7) to get current state.

### Step 3: Compare

For each category (hooks, rules, skills, squads, agents), compare snapshot vs current:

- **REMOVED** (in snapshot, not on disk): mark with red indicator
- **ADDED** (on disk, not in snapshot): mark with green indicator
- **MODIFIED** (exists in both but properties changed): mark with yellow indicator
- **UNREGISTERED** (hooks on disk but `registered: no`): mark with warning indicator

### Step 4: Report Diff Table

Output a table per category with changes:

```
## Hooks
| Status | File | Detail |
|--------|------|--------|
| REMOVED | some-hook.sh | Was registered with matcher "Agent" |
| ADDED | new-hook.sh | Not yet registered |
| UNREGISTERED | orphan-hook.sh | On disk but not in settings.json |

## Rules
| Status | File | Detail |
|--------|------|--------|
| (no changes) |

## Skills
...

## Summary
- Removed: X items
- Added: Y items
- Modified: Z items
- Unregistered hooks: W
```

If REMOVED items found, add warning:
"WARNING: X capabilities were removed since last snapshot. Run `/capability-snapshot restore [item]` to recover."

---

## Sub-command: restore [item]

Restore a capability that was removed since the last snapshot.

### Step 1: Identify Item

Parse `[item]` — it can be a filename (e.g., `some-hook.sh`) or a skill directory name (e.g., `my-skill`).

### Step 2: Look Up in Snapshot

Load the latest snapshot. Find the item by matching against hooks (filename), rules (filename), skills (dirname), squads (filename), or agents (filename).

If not found in snapshot: "Item '{item}' not found in the latest snapshot."

### Step 3: Restore from Git

Use `git log --diff-filter=D --name-only -- {path}` to find when the file was deleted, then `git show {commit}:{path}` to recover the content.

- **Hook**: restore the `.sh` file to `.cognitive-os/hooks/`, make executable (`chmod +x`). Suggest adding to `settings.local.json` with the original matcher from the snapshot.
- **Rule**: restore the `.md` file to `.cognitive-os/rules/`. Suggest adding to `RULES-COMPACT.md`.
- **Skill**: restore the entire directory to `.cognitive-os/skills/`. Check if `SKILL.md` is recovered.
- **Squad**: restore the `.yaml` file to `.cognitive-os/squads/`.
- **Agent**: restore the `.md` file to `.cognitive-os/agents/`.

### Step 4: Report

```
Restored: {item}
Type: {hook|rule|skill|squad|agent}
Path: {restored path}
Action needed: {any manual registration steps}
```

If git recovery fails: "Could not restore '{item}' from git history. The file may have never been committed."
