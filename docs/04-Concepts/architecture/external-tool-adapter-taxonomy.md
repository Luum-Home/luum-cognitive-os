---
title: External Tool Adapter Taxonomy
date: 2026-05-08
status: proposed-contract
source_index: docs/06-Daily/reports/external-tools-radar-INDEX.md
related_adrs: [ADR-065, ADR-212, ADR-247, ADR-250, ADR-251, ADR-252]
---

# External Tool Adapter Taxonomy

## Problem

The radar uses phrases like "adopt", "trial", "pattern port", "already
shipped", and "hardening pending". Those are useful in prose, but too vague
for implementation. Without a taxonomy, the project can confuse:

- importing a dependency,
- copying a pattern,
- porting an algorithm,
- vendoring test fixtures,
- wrapping a CLI,
- exposing an optional operator-installed service,
- or merely documenting a rejected idea.

This confusion is the path back to reinvention and claim drift.

## Canonical adoption kinds

| Kind | Definition | Example from radar | Implementation expectation |
|---|---|---|---|
| `dependency` | Third-party package is installed and used directly by COS runtime or package. | FastMCP for MCP server; Bubble Tea for Go TUI. | License pin, version range, dependency audit, tests proving import/use. |
| `cli-adapter` | COS shells out to an external CLI; COS owns args/policy/results. | Syft/Grype, Trivy, git-filter-repo, Bubblewrap. | Command discovery, dry-run, failure policy, no unsafe default flags, tests with fixture/fake executable where possible. |
| `schema-port` | COS copies a schema idea, not code. | Graphiti bi-temporal validity fields. | ADR/SDD, migration plan, compatibility/backfill tests, source attribution. |
| `algorithm-port` | COS reimplements algorithmic idea in local code. | LightRAG dual-level retrieval; HippoRAG PPR; Aider repo-map ranking. | Clean-room notes, benchmark, unit tests, no long verbatim code copying. |
| `testdata-vendor` | COS vendors external fixtures/corpus, not runtime. | agentapi harness message fixtures. | License/NOTICE, fixture provenance, parser contract tests. |
| `operator-installed` | Tool may be used if operator installs/runs it; COS does not bundle it. | Phoenix server under ELv2 edge boundary. | Clear docs, no default bundle, license gate, connection-health checks. |
| `pattern-only` | Tool informs design, but no code/data dependency exists. | Temporal/Inngest patterns, OPA policy ideas, NATS future bus. | Radar note only; no implementation claim. |
| `adapter-candidate` | Manifested candidate but not wired. | LangGraph/OpenAI Agents SDK in orchestration boundary. | Must be labeled candidate/lab; cannot be advertised active. |
| `rejected` | Blocked by license/footprint/product boundary. | AGPL/SSPL/BSL/Commons Clause defaults. | Blocked-tools entry and rationale. |

## Required fields before implementation

Every radar item that graduates beyond prose must have:

```yaml
tool: graphiti
adoption_kind: schema-port
source_report: docs/06-Daily/reports/external-tools-radar-2026-05-08.md
source_detail: docs/06-Daily/reports/cross-check-A-memory-2026-05-08.md
license_spdx: Apache-2.0
owner: memory-layer-evolution
status: proposed
implementation_paths: []
test_paths: []
claim_status: not_public
rollback_plan: additive migration with fallback query mode
```

## Status vocabulary

| Status | Meaning |
|---|---|
| `researched` | Radar/deep audit exists, no adoption contract. |
| `proposed` | Adoption contract exists, no implementation. |
| `partial` | Some code/docs landed, but no full runtime or test closure. |
| `active` | Runtime/CLI/docs/tests prove use in supported lane. |
| `opt-in` | Working implementation but not default. |
| `blueprint` | Design exists; no runtime consumer. |
| `deprecated` | Kept for compatibility only. |
| `rejected` | Will not pursue under current constraints. |

## Consumer proof classes

An adopted external tool is not "done" until at least one consumer proof exists:

- `runtime`: production/default code path calls it.
- `cli`: a supported `scripts/cos ...` command calls it.
- `hook`: a registered hook calls it in a profile.
- `test`: test-only fixture or corpus consumer.
- `docs`: documentation only; never enough for active/runtime claims.
- `manual`: runbook/manual-only; must not be advertised as automatic.

## Known classification from the 2026-05-08 radar

| Tool/pattern | Current kind | Current status | Notes |
|---|---|---:|---|
| FastMCP | dependency | active | Real imports and MCP server surface. |
| Bubble Tea | dependency | active/proof | TUI proof exists; do not reopen framework choice. |
| Bubblewrap | cli-adapter | opt-in/partial | Native sandbox adapter exists; hardening remains. |
| Phoenix server | operator-installed | opt-in | Do not bundle server without license review. |
| MLflow | dependency/integration | opt-in | Outcome/experiment backend. |
| Graphiti | schema-port or optional backend | proposed | Schema first; backend only after benchmark. |
| LightRAG | algorithm-port/provider | proposed | Do not make core memory default yet. |
| HippoRAG | algorithm-port/benchmark | deferred | PPR as benchmark or optional mode. |
| DSPy | dependency | proposed | Pilot structured-I/O skill, not router. |
| Aider repo-map | algorithm-port | proposed | COS-specific projection required. |
| agentapi | testdata-vendor or adapter | proposed | Testdata first; runtime adapter later if justified. |
| Superpowers | pattern-only/selective import | proposed | Use conventions, not wholesale governance. |
| NATS/Temporal/OPA/Firecracker-primary | pattern-only | deferred | Too heavy for default local-first core. |

## Enforcement path

This document is intentionally documentary first. The next implementation step
should be a machine-readable manifest such as `manifests/external-tools-adoption.yaml`
plus an audit that blocks:

- active claims without consumer proof,
- dependencies without license/footprint fields,
- schema/algorithm ports without source attribution,
- operator-installed services listed as bundled dependencies,
- blueprint tools advertised as runtime features.
