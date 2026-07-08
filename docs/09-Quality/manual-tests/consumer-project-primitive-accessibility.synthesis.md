---
type: quality-synthesis
source: docs/09-Quality/manual-tests/consumer-project-primitive-accessibility.md
provenance: "Manual test proving primitive readiness claims are grounded in actual downstream consumer-project projection, not only SO-local documentation."
---

## What it is
A manual test procedure verifying that "primitive is ready" claims made in Cognitive OS docs are backed by evidence of real projection into consumer (downstream) projects — not just internal SO documentation asserting readiness.

## Key mechanics
1. Run automated consumer projection checks: `python3 -m pytest tests/behavior/test_consumer_project_projection.py -q`.
2. Regenerate readiness ledgers via `scripts/primitive_readiness_ledger.py --project-dir . --fail-low-confidence` and per-family via `scripts/primitive_family_readiness_ledger.py --target-family {hooks,skills,rules}`.
3. Inspect `docs/06-Daily/reports/primitive-readiness-ledger-{family}-latest.json` and assert each family's `summary.consumer_accessibility` field is present.
4. For install-regression investigation, manually spin up a temp consumer project: `cos_init.py --default --harness claude` in a `mktemp -d`, then inspect `.cognitive-os` files projected (`find ... -maxdepth 3 -type f`).
5. For any new IDE/harness claim, repeat step 4 with that harness driver and record exactly which files get projected.

## Relations & where used
Feeds the primitive-readiness ledger system (`scripts/primitive_readiness_ledger.py`, `scripts/primitive_family_readiness_ledger.py`) and guards against SO documentation overclaiming harness/IDE support. Related to `first-run-onboarding.md` and `five-minute-demo.md`, which also validate real projection into fresh consumer projects across harness drivers (Claude, Codex).

## Status / caveats
Procedural checklist, no embedded dated run evidence. Explicitly states that any IDE/harness not proven via step 4 "remains documented as not signed rather than implied by SO-local docs" — this is a policy statement worth preserving verbatim in downstream consumers of this synthesis.
