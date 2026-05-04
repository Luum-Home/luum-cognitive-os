# ADR-147: Agent Capability Coverage Pipeline

## Status

Accepted — 2026-05-04

## Context

`docs/agent-capability-coverage.md` defines Agent Capability Coverage (ACC): the degree to which real system capabilities are represented as agentic primitives that agents can discover, reason about, and invoke. The repository already has the pieces needed to approximate ACC for Cognitive OS itself:

- `scripts/cos_coverage.py` summarizes REAL/DORMANT/ASPIRATIONAL and claim-proof coverage.
- `scripts/primitive_readiness_ledger.py` classifies scripts and emits lifecycle/consumer-accessibility metadata.
- `scripts/primitive_family_readiness_ledger.py` classifies hooks, skills, and rules.
- `scripts/docs_execution_audit.py`, `scripts/primitive_gap_snapshot.py`, and `scripts/primitive_coverage.py` audit documentation and primitive evidence.
- `docs/architecture/consumer-project-primitive-accessibility.md` separates SO-local documentation from downstream project projection.

Before this ADR, agents had to run these surfaces manually and interpret them by conversation context. That was error-prone: the system could have script ledgers, family ledgers, docs audits, and coverage metrics without a single ACC report that says which capabilities are aligned, partial, missing, stale, overexposed, or unverified.

## Decision

Create `scripts/acc_pipeline.py` as the canonical ACC orchestrator for the SO repository. The pipeline is an adapter-composition layer, not a replacement for existing tools.

Canonical command:

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
```

Canonical generated artifacts:

- `docs/acc/latest.json`
- `docs/acc/latest.md`
- `.cognitive-os/metrics/acc-pipeline-history.jsonl`

The pipeline MUST:

1. Discover represented agentic primitives by consuming readiness ledgers for scripts, hooks, skills, and rules.
2. Discover real capability signals from existing ACC/coverage/docs/gap tools when available.
3. Cross-map rows into ACC capabilities with `mapping_status` values:
   - `aligned`
   - `missing`
   - `partial`
   - `stale`
   - `overexposed`
   - `unverified`
4. Preserve `consumer_accessibility` so SO-local docs are not treated as downstream project availability.
5. Emit ACC metrics and findings in machine-readable JSON and human Markdown.
6. Gate by phase: reconstruction warns on non-critical partial/unverified debt; production blocks stale, overexposed, critical missing, or score below threshold.
7. Append local history every run and expose Engram persistence status without pretending the script can call MCP tools that are not available in its process.

## Mapping Rules

For the first implementation, readiness ledgers are authoritative for agentic primitive representation:

| Input signal | ACC interpretation |
|---|---|
| `consumer_accessibility` is `projected-consumer-surface` | `aligned` |
| `consumer_accessibility` is `install-profile-managed` | `partial` until projection proof is linked |
| `consumer_accessibility` is `lifecycle-declared-consumer-candidate` | `partial` |
| `consumer_accessibility` is `lifecycle-declared-maintainer` | `aligned` for SO-maintainer scope, not consumer scope |
| `consumer_accessibility` is `repo-skill-not-projectable`, `skill-referenced-not-projectable`, or `so-local-only` | `unverified` unless intentionally maintainer/local |
| Script role is `agentic-primitive` without lifecycle metadata | `missing` |
| Docs execution audit hard gaps | `stale` findings |
| Primitive coverage actionable gaps | `missing` findings |
| Future explicit overexposure audit rows | `overexposed` findings |

This is conservative. It should not claim broad consumer availability unless projection evidence exists.

## Consequences

- Future agents get one ACC entrypoint instead of re-running manual command bundles.
- Existing tools remain useful and testable as adapters.
- Generated `docs/acc/latest.json` becomes the offline drift baseline required by `docs/agent-capability-coverage.md`.
- Engram remains the preferred canonical memory store when surfaced, but local JSONL history is the deterministic fallback.
- The first pipeline is SO-oriented. Project-specific endpoint/event/job adapters remain future work.

## Alternatives rejected

- **Keep ACC as a manual checklist in `docs/agent-capability-coverage.md`**: rejected because manual execution was already drifting from readiness ledgers and docs execution reports.
- **Fold ACC into `primitive_readiness_ledger.py`**: rejected because readiness is per primitive family, while ACC is a cross-adapter capability view.
- **Claim consumer-project coverage from SO-local documentation alone**: rejected because downstream IDE/project availability requires projection evidence, not just repository-local docs.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `python3 scripts/acc_pipeline.py --project-dir . --refresh` writes `docs/acc/latest.json` and `docs/acc/latest.md`.
2. The JSON report includes ACC scores, thresholds, weights, capabilities, findings, adapter statuses, and persistence status.
3. Readiness ledgers are consumed as adapters for scripts, hooks, skills, and rules.
4. The report distinguishes SO-local from consumer-project accessibility.
5. Unit and contract tests cover mapping statuses and repository report generation.
6. The manual test documents the refresh and inspection workflow.
```

## Verification

```bash
python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
python3 -m py_compile scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --refresh
```

## Implementation Evidence

- Implemented in `scripts/acc_pipeline.py`: ACC adapter orchestration, capability mapping, threshold evaluation, local history persistence, and Markdown/JSON report generation.
- Implemented in `tests/unit/test_acc_pipeline.py`: mapping and report-shape unit coverage.
- Implemented in `tests/contracts/test_acc_pipeline_contract.py`: repository-level report generation contract.
- Implemented in `docs/architecture/agent-capability-coverage-pipeline.md`: architecture and adapter boundaries.
- Implemented in `docs/manual-tests/agent-capability-coverage-pipeline.md`: operator refresh and inspection workflow.

## 2026-05-04 Consumer Projection Adapter

The ACC pipeline now runs a temp-project projection adapter for Claude Code and OpenAI Codex default installs. The adapter invokes `scripts/cos_init.py --default --harness claude` and `--harness codex`, inventories `.cognitive-os/hooks/cos/`, `.cognitive-os/skills/cos/`, and `.cognitive-os/rules/cos/`, and marks matching hook/skill/rule capability rows as `aligned` with `consumer_accessibility: projected-consumer-surface`.

This adapter is deliberately evidence-first: it signs only the primitives that actually appear in generated consumer projects. It does not imply Cursor, Windsurf, VS Code Copilot, Google Antigravity, OpenCode, full-profile projection, or script CLI availability.
