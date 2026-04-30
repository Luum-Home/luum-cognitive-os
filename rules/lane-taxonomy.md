<!-- SCOPE: os-only -->
# Test Lane Taxonomy

> Source: ADR-072 (`docs/adrs/ADR-072-test-lane-taxonomy.md`).
> Lane registry: `.cognitive-os/test-lanes.yaml` (single source of truth).

## Rule

Every test directory under `tests/` MUST be classified into a lane in
`.cognitive-os/test-lanes.yaml` with an explicit parallel-safety contract
(`parallel: true|false|marker`). The lane assigns a marker that
`tests/conftest.py` injects at collection time, and `cmd/cos-test` is the
canonical entry point for running them (`focused | cluster | broad`). New test
directories without a registered lane fail the lane-registry contract test —
the friction is intentional to prevent silent classification drift.

## Lane registry location

`.cognitive-os/test-lanes.yaml` is the durable lane registry. It is read by
`cmd/cos-test` (Go) and `tests/conftest.py` (Python). The bash wrapper
`scripts/pytest-with-summary.sh` does NOT parse YAML — it receives explicit
`--workers N --lane <name>` from `cos-test` (per ADR-066 polyglot boundary).

## Auto-marker behavior

`tests/conftest.py:pytest_collection_modifyitems` injects path-derived markers
**additively**: any test file under `tests/<dir>/` receives the corresponding
lane marker if it does not already carry one. The mapping (longest-prefix match)
covers nine lanes: `unit`, `audit`, `contract`, `integration-isolated`,
`integration-shared` (via `docker` marker), `behavior`, `hooks`, `e2e`, `chaos`.

The hook is idempotent (re-collection safe) and preserves existing manual
`pytestmark` declarations. `--strict-markers` is enforced — every lane marker
is registered in `pytest.ini`.

## Escalation ladder

Use `cos-test` (canonical CLI). Three modes, in increasing scope:

| Mode | Command | When |
|---|---|---|
| focused | `cos-test focused` | Single-file edit; iteration loop. < 30 s. |
| cluster | `cos-test cluster --lane <name>` | Validate one lane (CI shard, targeted check). < 2 min unit / < 5 min stateful. |
| broad | `cos-test broad` | Pre-push validation; full sweep. < 10 min. |

`cos-test broad` runs lanes in dependency order: parallel-safe group (unit,
audit, contract, integration-isolated) → integration-shared → behavior → hooks
→ e2e → chaos.

## Contributor obligations when adding a new test directory

When adding `tests/<new-dir>/`, you MUST:

1. Decide whether the lane is **parallel-safe** (no shared state, all fixtures
   use `tmp_path`/`monkeypatch`) or **serial** (process-global state, real
   filesystem mutations, session-scoped Docker, hook chains).
2. Add an entry to `.cognitive-os/test-lanes.yaml` with `paths`, `parallel:
   true|false|marker`, `marker_serial` (if `parallel: marker`),
   `stateful_reason` (one-line written justification), and
   `typical_wall_time_s` (from initial measurement).
3. Register the lane marker in `pytest.ini` under `[pytest] markers`.
4. Verify the new lane runs end-to-end via `cos-test cluster --lane <name>`.
5. Verify the audit test `tests/audit/test_marker_coverage.py` passes — every
   test in your new directory must carry the lane marker after auto-injection.

A new lane without a written `stateful_reason` will fail the lane-registry
contract test. The friction is intentional: silent classification drift is what
ADR-072 fixes.

## Cross-references

- **ADR-072** — full decision: `docs/adrs/ADR-072-test-lane-taxonomy.md`.
- **`.cognitive-os/test-lanes.yaml`** — lane registry.
- **ADR-068** — adaptive worker count (consumed by cluster/broad modes).
- **ADR-066** — polyglot language boundaries (YAML read by Go+Python; bash
  receives scalars).
- **`tests/conftest.py`** — auto-marker injection site.
- **`pytest.ini`** — marker registry.
