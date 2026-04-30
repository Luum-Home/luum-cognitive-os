# Primitive Gap Matrix — 2026-04

> Working report for the Cognitive OS primitive-by-primitive reality audit.

## Evidence Standard

A primitive is not considered real just because a file exists or a document describes it.

Evidence priority:

1. Runtime invocation path: settings, hook registration, command, router, or workflow.
2. Behavioral test that executes the primitive and checks side effects.
3. Runtime metric or artifact emitted by real usage.
4. Consumer that reads or acts on the primitive output.
5. Documentation, ADR, or roadmap mention.
6. File existence only.

## Classification

| Label | Meaning |
|---|---|
| `proven` | Wired, behaviorally tested or observed, emits/affects runtime state, and has a consumer or user-visible outcome. |
| `partial` | Implemented and partly wired, but missing tests, consumer, metrics, or clear user-visible closure. |
| `aspirational` | Present mainly as docs, ADRs, dead files, unregistered hooks, or uninvoked scripts. |
| `harmful-overhead` | Real behavior, but cost/noise/latency/confusion currently exceeds observed value. |

## Severity

| Severity | Definition | Default Action |
|---|---|---|
| `blocker` | Misleading product claim, unsafe behavior, or daily-workflow regression. | Fix or disable before more feature work. |
| `high` | Large DX/runtime cost, low proof, or core primitive gap. | Prioritize in reduction sprint. |
| `medium` | Real gap but bounded or optional. | Harden, demote, or document. |
| `low` | Cosmetic, stale, or low-risk cleanup. | Batch with nearby work. |

## Baseline Snapshot

Measured on 2026-04-30 from the self-hosting repo working tree.

| Primitive Family | Count / Signal | Initial Classification | Severity | Notes |
|---|---:|---|---|---|
| Hooks | 165 files; 80 registered; 76 registered + test-mentioned | partial | high | Hook wiring and latency directly affect daily DX. Needs row-level audit first. |
| Rules | 112 files | partial | high | Need verify actual `<!-- TIER: N -->` loader metadata and default/contextual load paths. |
| Skills | 143 skills; dogfood coverage 35/143 | partial | high | Catalog size outpaces behavioral proof and discoverability. |
| Agents/Subagents | 1 file in `agents/` + `.claude/agents/` | partial | medium | COS behavior versus harness-native delegation needs separation. |
| Memory | 9 memory-named files in lib/hooks/skills | partial | high | High value if closed-loop; risk if save/read paths are manual or disconnected. |
| MCP/Tools | 174 files mention MCP/mcp | partial | high | Likely mixed real integrations, optional services, docs-only references, and setup risk. |
| Config/Projection | 2 known projection/config script signals plus `cognitive-os.yaml` | partial | high | Portability claims depend on this being real and tested across drivers. |
| Metrics/Observability | 94 JSONL streams; 72 non-empty; 22 empty | partial | medium | Need separate decision-grade metrics from dead/noisy streams. |
| Tests/Quality Gates | 538 `test_*.py` files | partial | high | Volume is high; behavior quality must be audited to avoid test theater. |
| Docs/ADRs | 371 docs; 58 ADRs | partial | high | Product claims need proof mapping and stale claim cleanup. |

## Hook Findings

_Status: not yet row-audited._

Initial known risks:

- 89 hook files are not both registered and test-mentioned.
- Some hooks are test-mentioned but not registered, which can create false confidence.
- Hook timing evidence exists and shows p95 cost above 1.6 seconds with max above 13 seconds.
- The next audit pass must map hook → lifecycle → metric stream → test type → consumer → action.

## Skill Findings

_Status: not yet row-audited._

Initial known risks:

- Dogfood reports only 35/143 covered by its skill coverage heuristic.
- Broad mention heuristic finds 91/143 mentioned in tests/settings, meaning many mentions likely are not behavioral proof.
- The next audit pass must cluster skills by purpose and identify duplicates, manual-only skills, and hidden-maintainer-knowledge skills.

## Rule Findings

_Status: not yet row-audited._

Initial known risks:

- The loader contract uses `<!-- TIER: N -->`, not YAML `tier:` metadata.
- Tier/load reality must be verified from actual parser and compact index behavior.
- The next audit pass must distinguish governance rules that are enforced from advisory prose.

## Open Work Queue

1. Run hook row-level audit and fill hook table.
2. Run skill row-level audit and cluster duplicate/low-proof skills.
3. Run rule tier/load audit using `lib/ref_key_loader.py` semantics.
4. Run metrics ownership audit for all JSONL streams.
5. Run test-quality audit and map theater tests to primitive families.

## Periodic Automation

A weekly scheduled workflow now runs the family-level primitive gap snapshot:

- workflow: `.github/workflows/primitive-gap-audit.yml`
- script: `scripts/primitive_gap_snapshot.py`
- JSON artifact: `primitive-gap-snapshot.json`
- latest Markdown report: `docs/reports/primitive-gap-latest.md`
- trend metric: `docs/reports/primitive-gap-history.jsonl` in CI, or `.cognitive-os/metrics/primitive-gap-snapshot.jsonl` for local runs

The workflow intentionally does not fail on high risk yet. The current baseline is high-risk, so failing the scheduled job would create noise instead of useful escalation. Once the family-level baseline is cleaned up, enable `--fail-high-risk` or a narrower regression threshold for blocker/high deltas.
