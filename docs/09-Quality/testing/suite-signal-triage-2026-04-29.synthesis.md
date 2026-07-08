---
type: quality-synthesis
source: docs/09-Quality/testing/suite-signal-triage-2026-04-29.md
provenance: "Point-in-time triage record explaining what caused xfail/skip/warning noise in a green test-suite baseline on 2026-04-29, what was fixed, and the resulting testing doctrine."
---

## What it is
A dated triage report (2026-04-29) investigating why a green, non-Docker/non-e2e test-suite run (11825 passed, 1458 skipped, 200 deselected, 18 xfailed, 1 warning) carried significant skip/xfail/warning noise, what was root-caused and fixed, and what doctrine was extracted to prevent recurrence.

## Key mechanics
- **Baseline inspected:** `.cognitive-os/reports/test-runs/20260429T165946Z-tests-m-not-docker-and-not-e2e`.
- **Findings table (signal → cause → action → remaining work):**
  - 18 xfailed: 16 cross-platform shell portability exceptions + 1 crash-recovery SessionStart gap + 1 non-deterministic session-leak SLO contract. Fixed via shebang/path-resolution fixes, wiring snapshot recovery through `session-init.sh`, and injecting a deterministic `ps` fixture. No remaining work for this slice.
  - 1 warning: third-party Authlib deprecation warning, already filtered in pytest config; revisit on Authlib upgrade.
  - ~1148 skipped: `tests/hooks/test_hook_graceful_degradation.py` parametrized every hook × every scenario then skipped irrelevant combos. Fixed by replacing skip-heavy parametrization with scenario-specific fixtures; future hook tests should parametrize by actual hook capability.
  - 97 skipped: MCP direct-import tests skipped whenever `fastmcp` was absent, even for tests not needing MCP transport. Fixed via import-time FastMCP compatibility stubs; CLI transport still fails fast without `fastmcp`. Follow-up: separate transport smoke lane when `fastmcp` is installed.
  - 8 skipped: phase tests only looked for `.cognitive-os/cognitive-os.yaml`, missing this repo's root-level `cognitive-os.yaml`. Fixed with a root-config fallback and universal constitutional-gate context emission. Follow-up: prefer canonical config placement in future install/projection work.
  - ~210 skipped: audit/rules tests intentionally skip grandfathered rule files, rules without hook references, deferred hook registrations, empty research-report parameter sets, and opt-in install flows. Classified as legitimate audit debt, not hidden failure. Follow-up: dedicated cleanup slice converting exemptions to explicit allowlists/reports, migrating grandfathered rules gradually.
- **Verification after fixes** (targeted lane across the affected test files): `1721 passed, 21 skipped in 55.97s` — remaining 21 skips are shebang/portable-helper exemptions from cross-platform discipline tests, not product-behavior skips.
- **Testing doctrine captured (4 rules):** (1) never use `xfail` to permanently hide broken behavior — fix it or make it a deterministic, host-independent contract; (2) never parametrize irrelevant scenarios and call them "skipped" — generate only combinations that actually exercise behavior; (3) never skip direct-import unit tests over a missing optional transport package — stub the transport boundary, reserve the real dependency for a transport smoke lane; (4) intentional legacy-debt skips must stay visible and move toward explicit allowlists/reports rather than scattered `pytest.skip` calls.

## Relations & where used
- `tests/hooks/test_hook_graceful_degradation.py`, `hooks/session-init.sh`, `tests/behavior/test_phase_system.py`, `tests/unit/test_cos_mcp_server.py`, `tests/unit/test_advisor_mcp.py`, `tests/integration/test_mcp_server_functional.py`, `tests/unit/test_cross_platform_discipline.py`, `tests/unit/test_session_leak_detection.py`, `tests/integration/test_compaction_resilience.py::TestCrashRecovery` — the concrete test files/fixtures touched by this triage.
- Feeds testing-quality doctrine that complements `docs/09-Quality/testing/README.md`'s structural-vs-behavioral test policy.

## Status / caveats
- **Dated point-in-time snapshot** (2026-04-29) — the specific counts (11825 passed, 1458 skipped, 18 xfailed) and the "remaining work" column reflect that date's baseline only; later suite runs will have different numbers. Synthesized here as the historical record + doctrine, not as current suite state.
- All "action taken" items are reported as already completed as of this document's writing; only the "remaining work" column items are open.
