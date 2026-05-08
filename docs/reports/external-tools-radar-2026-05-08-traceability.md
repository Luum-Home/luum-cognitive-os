---
report_type: external-tools-radar-traceability
date: 2026-05-08
source_index: docs/reports/external-tools-radar-INDEX.md
status: documentation-before-implementation
---

# External Tools Radar 2026-05-08 — Traceability Review

## Purpose

This review connects the radar narrative to git/ADR/proof reality before new
external-tool implementation starts. It exists because the radar is currently a
strong research corpus but not yet a fully auditable provenance ledger.

## Provenance gaps found

| Gap | Current state | Risk | Documentation fix |
|---|---|---|---|
| Missing commit provenance | Most radar/cross-check files do not record introduced/verified commits. | Readers cannot tell whether a claim reflects current code or a stale snapshot. | Add `introduced_by_commit`, `last_verified_commit`, and `implementation_commits` in future editions. |
| Snapshot vs tracker drift | Radar rows H1-H5 can become stale after tracker commits. | Agents respawn closed work. | Keep radar immutable, but add errata/tracker pointers. |
| Adoption kinds mixed | Dependency, pattern-port, schema-port, and testdata-vendor are described in prose only. | Teams may import heavy frameworks when only an algorithm was intended. | Use `docs/architecture/external-tool-adapter-taxonomy.md`. |
| ADR-247 scope unclear | Manifest currently has narrow external tools, while radar expects broad adoption governance. | "Adopted" tools escape the adapter contract. | Decide whether a new global adoption manifest extends ADR-247 or remains separate. |
| Consumer proof not uniform | Some tools are active, some opt-in, some blueprint. | Public docs can overclaim. | Require consumer proof class: runtime, cli, hook, test, docs, manual. |

## Phase 3 trace table

| Radar/cross-check item | Decision | Evidence today | Remaining gap |
|---|---|---|---|
| Squads / agent-squad | Rejected/tombstoned | ADR-253 exists; ADR-251 is redesign path. | Some historical cross-check text still says tombstone missing. |
| FastMCP | Adopted dependency | MCP server imports FastMCP and exposes tools. | Correct dependency path claim; consider resources/prompts only if valuable. |
| Bubblewrap / sandbox-exec | Integrated backend | Sandbox adapter and CLI exist. | Seccomp/capability profile and host read-only exposure hardening. |
| Deferred tool loading / ToolSearch | Partial governance/index | Manifest/planner/index exist. | Provider-native runtime/list-changed not generally active. |
| Phoenix + MLflow | Integrated optional observability | ADR-058 and trace/outcome split documented. | Langfuse remnants and Phoenix packaging/license boundary need final classification. |
| Bubble Tea | Adopted framework | ADR-192 + Go proof. | No need to reopen unless TUI product scope changes. |
| Graphiti | Proposed schema/backend | Radar recommends temporal schema. | Needs memory-layer SDD, benchmark, migration plan. |
| LightRAG | Proposed algorithm/provider | Radar recommends dual-level retrieval idea. | Needs local benchmark and clean algorithm-port design. |
| HippoRAG | Deferred/runtime benchmark | PPR idea valuable. | Needs benchmark before runtime adoption. |
| DSPy | Proposed selective dependency | Fits structured-I/O optimization. | Pilot target unresolved; do not touch skill router. |
| Aider repo-map | Proposed algorithm-port | Repo-map pattern is relevant. | Needs COS-specific context selector design. |
| agentapi | Proposed testdata/adapter | Multi-harness API useful. | Start with fixtures/testdata before runtime adapter. |
| Superpowers | Proposed pattern/selective import | Skills convention useful. | Need skill-description migration inventory and exceptions. |

## Commit-provenance fields for future radar editions

Future radar artifacts should include:

```yaml
introduced_by_commit: <sha>
last_verified_commit: <sha>
source_commits:
  - <sha> # scout/deep audit creation
implementation_commits:
  - <sha> # if already shipped
related_adrs:
  - ADR-065
  - ADR-212
  - ADR-247
verification_commands:
  - git log --diff-filter=A -- ...
  - scripts/cos-control-plane-audit --lane hook-fast --json
```

## Implementation hold rule

Do not implement new Wave 2/Wave 3 items until each item has:

1. adoption kind,
2. license/footprint/default-install posture,
3. owner,
4. source report,
5. consumer proof target,
6. benchmark/acceptance criteria,
7. rollback/deprecation path.

This does not block documentation, errata, or manifests that make those fields
explicit.
