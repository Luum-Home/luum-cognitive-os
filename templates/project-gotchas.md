<!-- SCOPE: os-only -->

# Project Gotchas — Read BEFORE acting

> Compact index of traps that have broken agents.
> Injected into sub-agent prompts when working on COS internals.
>
> Every number below carries the command that produced it, and the date it was
> last run. A number without its command is an opinion with digits: it cannot be
> rechecked, so it rots silently. Re-run the command before repeating the figure.

## Architecture traps

- **There is no `lib/` at the repo root** — the package directory is `cos_lib/`. `ls -d lib` returns "No such file or directory" (checked 2026-08-15). Any instruction, doc or script that says `lib/*.py` predates the rename; read it as `cos_lib/*.py`.
- **cos_lib/ has TWO symlink layers** — `ls -la cos_lib/<file>` AND `ls -la cos_lib/<dir>/` BEFORE acting:
  - **File-level** (the minority): some `.py` files are symlinks into `packages/*/lib/` — count them below; the DEFAULT case is a real file. Examples, re-measured 2026-08-20 — symlinks: `cos_lib/batch_runner.py` `cos_lib/ground_truth.py` `cos_lib/cost_predictor.py`; not a symlink: `cos_lib/peer_card.py`. Never assume; check.
    ```bash
    find cos_lib -name '*.py' -type l | wc -l    # symlinked .py
    find cos_lib -name '*.py' | wc -l            # total .py
    ```
  - **Directory-level**: three whole directories are symlinks — `cos_lib/harness_adapter/` → `packages/agent-lifecycle/lib/harness_adapter`, `cos_lib/event_projections/` → `packages/agent-lifecycle/lib/event_projections`, `cos_lib/providers/` → `packages/llm-providers/lib`. Mutations in `cos_lib/harness_adapter/X.py` land in `packages/agent-lifecycle/lib/harness_adapter/X.py` directly. **Do NOT** `rm + ln -s` "to recreate the symlink" — relative targets resolve from the symlink's TARGET, not its literal path → broken/looped. Enumerate with `find cos_lib -maxdepth 1 -type l -exec sh -c 'test -d "$1" && echo "$1 -> $(readlink "$1")"' _ {} \;`, or `bash scripts/topology-discover.sh` for the full topology. (See 2026-05-02 incident. This IS blocked, exit 2, by `hooks/symlink-mutation-guard.sh` — which runs from `hooks/bash-hot-path-dispatcher.sh`, not as its own `.claude/settings.json` entry, so `grep -c` over that file returns 0 and proves nothing. It fires only when the `ln -s` target is RELATIVE and the link's parent chain contains a symlink; recreating a top-level dir symlink is not caught. Verify by running the hook with the payload on stdin, never by grepping a registry.)
- **A yaml entry alone does not make a hook fire.** This entry used to say the registry was `cognitive-os.yaml > harness.hooks`, projected by the driver. True for the bare, codex and opencode harnesses; **false for Claude Code**, whose driver (`scripts/_lib/settings-driver-claude-code.sh`) holds the registry HARDCODED as shell literals — its own header says so, after `CONFIG_FILE` was found assigned and never read. Strip the comments and exactly one yaml reference survives, and it is a `[ -f ]` to locate the repo root. The surfaces that decide reachability are kept in step **by hand**, so a hook can be declared and never run: do NOT cite a live orphan from memory, and do not cite a count of them either — run the gate. Most of what it reports as lost is declared somewhere the gate does not read. **Do not count the surfaces by hand and do not trust a number written in prose**. Run the gate: `.venv/bin/python3 scripts/audit_hook_registration.py` — exit 1 means a declared hook is unreachable, its absence undeclared, and never observed running; it names the surfaces it checked and the fix. Still never hand-edit `.claude/settings.json`: it is generated.
- **.cognitive-os/ = OS kernel** (universal). **.claude/ = driver** (Claude Code-specific). Don't mix.
- **Not every hook script is wired** — count them with the commands below; the unregistered ones are gated by the efficiency profile. This is by design, not a bug. ADR-093 collapsed the old naming, but the driver is NOT two-tier: `scripts/apply-efficiency-profile.sh` still accepts the old spellings and resolves every one of them onto one of three tiers, in the case arm's own order: core maintainer full. `default` — what `cognitive-os.yaml` carries — resolves to `maintainer`, and `lean`/`standard`/`minimal` resolve there too with a note on stderr. Read the tiers off the case arm, do not quote this list:
  ```bash
  grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l
  ls hooks/*.sh | wc -l
  grep -A2 '^efficiency:' cognitive-os.yaml | grep 'profile:'   # the spelling in config
  # the tiers that spelling can resolve to — the arm that keeps the name it was given
  awk '/^case "\$RAW_PROFILE" in/{c=1} c&&/^[[:space:]]*[a-z|]+\)/{l=$0} c&&/PROFILE="\$RAW_PROFILE"/{gsub(/[^a-z|]/,"",l); print l; exit}' scripts/apply-efficiency-profile.sh
  ```

## Before modifying

| If touching... | First read... | Because... |
|---|---|---|
| `cos_lib/*.py` | `ls -la cos_lib/<file>` | May be a symlink to packages/ |
| `.claude/settings.json` | the surfaces that decide reachability, kept in step BY HAND | Generated — never hand-edit. But the Claude Code driver does **not** read `cognitive-os.yaml`: its registry is hardcoded. See the registration entry above |
| `hooks/*.sh` (new) | `cognitive-os.yaml` **and** the Claude Code driver **and** `apply-efficiency-profile.sh` **and** the three security-profile templates | The yaml alone is not enough for Claude Code — the hook will exist and never fire. Run `scripts/audit_hook_registration.py` before believing it is registered |
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
# Symlink status of cos_lib — symlinked .py (total: find cos_lib -name '*.py' | wc -l)
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
