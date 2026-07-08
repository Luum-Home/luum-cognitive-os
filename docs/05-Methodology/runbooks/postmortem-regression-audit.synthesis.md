---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/postmortem-regression-audit.md
provenance: "Documents the read-only detector for the bug classes captured in ADR-242 through ADR-246, establishing detect-first-repair-second as the required workflow before any agent touches the affected local primitives."
---

## What it is

Runbook for `scripts/cos-postmortem-regression-audit`, a read-only detector that reports current incoherence for five specific bug classes (ADR-242 through ADR-246) before repairs are made.

## Key mechanics

- Scope table maps each ADR to the class it detects: ADR-242 (direct `git filter-repo` callsites bypassing the governed wrapper), ADR-243 (push-collision detector missing post-rewrite marker support), ADR-244 (trust-report claims scored/advised without enforceable verification), ADR-245 (chaos lane lacking a read-only source guard or writing protected source directly), ADR-246 (release transaction freeze artifacts missing).
- Usage: `scripts/cos-postmortem-regression-audit --json`, `--strict`, plus a unit test at `tests/unit/test_postmortem_regression_audit.py`.
- Policy: the audit never modifies hooks, scripts, history, branches, remotes, or tests; findings are resolved in separate commits referencing the finding code; a finding may only be downgraded with a documented manifest/runbook rationale; the audit must never be made green by deleting evidence or weakening detection patterns.
- As of the 2026-05-08 session, the audit is *expected* to report blockers because ADR-242–246 were newly proposed/partially implemented — that non-green baseline is itself the proof the detector can see the classes before repairs land.
- ADR-247 sets the long-term contract as manifest-driven: the script stays a generic engine, while ADR mapping, paths, forbidden patterns, required artifacts, and external-tool adapter declarations move into `manifests/postmortem-regression-audit.yaml`. Sensitive values must live in env-var names or gitignored local manifests, never hardcoded.
- Recommended external-tool stance: adopt mature tools (Gitleaks, TruffleHog, git-filter-repo, pre-commit, Conftest/OPA, GitHub branch protection) as declared adapters with owner/license/callers/failure-policy/recursion-boundary/sanitization metadata, rather than rebuilding them inside COS.

## Relations & where used

Directly tied to ADR-242 through ADR-247; the manifest-driven direction connects to the broader manifest-loader pattern used elsewhere in dependency/tooling declarations (e.g. `manifests/dependencies.yaml`).

## Status / caveats

The "Current expected state" section is a dated point-in-time note (2026-05-08 session) describing an intentionally non-green baseline — read it as a snapshot, not a permanent expectation. ADR-247's manifest migration is described as the long-term contract but the runbook does not state whether `manifests/postmortem-regression-audit.yaml` exists yet; treat that section as forward-looking design intent.
