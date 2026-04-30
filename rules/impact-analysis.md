<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Change Impact Analysis Protocol

## Purpose

Before making changes, understand the blast radius: which files import the changed code, which tests cover it, which services are affected, and what risk level the change carries. This prevents "works on my file" blindness where agents modify code without understanding downstream effects.

## When to Run Impact Analysis

| Trigger | Requirement |
|---------|-------------|
| Before `sdd-apply` on large/critical changes | MUST run |
| Before any multi-service change | SHOULD run |
| After unexpected test failures | SHOULD run to find root cause |
| Before refactoring shared code | MUST run |
| User invokes `/impact-analysis` | Always |

## Analysis Dimensions

| Dimension | What It Checks | Why It Matters |
|-----------|---------------|----------------|
| Direct importers | Files that import/require the changed files | Identifies the blast radius — who breaks if you break this |
| Test coverage | Test files that exercise the changed code | Ensures all affected tests are run |
| Config dependencies | YAML/JSON/TOML files referencing changed files | Prevents config drift |
| Docker services | Services whose build context includes changed files | Identifies which containers need rebuilding |
| SDD artifacts | Specs/designs that reference changed files | Ensures documentation stays in sync |

## Risk Classification

| Level | Criteria | Action |
|-------|----------|--------|
| LOW | < 5 importers, single service, tests exist | Proceed normally |
| MEDIUM | 5-10 importers, or no test coverage, or multi-service | Review affected tests, run explicitly |
| HIGH | > 10 importers, > 2 services, or auth/security paths | Consider splitting the change |
| CRITICAL | Payment/billing/crypto paths, or docker-compose/.env changes | HALT — human review required |

## Integration with SDD

Impact analysis integrates with the SDD pipeline at two points:

1. **Pre-apply**: Run on files listed in the tasks artifact to estimate risk before implementation
2. **Post-apply**: Run on actually changed files to validate the blast radius matches expectations

If post-apply risk is significantly higher than pre-apply risk, the verify phase should flag this as a concern.

## Lib Module

The analysis logic lives in `lib/impact_analysis.py`:

- `analyze_impact(changed_files, project_dir) -> ImpactReport`
- `format_impact_report(report) -> str`
- `classify_risk(files, importers, tests, services) -> (RiskLevel, reasons)`

## Contextual Trigger

This rule is loaded when: impact analysis, blast radius, change scope, affected files, risk assessment.
