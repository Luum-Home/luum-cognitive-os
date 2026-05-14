<!-- SCOPE: both -->
<!-- TIER: 1 -->

# Bash Script Naming — Kebab-Case Required

## Rule

Bash scripts in `scripts/`, `hooks/`, `packages/*/hooks/`, and `packages/*/scripts/`
MUST use kebab-case filenames (lowercase letters, digits, and hyphens between words).
Functions inside `.sh` files MUST use snake_case.

Examples (correct):
- `scripts/cos-bootstrap.sh`
- `hooks/auto-rollback-trigger.sh`
- `scripts/setup.sh` (single word, no separator needed)

Examples (wrong — do not use):
- `cos_bootstrap.sh` — wrong (snake\_case: use hyphens, not underscores)
- `AutoRollbackTrigger.sh` — wrong (PascalCase: use all-lowercase-kebab)

## Rationale

Kebab-case is the Unix/POSIX idiomatic convention for shell tooling names
(`apt-get`, `docker-compose`, `git-config`, `set-up`). Using snake_case for bash
filenames creates visual confusion with Python modules. ADR-066 §4 ratified this
convention to eliminate that ambiguity and prevent the drift that required the
35-file Python rename on 2026-04-24.

## Enforcement

- `tests/audit/test_bash_naming.py` — fails CI if any `*.sh` file in the
  enforced paths has underscores, capital letters, or other non-kebab characters
  in its filename
- Generators (`/add-hook`, `/add-skill`, `/add-rule`) MUST emit kebab-case `.sh`
  filenames when writing new hooks or scripts

## Scope

| Path pattern | Rule | Notes |
|---|---|---|
| `scripts/*.sh` | **MUST** use kebab-case | Enforced by audit test |
| `hooks/*.sh` | **MUST** use kebab-case | Enforced by audit test |
| `packages/*/hooks/*.sh` | **MUST** use kebab-case | Enforced by audit test |
| `packages/*/scripts/*.sh` | **MUST** use kebab-case | Enforced by audit test |
| `scripts/_lib/*.sh` | Exempt | Private subdirs (start with `_`) |
| `hooks/_lib/*.sh` | Exempt | Private subdirs (start with `_`) |

## Functions inside .sh files

Functions MUST use snake_case (POSIX convention — hyphens are invalid in function
names in most shells):

```bash
do_something() { ... }        # correct
setup_git_hooks() { ... }     # correct
DoSomething() { ... }         # wrong (PascalCase)
do-something() { ... }        # wrong (hyphen invalid in POSIX function names)
```

## Generators

When a skill, hook, or script writes a new bash script, derive the filename as:

```bash
# CORRECT — kebab-case for bash scripts
script_name="${feature_name//_/-}.sh"

# WRONG — snake_case looks like a Python module
script_name="${feature_name}.sh"   # if feature_name has underscores
```

## Migration policy

- New files: enforced immediately (audit test blocks CI)
- Existing files: no violations found at rule creation (2026-04-24, 270 scripts
  audited, zero offenders)
- Future renames: per the `rules/python-naming.md` migration pattern — one atomic
  commit renames all files and updates all references simultaneously

## Related

- ADR-066 §4 — polyglot naming conventions per language
- `rules/python-naming.md` — sister rule for Python (snake_case)
- `.github/workflows/go-quality.yml.disabled` — preserved sister enforcement reference for Go (gofmt) after ADR-131 moved CI enforcement local-first
- `tests/audit/test_bash_naming.py` — enforcement test

## Contextual Trigger

- When work relates to Bash Script Naming — Kebab-Case Required.
