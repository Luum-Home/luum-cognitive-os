# Runtime Environment Flags Inventory — 2026-05-05

## Purpose

This note records the baseline state of Cognitive OS runtime flags used to
skip, disable, bypass, allow, force, or opt in to behavior. It was created before
adding `COS_SKIP_DOTENV=1`, then retained as historical context for why a central
flag contract was needed.

## Summary

Cognitive OS already has many runtime flags, but they are documented by
subsystem rather than through one global contract. There is partial
centralization for hook suppression and testing opt-ins; safety bypasses,
optional services, watchdogs, and observability toggles remain distributed
across hooks, scripts, tests, and docs.

## Current flag families

| Family | Examples | Current documentation or implementation anchor |
|---|---|---|
| Hook suppression | `DISABLE_HOOK_BLAST_RADIUS`, `DISABLE_HOOK_RATE_LIMITER`, `DISABLE_HOOK_SEMGREP_SCAN` | `rules/hook-security-profiles.md` |
| Common hook implementation | `check_disabled_env` | `hooks/_lib/common.sh` |
| LLM dispatch | `COS_DISABLE_QWEN`, `COS_FORCE_CLAUDE_PRIMARY`, `COS_DISABLE_LLM_FALLBACK` | `rules/llm-dispatch.md`, `docs/runbooks/llm-dispatch.md` |
| Startup safe mode | `COS_STARTUP_SAFE_MODE`, `COS_DISABLE_SESSIONSTART_HOOKS` | `docs/adrs/ADR-104-startup-circuit-breaker.md` |
| Test opt-ins | `COS_RUN_HEADLESS_SERVICE_DOCKER`, `COS_RUN_DATABASE_CONTAINERS`, `COS_RUN_OPTIONAL_APP_SERVICES` | `docs/testing.md` |
| Safety bypass or allow flags | `COS_ALLOW_CONCURRENT_WRITES`, `COS_ALLOW_DESTRUCTIVE_GIT`, `COS_ALLOW_DIRECT_MAIN` | Distributed in hooks, tests, and docs |
| Optional services and scanners | `SEMGREP_ENABLED`, `AGUARA_ENABLED`, `AGENT_BUS_ENABLED`, `BIFROST_ENABLED` | Distributed in hooks, tests, reports, and subsystem docs |
| Watchdog and observability | `COS_SESSION_WATCHDOG_DISABLE`, `SO_WATCHDOG_DRY_RUN`, `COS_MLFLOW_HOTPATH_ENABLED` | Distributed in watchdog, observability, and test files |

## Existing centralization

### Hook suppression

`DISABLE_HOOK_*` is the most mature pattern. It is documented in
`rules/hook-security-profiles.md` and implemented through
`hooks/_lib/common.sh::check_disabled_env`. The transformation is predictable:
hook names become uppercase and hyphens become underscores.

Example:

```bash
DISABLE_HOOK_BLAST_RADIUS=true
```

### Test opt-ins

Optional and heavy test lanes use `COS_RUN_*` flags documented in
`docs/testing.md`. These flags are explicit opt-ins and prevent Docker,
external services, or heavyweight tests from running in default lanes.

Example:

```bash
COS_RUN_HEADLESS_SERVICE_DOCKER=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_headless_service_drill.py -q -ra
```

### LLM dispatch controls

LLM routing has subsystem-specific kill switches documented in
`rules/llm-dispatch.md` and `docs/runbooks/llm-dispatch.md`.

Examples:

```bash
COS_DISABLE_QWEN=1
COS_FORCE_CLAUDE_PRIMARY=1
COS_DISABLE_LLM_FALLBACK=1
```

## Central contract gap and follow-up

The initial investigation found no single source of truth for all runtime flags.
At that time, the repository did not contain a central artifact such as:

- `manifests/runtime-env-flags.yaml`
- `docs/runtime-env-flags.md`
- `rules/env-flags.md`

That gap is now partially closed by `manifests/runtime-env-flags.yaml` and
`docs/runtime-env-flags.md`. The manifest is a public-flag registry, not an
exhaustive grep dump of every local shell variable.

## Implication for new flags

A new flag such as `COS_SKIP_DOTENV=1` should not be added as an isolated
one-off without documenting which family it belongs to. The likely family is
**secret-loading / local-development credential hygiene**, with these expected
properties:

- default human workflow remains unchanged;
- agents can opt out of reading `.env` indirectly;
- the flag is documented where the smoke script is documented;
- tests prove both the default path and the skip path;
- no secret value is printed, persisted, or inspected by tests.

## Recommended follow-up

1. Keep `manifests/runtime-env-flags.yaml` current for public runtime flags.
2. Keep `docs/runtime-env-flags.md` aligned with the manifest.
3. Maintain a contract test that validates required fields for each public flag:
   name, family, default, allowed values, owner file, documentation link,
   risk level, and whether it can bypass a safety primitive.
4. Keep internal/private helpers such as `_COS_QWEN_DOTENV_LOADED` out of the
   public manifest unless they become supported operator controls.
