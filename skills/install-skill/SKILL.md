---
name: install-skill
description: 'Use when you need this Cognitive OS skill: Install an extension skill
  from a local path, extension pack, or packages/cos-* into the active skill routing;
  do not use when the skill already exists or when authoring a new skill from scratch.'
routing_intents:
  - "Install a Cognitive OS extension skill by name from the extension registry"
  - "Enable an opt-in skill from packages/cos-* or skills/extensions/"
  - "Symlink an extension skill into the active skill routing surface"
  - "Register an extension skill in cognitive-os.yaml extensions key"
  - "Make an extension pack skill invokable without a full COS migration"
version: 0.1.0
audience: os
tags:
  - install
  - extension
  - skills
  - plugin
platforms:
  - claude-code
prerequisites: []
routing_patterns:
  - pattern: \binstall[- ]?skill\b
    confidence: 0.95
  - pattern: /install-skill\b
    confidence: 0.97
  - pattern: \benable\s+skill\b
    confidence: 0.75
  - pattern: \bactivate\s+extension\s+skill\b
    confidence: 0.78
summary_line: Install an extension skill from packages/cos-* or skills/extensions/ into active routing.
triggers:
  - install-skill
  - /install-skill
  - enable extension skill
  - activate skill

---
<!-- SCOPE: os-only -->
# /install-skill

> Install an extension skill from the COS extension registry into the active skill routing surface.

## Scope note

This skill is `os-only` because it modifies the COS skill routing surface
(`.claude/skills/` symlinks) and registers entries in `cognitive-os.yaml`.
Only use this in COS self-hosting contexts. For creating a brand-new skill from
scratch, use `/add-skill`.

## Trigger

When you want to activate an existing but unlinked extension skill — one that
lives in `packages/cos-*/skills/` or `skills/extensions/` — and make it
invokable via its slash command without running a full wave migration.

## Inputs

- **`<name>`**: kebab-case skill name (e.g., `dogfood-score`, `sdd-design`)
- **`--source <path>`** (optional): explicit directory containing the skill's
  `SKILL.md` if it is not in the standard search paths
- **`--dry-run`** (optional): show what would happen without writing anything

## API Signature

```
/install-skill <name> [--source <path>] [--dry-run]
```

## When to use

- You ran `/install-recommended` and it listed an extension skill you want now.
- A feature plan asks you to ship an on-demand skill without executing a full
  wave migration.
- The `system-reminder` does NOT list a skill you know exists under
  `packages/cos-*/skills/` or `skills/extensions/`.

## When NOT to use

- The skill already appears in the `system-reminder` — it is already routed.
- You want to create a new skill from scratch — use `/add-skill`.
- You want to install all recommended skills for a project stack — use
  `/install-recommended --install`.
- The skill lives in an external git repository — clone it first, then use
  `--source`.

## Steps

### 1. Resolve the skill source

Run the backing script in dry-run mode to confirm the source path:

```bash
scripts/cos-install-skill <name> --dry-run
```

The script searches in this priority order:
1. `--source <path>` if provided
2. `packages/cos-*/skills/<name>/`
3. `skills/extensions/<name>/`
4. `skills/<name>/` (present but unlinked)

### 2. Validate the SKILL.md

The script verifies:
- `SKILL.md` exists in the resolved directory
- Frontmatter has required fields: `name`, `description`, `version`
- `name` in frontmatter matches `<name>` argument
- No collision: `.claude/skills/<name>` does not already exist as a valid symlink

### 3. Create the symlink

```bash
scripts/cos-install-skill <name> [--source <path>]
```

This creates `.claude/skills/<name> -> <resolved-source-dir>` as a relative
symlink following the convention of existing skills.

### 4. Register in cognitive-os.yaml (if applicable)

If the skill came from a `packages/cos-*/` pack, the script appends a record
under `extensions:` in `cognitive-os.yaml` so future `apply-efficiency-profile.sh`
runs know which extensions are active.

### 5. Verify

```bash
ls -la .claude/skills/<name>
python3 -c "
import pathlib
p = pathlib.Path('.claude/skills/<name>/SKILL.md')
assert p.exists(), f'SKILL.md not reachable via symlink: {p}'
print('OK')
"
```

### 6. Inform the user

Report:
- Source path resolved
- Symlink created at `.claude/skills/<name>`
- Whether `cognitive-os.yaml` was updated
- Slash command now available: `/<name>`

## Edge cases

| Situation | Behaviour |
|---|---|
| Skill already symlinked | Error: "already installed — use `/add-skill` to author a replacement" |
| SKILL.md missing in source | Error with resolved path; suggest `--source` override |
| Name collision (different source) | Error: diff the two `SKILL.md` files; ask operator which to keep |
| `cognitive-os.yaml` `extensions:` key absent | Script creates the key before appending |
| `--dry-run` | Prints plan; writes nothing |
| Source is outside project root | Error: "source must be within project root (scope violation)" |

## Cross-references

- `/add-skill` — author a new skill from scratch
- `/install-hook` — install an extension hook the same way
- `/install-recommended` — stack-aware bulk recommendations
- `scripts/cos-install-skill` — backing executable
- `docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md` — extension pack taxonomy
- `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` Phase 3 — origin requirement
