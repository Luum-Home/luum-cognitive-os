# Suite Signal Triage — xfail, warnings, and skipped tests

> Date: 2026-04-29  
> Baseline inspected: `.cognitive-os/reports/test-runs/20260429T165946Z-tests-m-not-docker-and-not-e2e`  
> Baseline result: `11825 passed, 1458 skipped, 200 deselected, 18 xfailed, 1 warning`.

## Why This Exists

The broad non-Docker/non-e2e lane was green, but the signal was noisy. A green
suite with many `skipped`, `xfailed`, or warning entries can hide product debt.
This triage records what was real, what was test-shape noise, and what still
needs a follow-up slice.

## Findings

| Signal | Baseline Cause | Action Taken | Remaining Work |
|---|---|---|---|
| `18 xfailed` | 16 cross-platform shell portability exceptions, 1 crash-recovery SessionStart gap, 1 session-leak SLO contract that depended on live host state. | Removed the xfail debt by fixing shebangs/path resolution, wiring snapshot recovery through `session-init.sh`, and making the leak SLO deterministic with an injected ps fixture. | None for this slice. |
| `1 warning` | Third-party Authlib deprecation warning from transitive dependency import path. | Already filtered in pytest config before this slice; targeted warning lane stays clean. | Revisit when Authlib dependency is upgraded. |
| ~1148 skipped | `tests/hooks/test_hook_graceful_degradation.py` parametrized every hook into every scenario, then skipped irrelevant hooks inside each test. | Replaced skip-heavy parametrization with scenario-specific fixtures. Irrelevant combinations are no longer generated. | Keep new hook graceful-degradation tests parametrized by actual hook capability. |
| 97 skipped | MCP direct-import tests skipped whenever `fastmcp` was not installed, even though the tests do not need MCP transport. | Added import-time FastMCP compatibility stubs for direct tool tests; CLI transport still fails fast when run without `fastmcp`. | Add a separate transport smoke lane when `fastmcp` is installed. |
| 8 skipped | Phase tests looked only for `.cognitive-os/cognitive-os.yaml`; this repo currently keeps the root `cognitive-os.yaml`. | Added root-config fallback and made the phase hook emit universal constitutional-gate context even when project-specific gates are absent. | Prefer canonical config placement in future install/projection work. |
| ~210 skipped | Audit/rules tests intentionally skip grandfathered rule files, rules without hook references, deferred hook registrations, empty research-report parameter sets, and opt-in install flows. | Classified as remaining audit debt rather than hidden failure. | Dedicated rules-audit cleanup slice: convert intentional exemptions to explicit allowlists/reports and migrate grandfathered rules gradually. |

## Verification

Targeted validation after the fixes:

```bash
python3 -m pytest \
  tests/unit/test_cross_platform_discipline.py \
  tests/unit/test_session_leak_detection.py \
  tests/integration/test_compaction_resilience.py::TestCrashRecovery \
  tests/hooks/test_hook_graceful_degradation.py \
  tests/behavior/test_phase_system.py \
  tests/unit/test_cos_mcp_server.py \
  tests/unit/test_advisor_mcp.py \
  tests/integration/test_mcp_server_functional.py \
  -q -ra -rxX
```

Result:

```text
1721 passed, 21 skipped in 55.97s
```

The remaining 21 skips in this targeted lane are library-file shebang exemptions
and portable-helper exemptions from cross-platform discipline tests. They are not
product behavior skips.

## Testing Doctrine Captured

1. Do not use `xfail` to permanently hide broken product behavior. Fix it or
   convert it into a deterministic contract that does not depend on local host
   state.
2. Do not parametrize irrelevant scenarios and call them skipped. Generate only
   the combinations that are supposed to exercise behavior.
3. Do not skip direct-import unit tests because an optional transport package is
   missing. Stub the transport boundary and reserve the real dependency for a
   transport smoke lane.
4. If a skipped test represents intentional legacy debt, keep the reason visible
   and move it toward an explicit allowlist/report instead of leaving it as
   scattered `pytest.skip` noise.
