# Runbook — land the conditional structural-discovery rule

**Date:** 2026-08-15 · **Decision:** ADR-343 · **Status:** waiting for operator

## What this is

`rules/**` is a protected control-plane path (`hooks/protected-config-write-guard.sh`),
and the approval env var does not reach an agent, because the guard runs in its
own process before the agent's command. So the rule file ships here as a patch
instead of being written directly. Same shape as
`gate-exit-code-contract-2026-08-15/`.

The script the rule depends on is **already landed and runnable** —
`scripts/check_codebase_memory_readiness.py`. Only the rule text is blocked.

## Why this rule exists

A directive of the form *"ALWAYS use codebase-memory-mcp tools FIRST"* currently
lives in the operator's own profile, outside this repo, and is **unconditional**.
Measured on 2026-08-15, this repository is **not** in the server's graph:

```bash
python3 scripts/check_codebase_memory_readiness.py
# NOT_READY: codebase-memory-mcp
#   server present    True
#   project indexed   False
#   projects in graph 8
# exit 1
```

So the directive as written orders an agent to consult an empty graph before
grepping. The rule makes it conditional on the graph actually holding this
project. That is a defect fix, not an adoption — nothing external is vendored.

## Apply

```bash
git apply --check docs/05-Methodology/runbooks/codebase-memory-directive-2026-08-15/conditional-directive.patch
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 git apply \
  docs/05-Methodology/runbooks/codebase-memory-directive-2026-08-15/conditional-directive.patch
```

`git apply` writes through the filesystem, not the agent tool layer, so the
PreToolUse guard is not involved; the env var is shown for consistency with the
review trail the guard asks for.

## Verify after applying

```bash
test -f rules/codebase-memory-directive.md && echo "rule present"
python3 scripts/check_codebase_memory_readiness.py --explain   # exit 0
python3 scripts/check_codebase_memory_readiness.py             # exit 1 here, 0 on an indexed repo
```

## Not included on purpose

- **No `rules/RULES-COMPACT.md` entry.** That file is protected too and is
  edited by concurrent sessions; adding an index line is a separate, conflict-prone
  edit. Until it is added, the rule is on disk but not indexed — say so rather
  than assume discovery.
- **No hook.** Nothing enforces the precondition mechanically; the rule is
  advisory and the script is the evidence. Making it a gate is a separate
  decision with its own blast radius.
