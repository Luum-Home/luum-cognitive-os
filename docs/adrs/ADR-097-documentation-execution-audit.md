# ADR-097: Documentation Execution Audit

- Status: Accepted
- Date: 2026-04-30
- Owner: codex

## Status

Accepted.

## Context

Cognitive OS has many planning, architecture, ADR, product, and report documents. Multiple agents have written docs across sessions, so maintainers need a report-only way to know what documentation is implemented, planned, proposed, stale, or claimed done without proof.

## Decision

Add a Documentation Execution Audit that scans Markdown items and classifies them using repository evidence. The first version is advisory/report-only and must not rewrite checkboxes automatically.

Statuses:

- `done_with_proof`
- `done_weak_proof`
- `claimed_done_no_proof`
- `planned`
- `proposed`
- `stale`
- `contradicted`
- `unknown`

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.

## Consequences

Agents and maintainers can ask what remains without loading all docs into context. Heuristic false positives are expected, so CI should start report-only and move to regression gates after baseline triage.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/contracts/test_local_connected_systems_validation_docs.py tests/contracts/test_runtime_comparison_benchmark_plan.py -q
```
