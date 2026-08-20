<!-- SCOPE: os-only -->

# Project Gotchas — Read BEFORE acting

> Compact index of traps that have broken agents. ~30 lines, ~500 tokens.
> Injected into sub-agent prompts when working on COS internals.
>
> Every number below carries the command that produced it, and the date it was
> last run. A number without its command is an opinion with digits: it cannot be
> rechecked, so it rots silently. Re-run the command before repeating the figure.

## Architecture traps

- **There is no `lib/` at the repo root** — the package directory is `cos_lib/`. `ls -d lib` returns "No such file or directory" (checked 2026-08-15). Any instruction, doc or script that says `lib/*.py` predates the rename; read it as `cos_lib/*.py`.
- **cos_lib/ has TWO symlink layers** — `ls -la cos_lib/<file>` AND `ls -la cos_lib/<dir>/` BEFORE acting:
  - **File-level** (the minority): 70 of 369 `.py` files are symlinks into `packages/*/lib/` — 19.0%, so the DEFAULT case is a real file. Examples that are symlinks today: `cos_lib/batch_runner.py`, `cos_lib/ground_truth.py`, `cos_lib/cost_predictor.py`. `cos_lib/peer_card.py` is NOT one — it is a regular file. Never assume; check.
    ```bash
    # 70 / 369 = 19.0% as of 2026-08-15
    find cos_lib -name '*.py' -type l | wc -l    # symlinked .py
    find cos_lib -name '*.py' | wc -l            # total .py
    ```
  - **Directory-level**: three whole directories are symlinks — `cos_lib/harness_adapter/` → `packages/agent-lifecycle/lib/harness_adapter`, `cos_lib/event_projections/` → `packages/agent-lifecycle/lib/event_projections`, `cos_lib/providers/` → `packages/llm-providers/lib`. Mutations in `cos_lib/harness_adapter/X.py` land in `packages/agent-lifecycle/lib/harness_adapter/X.py` directly. **Do NOT** `rm + ln -s` "to recreate the symlink" — relative targets resolve from the symlink's TARGET, not its literal path → broken/looped. Enumerate with `find cos_lib -maxdepth 1 -type l -exec sh -c 'test -d "$1" && echo "$1 -> $(readlink "$1")"' _ {} \;`, or `bash scripts/topology-discover.sh` for the full topology. (See 2026-05-02 incident; `hooks/symlink-mutation-guard.sh` blocks the pattern.)
- **Registering a hook for Claude Code takes SIX files, not one.** This entry used to say the registry was `cognitive-os.yaml > harness.hooks`, projected by the driver. That is true for the bare, codex and opencode harnesses (their drivers reference the yaml 6, 5 and 15 times). **Claude Code is the exception**: `scripts/_lib/settings-driver-claude-code.sh` holds the registry HARDCODED as shell literals and does not read the yaml — its own header says so in capitals, after `CONFIG_FILE` was found assigned and never read. A hook added only to the yaml **never reaches Claude Code, and nothing reports it**. The live case, measured 2026-08-19: `hooks/publication-safety.sh` is declared in the yaml with `scope: both` and no opt-out, and is absent from `.claude/settings.json`, absent from `hooks/bash-hot-path-dispatcher.sh`, with 0 firings. Counter-check with a hook that does fire — `concurrent-write-guard` appears in `cognitive-os.yaml`, `scripts/_lib/settings-driver-claude-code.sh`, `scripts/apply-efficiency-profile.sh` and the three `templates/security-profiles/*.json`. Still never hand-edit `.claude/settings.json`: it is generated. Verify with `grep -c '<hook-name>' cognitive-os.yaml scripts/_lib/settings-driver-claude-code.sh scripts/apply-efficiency-profile.sh templates/security-profiles/*.json` — a working hook is present in all six.
- **.cognitive-os/ = OS kernel** (universal). **.claude/ = driver** (Claude Code-specific). Don't mix.
- **Most hook scripts are intentionally not wired** — 154 of 257 are registered; the rest are gated by the efficiency profile. This is by design, not a bug. Since ADR-093 the profile is two-tier (`default | full`), not the old lean/standard/full.
  ```bash
  # 154 registered / 257 present as of 2026-08-15
  grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l
  ls hooks/*.sh | wc -l
  grep -A2 '^efficiency:' cognitive-os.yaml | grep 'profile:'
  ```

## Before modifying

| If touching... | First read... | Because... |
|---|---|---|
| `cos_lib/*.py` | `ls -la cos_lib/<file>` | May be a symlink to packages/ |
| `.claude/settings.json` | six surfaces, kept in step BY HAND | Generated — never hand-edit. But the Claude Code driver does **not** read `cognitive-os.yaml`: its registry is hardcoded. See the registration entry above |
| `hooks/*.sh` (new) | `cognitive-os.yaml` **and** the Claude Code driver **and** `apply-efficiency-profile.sh` **and** the three security-profile templates | The yaml alone is not enough for Claude Code — the hook will exist and never fire. Verify presence in all six before believing it is registered |
| `packages/*/lib/*.py` | `ls -la cos_lib/` for symlinks | cos_lib/ symlinks point here |
| `.cognitive-os/workflows/` | `docs/08-References/root/adw-patterns.md` | Defines the YAML schema |
| `cognitive-os.yaml` | Current value first (`grep` it) | Don't duplicate existing sections |
| `rules/*.md` | `rules/RULES-COMPACT.md` | May already be covered |
| `scripts/orchestrator.py` or `cos_lib/dispatch.py` | `rules/llm-dispatch.md` + ADR-049 | Sub-agents dispatched via our orchestrator default to **Qwen primary**, Claude fallback. Preserves Claude Max quota for main chat. Native `Agent()` tool still uses Claude Max. Kill-switches: `COS_DISABLE_LLM_FALLBACK=1`, `COS_FORCE_CLAUDE_PRIMARY=1`. Qwen Pro ToS: interactive-only, NO cron/backend. |

## Common false positives

- "cos_lib/ and packages/ have duplicate files" → **symlinks**, not duplicates
- "these hooks are dead" → **efficiency profile**, not a bug
- "No tests for cos_lib/X" → check `tests/unit/test_X.py` AND `tests/behavior/`
- "How do I add OpenCode/Cursor/Aider/Continue support?" → **do NOT fork the hook chain**. Subclass `HarnessAdapter` in `cos_lib/harness_adapter/`, register in `dispatch.py`. See `docs/05-Methodology/guides/adding-a-harness-adapter.md` and ADR-033.

## Verification commands

```bash
# Symlink status of cos_lib (70 of 369 .py were symlinks on 2026-08-15)
find cos_lib -name '*.py' -type l | wc -l

# Drift between a cos_lib symlink and its packages/ target
python3 scripts/cos_lib_symlink_invariant_audit.py

# Current efficiency profile (default | full — ADR-093)
grep -A2 '^efficiency:' cognitive-os.yaml | grep 'profile:'

# Hook wiring count
grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l

# Verify a cos_lib import resolves
python3 -c "from cos_lib.<module> import <class>"
```
