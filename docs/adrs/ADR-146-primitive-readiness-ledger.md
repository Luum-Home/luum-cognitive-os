# ADR-146: Primitive Readiness Ledger

## Status

Accepted — 2026-05-04

## Context

Cognitive OS already has lifecycle metadata, primitive coverage reports, usage maps, docs execution audits, and gap snapshots. Those tools prove slices of the system, but they do not give future agents a single machine-readable row per automation surface that answers:

- what role does this script play;
- whether it is an agent-facing primitive, maintainer-only tool, migration helper, driver-specific adapter, lab experiment, or archive candidate;
- which evidence caused that classification;
- what the next promotion/demotion action is.

Without that ledger, every cycle re-discovers `scripts/` from scratch and product language can drift toward universal claims before harness support, lifecycle metadata, and proof exist.

## Decision

Add a primitive readiness ledger for scripts as the first family-specific ledger.

Canonical entrypoint:

```bash
python3 scripts/primitive_readiness_ledger.py --project-dir .
```

Canonical generated reports:

- `docs/reports/primitive-readiness-ledger-scripts-latest.json`
- `docs/reports/primitive-readiness-ledger-scripts-latest.md`

The JSON report is the machine-readable surface. Each script row declares:

- `path`
- `role`: `agentic-primitive | maintainer-tool | migration-only | driver-specific | lab | archive`
- `role_source`: lifecycle, override, usage, wrapper, heuristic, or default
- `confidence`
- lifecycle fields when present
- supported harnesses when present
- consumers and consumer families
- evidence signals
- next action

The first implementation classifies every file under `scripts/` except ignored cache/build directories. It does not make low-confidence rows fail by default. Optional fail flags allow future gates to ratchet only when the team is ready:

```bash
python3 scripts/primitive_readiness_ledger.py --fail-low-confidence
python3 scripts/primitive_readiness_ledger.py --fail-agentic-without-lifecycle
```

## Role Semantics

| Role | Meaning | Required next action |
|---|---|---|
| `agentic-primitive` | Intended agent-facing or lifecycle-backed tool. | Add/keep lifecycle metadata, supported harnesses, evidence commands, and package boundary before universal claims. |
| `maintainer-tool` | Useful for SO maintainers but not default project/user surface. | Keep out of default distribution unless promoted through ADR-126 lifecycle. |
| `migration-only` | One-time/backfill/update helper. | Add sunset criteria and archive after retention. |
| `driver-specific` | Harness/IDE adapter or helper. | Declare supported harnesses and fallback behavior. |
| `lab` | Experiment, benchmark, chaos, or sandbox surface. | Keep non-default until proven. |
| `archive` | Dead or superseded surface. | Archive-first and remove active references. |

## Consequences

- Future agents can review `scripts/` without re-reading every file.
- Product claims can be checked against role and lifecycle evidence.
- The ledger creates a ratchet path: start advisory, then fail only on touched rows or chosen role classes.
- Classification remains revisable. A heuristic role is not a permanent decision; it is a visible starting point.

## Alternatives Rejected

- **Only extend `primitive_coverage.py`**: rejected because coverage score is not the same as distribution role or promotion state.
- **Manually maintain a YAML row for all scripts immediately**: rejected because the repo is in reconstruction and a generated first pass prevents stalling on 300+ rows.
- **Fail on all low-confidence rows immediately**: rejected because it would turn a visibility tool into noise before triage.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `python3 scripts/primitive_readiness_ledger.py --project-dir .` writes JSON and Markdown reports.
2. Every file under scripts/ receives one allowed role.
3. The JSON report includes role source, confidence, consumers, evidence, lifecycle fields when present, and next action.
4. Unit tests cover role classification and CLI output.
5. Contract test proves the repository ledger classifies every script row.
```

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_readiness_ledger.py tests/contracts/test_primitive_readiness_ledger_contract.py -q
python3 -m py_compile scripts/primitive_readiness_ledger.py
python3 scripts/primitive_readiness_ledger.py --project-dir .
```

## 2026-05-04 Triage Ratchet Update

The first low-confidence script pass is closed through `manifests/primitive-readiness-script-overrides.yaml`. The default ledger now reports zero low-confidence rows, while keeping 74 `agentic-primitive` rows without lifecycle metadata visible in the generated lifecycle backlog:

- `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json`
- `docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md`

Those backlog rows are not runtime lifecycle entries yet. They are candidate work items that must become ADR-126 metadata rows, be downgraded from `agentic-primitive`, or be archived before shared/harness-portable claims are made.

Family extension is tracked in `docs/architecture/primitive-readiness-ledger-family-extension.md`.
