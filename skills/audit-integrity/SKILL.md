<!-- SCOPE: os-only -->
---
name: audit-integrity
description: >
  Symlink-aware integrity audit of hooks, libs, and skills.
  Resolves symlinks before classifying, preventing false ghost reports.
version: 1.0.0
user-invocable: true
disable-model-invocation: true
auto-generated: false
last-updated: 2026-04-15
license: MIT
metadata:
  author: luum
audience: os
summary_line: "Symlink-aware integrity audit of hooks, libs, and skills."

---

## Purpose

Standardized integrity audit that correctly handles symlinks. Replaces ad-hoc `[ -f ]` checks that agents improvise (and get wrong — a prior audit reported 20 ghost hooks that were actually valid symlinks).

## Invocation

`/audit-integrity [--scope hooks|libs|skills|all] [--fix]`

## What to Do

### Step 1: Source the file checker

```bash
source hooks/_lib/file_checker.sh
```

### Step 2: For each component type, cross-reference settings.json with disk

**Hooks:**
```bash
# For each hook in .claude/settings.json:
#   1. Extract the path from the command field
#   2. Use file_exists_strict (not [ -f ]) to check
#   3. If symlink: resolve with resolve_path, report both paths
#   4. If broken symlink: use is_broken_symlink to detect
#   5. Classify: ALIVE (exists + registered), DORMANT (exists + not registered),
#      GHOST (registered + missing), BROKEN_SYMLINK (registered + broken target)
```

**Libs:**
```bash
# For each .py in lib/:
#   1. Check if imported by any hook or other lib
#   2. Resolve symlinks before checking imports
#   3. Classify: ALIVE (has callers), DEAD (no callers), BROKEN_CHAIN (calls missing lib)
```

**Skills:**
```bash
# For each SKILL.md in skills/ and packages/*/skills/:
#   1. Check if listed in CATALOG.md
#   2. Classify: ACTIVE (has content), STUB (empty/placeholder), ORPHANED (not in catalog)
```

### Step 3: Report

Output a structured table:
```
Component Type | Total | Alive | Dead | Ghost | Broken Symlink
hooks          |    48 |    48 |    0 |     0 |              0
libs           |    95 |    55 |    34|     0 |              6
skills         |   120 |   120 |    0 |     0 |              0
```

### Step 4: If --fix

- Remove GHOST entries from settings.json
- Report BROKEN_SYMLINK targets for manual resolution
- Do NOT delete files — only clean config references

## Rules

- ALWAYS use `hooks/_lib/file_checker.sh` functions, NEVER raw `[ -f ]`
- ALWAYS resolve symlinks with `readlink -f` before classifying as missing
- Report both the symlink path AND the resolved target path
- When counting, count the symlink as ONE component (not symlink + target)
- Cross-validate findings before reporting — if a file appears missing, verify with `ls -la` and `readlink -f`
