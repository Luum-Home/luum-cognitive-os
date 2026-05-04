# Agent Capability Coverage Pipeline

> Runtime architecture for turning existing COS primitive audits into one ACC report.

## Purpose

The ACC pipeline automates the manual primitive-readiness loop. It does not discover every possible endpoint, event, job, or integration in arbitrary applications yet. Its first scope is the Cognitive OS itself: scripts, hooks, skills, rules, docs claims, primitive coverage, and downstream consumer accessibility.

## Entrypoint

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
```

Outputs:

- `docs/acc/latest.json` — machine-readable ACC report and drift baseline.
- `docs/acc/latest.md` — human review summary.
- `.cognitive-os/metrics/acc-pipeline-history.jsonl` — append-only local history.

## Adapter flow

```text
existing tools / ledgers
  -> adapter status records
  -> capability rows
  -> mapping status classifier
  -> ACC score + findings
  -> docs/acc/latest.json + latest.md
  -> local JSONL history
  -> Engram handoff when mem tools are surfaced to the agent
```

## Current adapters

| Adapter | Source | Role |
|---|---|---|
| `cos_coverage` | `scripts/cos_coverage.py --json --refresh` | Existing ACC counts and trend. |
| `script_readiness` | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | Script primitive representation and consumer accessibility. |
| `family_readiness:{hooks,skills,rules}` | `docs/reports/primitive-readiness-ledger-*-latest.json` | Hook/skill/rule representation and consumer accessibility. |
| `docs_execution` | `scripts/docs_execution_audit.py` output when available | Stale/docs-reality signal. |
| `primitive_coverage` | `scripts/primitive_coverage.py` output when available | Coverage/actionable-gap signal. |
| `primitive_gap_snapshot` | `scripts/primitive_gap_snapshot.py` output when available | Family risk signal. |

## Scope boundary

This first implementation answers: “how well are COS agentic primitives represented and projected?” It does not yet provide application-specific static adapters for TypeScript routes, Go services, Python APIs, Terraform resources, MCP tools, or workflow engines. Those adapters should emit the same capability row shape and feed the same classifier later.

## Gate policy

Gate severity follows `cognitive-os.yaml → project.phase`:

| Phase | Default behavior |
|---|---|
| `reconstruction` | Warn on partial/unverified debt; block only stale/overexposed/critical missing when explicit fail flags request it. |
| `stabilization` | Warn on partial; block stale/overexposed and critical missing. |
| `production` | Block stale, overexposed, critical missing, or `acc_effective` below threshold. |
| `maintenance` | Same as production, with tighter tolerance for new missing mappings. |

## Engram boundary

A Python script cannot call in-process MCP tools unless they are exposed to that process. Therefore `acc_pipeline.py` records:

- local append-only history always;
- `persistence.engram.status = unavailable` when no Engram bridge is configured;
- enough report content for the agent to call `mem_save`/`mem_session_summary` when those tools are surfaced.

The agent must not claim Engram persistence from the pipeline unless a real Engram write occurred.
