# Hook Quality System

> Quality assurance for automatic Cognitive OS hook primitives across Claude
> Code, Codex, governed runners, and future IDEs.

## Why This Exists

Hooks run automatically. They block commands, mutate context, write metrics,
create snapshots, validate agent output, and coordinate concurrent work. If a
hook is slow, stale, miswired, or untested, it can create more problems than it
solves.

The Hook Quality System makes hook quality explicit and enforceable.

## Core Files

| File | Purpose |
|---|---|
| `cognitive-os.yaml` | Canonical hook registry. |
| `manifests/hook-quality.yaml` | Generated quality contract per hook primitive. |
| `scripts/hook_quality_audit.py` | Sync/check command for the manifest and hook scripts. |
| `tests/contracts/test_hook_quality_system.py` | Automated enforcement. |

## Operating Commands

```bash
# Create/update the manifest after adding or changing hook primitives
python3 scripts/hook_quality_audit.py --sync

# Fail if manifest, scripts, tiers, or critical coverage are invalid
python3 scripts/hook_quality_audit.py --check

# Machine-readable report
python3 scripts/hook_quality_audit.py --check --json
```

## Manifest Contract

Each hook entry records:

```yaml
hooks:
  secret-detector:
    script: hooks/secret-detector.sh
    event: PreToolUse
    matcher: Edit|Write
    scope: both
    criticality: security
    max_runtime_ms: 750
    safe_degradation: fail_closed_when_confident_otherwise_warn
    harness_tiers:
      claude: native
      codex: governed
    behavior_tests:
      - tests/chaos/test_secret_detector_exercised.py
```

The manifest is generated, but manual fields such as `manual_tests` and `notes`
are preserved by the sync command.

## Quality Layers

1. **Registry coverage** — every `cognitive-os.yaml > harness.hooks` primitive
   appears in the manifest.
2. **Static syntax** — every registered shell hook passes `bash -n`.
3. **Primitive metadata** — every hook has scope, criticality, safe-degradation,
   and runtime budget.
4. **Harness tier clarity** — Claude/Codex execution mode is explicit:
   `native`, `governed`, `cos_owned`, or `unsupported`.
5. **Critical behavior evidence** — required critical hooks must have automated
   tests discovered in `tests/unit`, `tests/behavior`, `tests/contracts`, or
   `tests/chaos`.
6. **Future SLO path** — `max_runtime_ms` feeds future `cos doctor hooks` and
   release gates.

## Adding or Updating a Hook Primitive

Use this sequence:

```bash
# 1. Edit hook and canonical registry
$EDITOR hooks/example.sh cognitive-os.yaml

# 2. Sync quality metadata
python3 scripts/hook_quality_audit.py --sync

# 3. Add behavior/contract/chaos tests when critical
python3 -m pytest tests/behavior/test_example.py -q

# 4. Enforce the whole hook-quality contract
python3 scripts/hook_quality_audit.py --check
python3 -m pytest tests/contracts/test_hook_quality_system.py -q
```

Do not add a hook only to a driver projection. Driver files are generated or
projected surfaces; `cognitive-os.yaml` and the hook-quality manifest carry the
primitive contract.

## Future Extension

The manifest is intentionally suitable for future `cos doctor hooks` output:

```text
secret-detector: PASS syntax, PASS behavior, claude=native, codex=governed
review-spawner: PASS syntax, WARN behavior-light, claude=native, codex=governed
some-future-ide-hook: UNSUPPORTED cursor
```

The long-term goal is not more hooks. The goal is fewer surprises from the hooks
that are allowed to run automatically.

## Related

- [ADR-114 — Hook Quality System](../adrs/ADR-114-hook-quality-system.md)
- [Harness Driver Parity](harness-driver-parity.md)
- [Codex Governed Tool Layer](codex-governed-tool-layer.md)
