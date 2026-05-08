# Postmortem Regression Audit Runbook

`scripts/cos-postmortem-regression-audit` is a read-only detector for the bug classes captured in ADR-242 through ADR-246.

It exists because the correct workflow is **detect first, repair second**. The tool must be able to report current incoherence before any agent fixes the local primitive.

## Scope

| ADR | Class detected |
|---|---|
| ADR-242 | direct `git filter-repo` callsites and missing governed wrapper |
| ADR-243 | push-collision detector missing post-rewrite marker support |
| ADR-244 | trust report claims scored/advised without enforceable verification |
| ADR-245 | chaos lane lacks read-only source guard or writes protected source directly |
| ADR-246 | release transaction freeze artifacts missing |

## Usage

```bash
scripts/cos-postmortem-regression-audit --json
scripts/cos-postmortem-regression-audit --strict
python3 -m pytest tests/unit/test_postmortem_regression_audit.py -q
```

## Policy

- The audit does not modify hooks, scripts, history, branches, remotes, or tests.
- Findings should be resolved in separate commits that reference the finding code.
- A finding may be downgraded only with a manifest/runbook rationale explaining why the state is intentional.
- Do not make the audit green by deleting evidence or weakening patterns.

## Current expected state

During the 2026-05-08 implementation session the audit is expected to report blockers because ADR-242 through ADR-246 are newly proposed/partially implemented. That non-green result is useful: it is the baseline proving the detector sees the classes before repairs land.
