# Project Gotchas — Read BEFORE acting

> Compact index of traps that have broken agents. ~30 lines, ~500 tokens.
> Injected into sub-agent prompts when working on COS internals.

## Architecture traps

- **lib/*.py are SYMLINKS** → `packages/*/lib/*.py`. Never replace package files. Verify: `ls -la lib/<file>.py`
- **settings.json is GENERATED** by `scripts/apply-efficiency-profile.sh`. Never edit directly. Update the script, then run it.
- **.cognitive-os/ = OS kernel** (universal). **.claude/ = driver** (Claude Code-specific). Don't mix.
- **48/93 hooks are intentionally not wired** — controlled by efficiency profile (lean=7, standard=18, full=all). This is by design, not a bug.

## Before modifying

| If touching... | First read... | Because... |
|---|---|---|
| `lib/*.py` | `ls -la lib/<file>` | May be a symlink to packages/ |
| `.claude/settings.json` | `scripts/apply-efficiency-profile.sh` | Script regenerates the file |
| `hooks/*.sh` (new) | `scripts/apply-efficiency-profile.sh` | Must add hook to a profile tier |
| `packages/*/lib/*.py` | `ls -la lib/` for symlinks | lib/ symlinks point here |
| `.cognitive-os/workflows/` | `docs/adw-patterns.md` | Defines the YAML schema |
| `cognitive-os.yaml` | Current value first (`grep` it) | Don't duplicate existing sections |
| `rules/*.md` | `rules/RULES-COMPACT.md` | May already be covered |

## Common false positives

- "lib/ and packages/ have duplicate files" → **symlinks**, not duplicates
- "48 hooks are dead" → **efficiency profile**, not a bug
- "plans/ directory is empty" → plans live in `.cognitive-os/plans/` currently
- "No tests for lib/X" → check `tests/unit/test_X.py` AND `tests/behavior/`

## Verification commands

```bash
# Check symlink status
find lib/ -type l | wc -l          # should be >40

# Check current efficiency profile  
grep "profile:" cognitive-os.yaml  # lean|standard|full

# Check hook wiring count
grep -c '"command":' .claude/settings.json

# Verify lib/ imports
python3 -c "from lib.<module> import <class>"
```
