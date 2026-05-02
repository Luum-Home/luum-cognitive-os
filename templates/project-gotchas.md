<!-- SCOPE: project -->

# Project Gotchas — Read BEFORE acting

> Compact index of traps that have broken agents. ~30 lines, ~500 tokens.
> Injected into sub-agent prompts when working on COS internals.

## Architecture traps

- **lib/ has TWO symlink layers** — `ls -la lib/<file>` AND `ls -la lib/<dir>/` BEFORE acting:
  - **File-level** (most): `lib/ground_truth.py`, `lib/peer_card.py`, etc. → `packages/<pkg>/lib/<file>.py`
  - **Directory-level**: `lib/harness_adapter/` → `packages/agent-lifecycle/lib/harness_adapter/` (the WHOLE directory is a symlink). Mutations in `lib/harness_adapter/X.py` affect `packages/agent-lifecycle/lib/harness_adapter/X.py` directly. **Do NOT** `rm + ln -s` "to recreate the symlink" — relative targets resolve from the symlink's TARGET, not its literal path → broken/looped. Run `bash scripts/topology-discover.sh` for full topology. (See 2026-05-02 incident; `hooks/symlink-mutation-guard.sh` blocks the pattern.)
  - **Other dir-symlinks**: `lib/providers/` → `packages/llm-providers/lib/`
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
| `scripts/orchestrator.py` or `lib/dispatch.py` | `rules/llm-dispatch.md` + ADR-049 | Sub-agents dispatched via our orchestrator default to **Qwen primary**, Claude fallback. Preserves Claude Max quota for main chat. Native `Agent()` tool still uses Claude Max. Kill-switches: `COS_DISABLE_LLM_FALLBACK=1`, `COS_FORCE_CLAUDE_PRIMARY=1`. Qwen Pro ToS: interactive-only, NO cron/backend. |

## Common false positives

- "lib/ and packages/ have duplicate files" → **symlinks**, not duplicates
- "48 hooks are dead" → **efficiency profile**, not a bug
- "No tests for lib/X" → check `tests/unit/test_X.py` AND `tests/behavior/`
- "How do I add OpenCode/Cursor/Aider/Continue support?" → **do NOT fork the hook chain**. Subclass `HarnessAdapter` in `lib/harness_adapter/`, register in `dispatch.py`. See `docs/guides/adding-a-harness-adapter.md` and ADR-033.

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
