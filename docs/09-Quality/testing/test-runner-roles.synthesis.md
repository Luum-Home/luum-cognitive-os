---
type: quality-synthesis
source: docs/09-Quality/testing/test-runner-roles.md
provenance: "Defines the canonical role taxonomy (selection/execution/reporting/governance/lifecycle) for Cognitive OS test tooling so new contributors pick the right entry point instead of ad-hoc scripts."
---

## What it is
An active operational guide (source of truth: ADR-072 and `.cognitive-os/test-lanes.yaml`) that splits Cognitive OS test tooling by role, so the product doesn't present every script as a generic "run everything" entry point. Answers: what test scope to select, and which primitive executes/persists it.

## Key mechanics
- **Five-role model:**
  - **Selection** — decide scope (focused diff / one lane / broad sweep / optional lanes). Owned by `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cos-test focused/cluster/broad`.
  - **Execution** — run the selected set with correct worker policy. Owned by `cmd/cos-test` (the user-facing entry point).
  - **Reporting** — persist summaries/failures/JUnit/coverage/quality artifacts and run history. Owned by `scripts/pytest-with-summary.sh`, `tests/coverage-report.sh`, `scripts/cos_test_quality_audit.py` — transport/reporting primitives that must not own lane policy.
  - **Governance** — enforce Definition of Done, coverage, auto-verify, quality gates, budgets via hooks/skills (`auto-verify`, `dod-gate`, `pre-commit-gate`, `coverage-enforcement`, `test-quality-audit`) — consumes persisted evidence, doesn't duplicate selection/execution.
  - **Lifecycle** — track quality ratchets, baselines, repair ledgers, historical drift via metrics JSONL/baselines/repair ledgers.
- **Canonical developer flow table** maps situation → command → rationale: tight iteration → `cos-test focused`; validate one lane → `cos-test cluster --lane <name>`; laptop-friendly broad → `make test-laptop`; local broad without Docker → `cos-test broad --no-docker` / `make test-local-wide-no-docker`; CI/pre-merge default → `cos-test broad --no-docker --ci` / `make test-ci-default`; release gate → `make test-release`; slow integration without Docker → `cos-test cluster --lane integration` / `make test-integration-no-docker`; lower-priority laptop integration → `make test-laptop-integration`; Docker/e2e explicit → `make test-docker`; cost-bearing/non-deterministic lanes → `make test-optional`; raw persisted pytest artifacts → `bash scripts/pytest-with-summary.sh -- <args>` (fallback, not primary UX).
- **Legacy/compatibility scripts table:** `scripts/cos-smoke.sh` (opt-in startup smoke), `scripts/test-cognitive-os.sh` (legacy Layer-1 shell runner → use `cos-test cluster --lane hooks`), `scripts/test-cognitive-os-full.sh` (legacy 3-layer pyramid → use `cos-test broad`), `scripts/test-all.sh` (legacy composite → use `cos-test focused/cluster/broad`), `scripts/run-all-tests.sh` (release/integrity sweep, not for daily iteration), `Makefile test-no-docker-*` (deprecated CI shims proxying to `cos-test`, kept one release cycle).
- **Five non-duplication rules:** selection policy lives only in `.cognitive-os/test-lanes.yaml` + `cos-test`; execution UX lives only in `cmd/cos-test`; reporting is split by concern (`pytest-with-summary.sh` / `coverage-report.sh` / `cos_test_quality_audit.py`); governance hooks consume persisted artifacts under `.cognitive-os/reports/{test-runs,coverage,test-quality}/` (ideally via `scripts/cos_test_artifact_status.py`) rather than re-implementing lane selection or launching broad scans directly; legacy scripts must declare `ROLE` and `CANONICAL` headers.
- **Acceptance criteria for future tooling:** new test directories must map to a lane; new runner-like scripts must declare role + canonical entry point; new governance hooks must consume existing summaries (or document why not); optional/cost-bearing lanes must never run in default broad sweep.

## Relations & where used
- `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cmd/cos-test` — the concrete selection/execution primitives this taxonomy governs.
- `scripts/pytest-with-summary.sh`, `tests/coverage-report.sh`, `scripts/cos_test_quality_audit.py`, `scripts/cos_test_artifact_status.py` — reporting-layer scripts.
- ADR-072 — the architectural decision this doc operationalizes.
- `docs/04-Concepts/architecture/validation-nervous-system.md` — linked as the "full Cognitive OS maintainer doctrine" for validation.
- `docs/09-Quality/testing/README.md` — the broader testing guide whose raw pytest/go-test commands this taxonomy supersedes as the canonical developer-facing wrapper.

## Status / caveats
- Marked "Active operational guide" (not dated/point-in-time) — treated as a living policy document rather than a snapshot.
- No internal inconsistencies noted; the doc is prescriptive/normative rather than reporting current numeric state.
