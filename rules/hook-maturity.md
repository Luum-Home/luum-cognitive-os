# Hook Maturity Policy

## Purpose

Guards the graduation path for hook behavior from passive observation to active
blocking. Prevents new hooks from blocking tool execution before false-positive
coverage is established.

## Maturity Levels

| Level | Exit behavior | Operator visibility | Requires |
|-------|--------------|---------------------|---------|
| `observe` | Always exit 0, record evidence | Log only | None |
| `warn` | Always exit 0, emit warning text | Visible to operator | None |
| `block` | May exit 2 to block tool execution | Hard block | Behavior + false-positive tests |
| `emergency` | Blocks in all profiles including `lean` | Hard block | ADR approval + behavior tests |

## Default for New Hooks

New hooks MUST start at `observe` or `warn`. A hook defaults to `observe` unless:

- The author explicitly sets `warn`, `block`, or `emergency`.
- `block` or `emergency` requires at least one behavior test and one
  false-positive test in `hook-quality.yaml`.

This prevents silent promotion of new guards into blocking mode without coverage.

## Where Maturity Lives

The canonical maturity field is `manifests/hook-quality.yaml` under each hook
entry:

```yaml
hooks:
  my-hook:
    maturity: observe          # observe | warn | block | emergency
    bypass_policy: not_required_observe_only
    behavior_tests:
      - tests/behavior/test_my_hook.py
    false_positive_tests: []   # required for block/emergency
    ...
```

The `policy.maturity_values` list in the same file is the allowed-values
contract; the audit test verifies both agree.

## Enforcement

`tests/audit/test_hook_maturity_coverage.py` enforces:

1. Every entry in `hook-quality.yaml` has a `maturity` field.
2. All maturity values are within `{observe, warn, block, emergency}`.
3. `block`/`emergency` hooks have at least one behavior or false-positive test.
4. The `policy.maturity_values` section matches the allowed set exactly.
5. Every `hooks/*.sh` file is either registered in `hook-quality.yaml`
   or classified in `hook-registration-classification.yaml`.
6. Maturity coverage across registered hooks is 100%.

## Graduation Process

1. Ship new hook at `observe` — records evidence, never blocks.
2. After 1+ sprint of production observation with low false-positive rate,
   promote to `warn`. Add behavior tests.
3. After `warn` coverage is confirmed, escalate to `block` with ADR note and
   false-positive tests.
4. `emergency` requires explicit ADR approval and covers only data-loss or
   unsafe-main-landing scenarios.

## Audit Command

```bash
.venv/bin/python -m pytest tests/audit/test_hook_maturity_coverage.py -v
```

## Related

- `manifests/hook-quality.yaml` — per-hook maturity and quality metadata
- `manifests/hook-registration-classification.yaml` — unregistered hook classification
- ADR-124 — distribution tiers
- Operational Stability Phase 2 acceptance verified 2026-05-18

## Contextual Trigger

Load this rule when creating, registering, promoting, or reviewing hook maturity metadata; editing `manifests/hook-quality.yaml`; changing hook block/warn/observe behavior; or adding false-positive coverage for hook gates.
