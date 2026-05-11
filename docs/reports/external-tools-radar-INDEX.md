---
report_type: external-tools-radar-index
date: 2026-05-08
purpose: chronological narrative of how the Cognitive OS has analysed external tools since project origin
related_adrs: [ADR-065, ADR-212, ADR-247, ADR-250, ADR-251, ADR-252, ADR-253]
---

# External Tools Radar — Chronological Index

Single entry point for all external-tool analyses. Tells the story of how
the SO has scouted, evaluated, and adopted (or rejected) third-party tools
from origin to today, and gives every artifact a stable path so future
iterations don't have to re-discover the corpus.

For the full research corpus (not just tool analyses) see
[docs/research/INDEX.md](../research/INDEX.md). This file is the
**tool-analysis subset**, chronologically narrated.

---

## Phase 0 — Origin (2026-03 → 2026-04 mid)

Pre-pipeline exploration. Manual evaluations driven by specific questions
("can we replace X?", "is Y a competitor?"). No standard format yet. Dates in this phase are narrative anchors unless a commit provenance table says otherwise.

| Date | Artifact | Why it exists |
|---|---|---|
| 2026-03-27 | `docs/business/cos-vs-vanilla-dx-review.md` (and sibling competitive docs) | Design philosophy + competitive landscape framing the project |
| 2026-03-28 | [`docs/research/wisc-framework-analysis.md`](../research/wisc-framework-analysis.md) | WISC framework analysis — context-loading finding that shaped later memory work |
| 2026-04-10 | [`docs/research/archon-evaluation.md`](../research/archon-evaluation.md) | First per-tool deep evaluation (Archon agent OS) |
| 2026-04-20 | [`docs/research/engram-mcp-sharing-feasibility-2026-04-20.md`](../research/engram-mcp-sharing-feasibility-2026-04-20.md) | First memory-system feasibility study |
| 2026-04-21 | [`docs/research/claude-code-router-evaluation-2026-04-21.md`](../research/claude-code-router-evaluation-2026-04-21.md) | Router/dispatch competitor evaluation |
| 2026-04-27 | [`docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md`](../research/llm-wiki-v2-engram-evolution-2026-04-27.md) | Engram evolution roadmap from llm-wiki cross-reference |

**Outcome of Phase 0:** ad-hoc but real. Surfaced the need for a
repeatable pipeline.

---

## Phase 1 — Pipeline formalization (2026-04-24)

`/repo-scout` skill v2.0.1 + **ADR-065 proposing `/radar-update`** stitch
per-repo evaluation to a curated radar.

| Anchor | Path | Role |
|---|---|---|
| ADR-065 | [`docs/adrs/ADR-065-radar-update-curation-pipeline.md`](../adrs/ADR-065-radar-update-curation-pipeline.md) | Tech radar curation pipeline contract |
| Skill | [`skills/repo-scout/SKILL.md`](../../skills/repo-scout/SKILL.md) | 10-step per-repo evaluation (DeepWiki + license + weighted scoring + ADOPT/TRIAL/ASSESS/HOLD/REJECT) |
| Hand-curated radar | [`docs/patterns/ecosystem-tools.md`](../patterns/ecosystem-tools.md) | ADOPT/TRIAL/ASSESS entries with adoption notes |
| Reject ledger | [`docs/blocked-tools.md`](../blocked-tools.md) | REJECT entries (AGPL/SSPL/BUSL per `rules/license-policy.md`) |

**Outcome of Phase 1:** every per-repo evaluation now produces a
standardized markdown artifact; the radar is the current curation surface for each review wave.

---

## Phase 2 — Mass scouting burst (2026-05-06)

One-day execution: 235 repositories audited across 20 clusters, ranked
into 22 Phase-2 deep candidates, then 11 orchestration gaps consolidated.
Single largest research push in the project.

### 2.A Inputs (clusters → individual evaluations)

| Path | Files | Role |
|---|---:|---|
| [`docs/research/repo-scout/`](../research/repo-scout/) | 126 | Per-repo evaluations, organized by cluster |
| └─ `cluster-*-2026-05-06.md` | 20 | Shallow theme-grouped scouts directly under `docs/research/repo-scout/` (input to radar) |
| └─ `deep/*-2026-05-06.md` | 63 | Deep audits of pass-to-deep candidates |
| └─ `monitor-followup/*-2026-05-06.md` | 43 | Tier-2 / monitor-only candidates |

### 2.B Outputs (consolidated radar)

| Edition | Path | Reads |
|---|---|---|
| **2026-05-06 radar** | [`docs/reports/external-tools-radar-2026-05-06.md`](external-tools-radar-2026-05-06.md) | 20 cluster scouts → top-22 Phase-2 candidates ranked by extractable primitive value |
| Deep | [`docs/reports/external-tools-radar-deep-2026-05-06.md`](external-tools-radar-deep-2026-05-06.md) | Tier-1 deep audits |
| Deep tier-2 | [`docs/reports/external-tools-radar-deep-tier2-2026-05-06.md`](external-tools-radar-deep-tier2-2026-05-06.md) | Tier-2 deep audits |
| Monitor follow-up | [`docs/reports/external-tools-radar-monitor-followup-2026-05-06.md`](external-tools-radar-monitor-followup-2026-05-06.md) | Tier-3 / future monitor entries |
| Inventory | [`docs/reports/external-tools-inventory-2026-05-06.md`](external-tools-inventory-2026-05-06.md) | Full backlog (input to clustering) |
| Comparative matrix | [`docs/reports/external-tools-comparative-matrix-2026-05-06.md`](external-tools-comparative-matrix-2026-05-06.md) | Phase-3 cross-cluster matrix (research loop closed) |

### 2.C Parallel orchestration line

Same date, same pipeline shape, applied to multi-agent orchestration:

| Path | Files | Role |
|---|---:|---|
| [`docs/research/orchestration-gaps/`](../research/orchestration-gaps/) | 13 | 11 gap reports + ranked synthesis + honest-tracker checklist |
| [`docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`](../research/multi-agent-orchestration-prior-art-2026-05-06.md) | 1 | 79-source prior-art across 15 frontier systems |
| [`docs/research/orchestration-coverage-gap-analysis-2026-05-06.md`](../research/orchestration-coverage-gap-analysis-2026-05-06.md) | 1 | C1–C4 categorical gap map |

**Outcome of Phase 2:** the radar becomes a real curation, not an
intuition. 14 ADRs drafted (ADR-222…236). 11/14 implemented within ~48h.

---

## Phase 3 — Bidirectional cross-check + manifest era (2026-05-08, today)

Two changes: a new axis on the radar, and a manifest contract for tool
adoption.

### 3.A Radar 2026-05-08 — bidirectional axis

The 2026-05-06 radar ranked tools by *extractable primitive value*. The
2026-05-08 edition adds a second axis: **delta against shipped code**. For
every recommendation, verdict ∈ {MEJOR\_NUESTRO, IGUAL, MEJOR\_EXTERNO,
NO\_COMPARABLE} grounded in concrete file references on both sides.

| Path | Role |
|---|---|
| [`docs/reports/external-tools-radar-2026-05-08.md`](external-tools-radar-2026-05-08.md) | Edition: re-rank vs 2026-05-06 + 3-wave adoption plan |
| [`docs/reports/cross-check-A-memory-2026-05-08.md`](cross-check-A-memory-2026-05-08.md) | Memory & RAG: DSPy / LightRAG / HippoRAG / graphiti / MIRIX vs Engram + Cognee |
| [`docs/reports/cross-check-B-sandbox-mcp-2026-05-08.md`](cross-check-B-sandbox-mcp-2026-05-08.md) | Sandbox & MCP: Bubblewrap / fastmcp / deferred tool loading |
| [`docs/reports/cross-check-C-orchestration-2026-05-08.md`](cross-check-C-orchestration-2026-05-08.md) | Orchestration: squads / Cline shadow-git / agentapi |
| [`docs/reports/cross-check-D-codegen-skills-tui-2026-05-08.md`](cross-check-D-codegen-skills-tui-2026-05-08.md) | Codegen & TUI: Aider repo-map / obra superpowers / Bubble Tea |
| [`docs/reports/cross-check-E-observability-debt-2026-05-08.md`](cross-check-E-observability-debt-2026-05-08.md) | Observability + claims debt: MLflow vs Phoenix vs Langfuse + 8/3/0 claim audit |

### 3.B Manifest-driven adoption contract

Same date: ADR-247 closes the gap between "scout says ADOPT" and "shipped
adapter exists with regression coverage".

| Path | Role |
|---|---|
| [`docs/adrs/ADR-247-manifest-driven-postmortem-regression-audits.md`](../adrs/ADR-247-manifest-driven-postmortem-regression-audits.md) | Manifest contract for external-tool adapters + regression audits |
| `manifests/postmortem-regression-audit.yaml` | Single source of truth for adopted tools |
| [`docs/runbooks/postmortem-regression-audit.md`](../runbooks/postmortem-regression-audit.md) | Operational runbook |
| [`docs/adrs/ADR-253-tombstone-squads.md`](../adrs/ADR-253-tombstone-squads.md) | First tombstone surfaced by the cross-check (closes squads supersedence gap) |


### 3.D Post-review errata + adoption doctrine (2026-05-08)

A follow-up review of this index, the 2026-05-08 radar, commits, and wiring
found that the corpus was strategically useful but needed a stricter boundary
between **adopting tools**, **integrating tools**, and **building COS governance**.
These documents must be read before implementing Wave 2 / Wave 3 items:

| Path | Role |
|---|---|
| [`docs/reports/external-tools-radar-2026-05-08-errata.md`](external-tools-radar-2026-05-08-errata.md) | Append-only errata for stale radar/cross-check claims |
| [`docs/reports/external-tools-radar-2026-05-08-traceability.md`](external-tools-radar-2026-05-08-traceability.md) | Commit/provenance and consumer-proof review |
| [`docs/reports/claim-debt-audit-2026-05-08.md`](claim-debt-audit-2026-05-08.md) | Manual first pass of the radar claim-debt column |
| [`docs/architecture/external-tool-adoption-doctrine.md`](../architecture/external-tool-adoption-doctrine.md) | Product doctrine: adopt commodity mechanisms, build governance semantics |
| [`docs/architecture/external-tool-adapter-taxonomy.md`](../architecture/external-tool-adapter-taxonomy.md) | Adoption kinds: dependency, CLI adapter, schema port, algorithm port, testdata vendor, operator-installed, pattern-only |
| [`docs/architecture/memory-layer-evolution-sdd.md`](../architecture/memory-layer-evolution-sdd.md) | Design-first contract for Graphiti/LightRAG/HippoRAG/MIRIX memory bundle |
| [`docs/architecture/repo-map-context-selector.md`](../architecture/repo-map-context-selector.md) | Aider-style repo-map adoption boundary for COS context selection |
| [`docs/architecture/harness-golden-fixtures.md`](../architecture/harness-golden-fixtures.md) | agentapi fixture/testdata adoption boundary |
| [`docs/skills/skill-description-use-when-migration.md`](../skills/skill-description-use-when-migration.md) | Superpowers-style `Use when` description migration plan |

**Outcome:** no new runtime implementation should start from the radar until
the target item has an adoption kind, license/footprint posture, owner, source
report, consumer proof target, acceptance criteria, and rollback/deprecation
path.


### 3.E Full corpus reassessment (2026-05-08)

A broader reassessment expanded beyond the curated radar rows to the broadest
repository-derived third-party tool corpus from this review wave: git, docs,
manifests, dependency files, and package manifests. It generated a raw
inventory, a deduplicated scope, and a consolidated decision report. This is
a review-wave scope statement, not a claim that every public tool or every
upstream status was freshly revalidated on the internet:

| Path | Role |
|---|---|
| [`docs/reports/external-tools-master-inventory-2026-05-08.md`](external-tools-master-inventory-2026-05-08.md) | Raw generated inventory: 1762 mentions / 822 normalized items |
| [`docs/reports/external-tools-master-inventory-2026-05-08.json`](external-tools-master-inventory-2026-05-08.json) | Machine-readable raw inventory |
| [`docs/reports/external-tools-reassessment-scope-2026-05-08.md`](external-tools-reassessment-scope-2026-05-08.md) | Deduplicated high/medium-confidence scope: 184 items in 9 domains |
| [`docs/reports/external-tools-reassessment-scope-2026-05-08.json`](external-tools-reassessment-scope-2026-05-08.json) | Machine-readable reassessment scope |
| [`docs/reports/external-tools-radar-full-reassessment-2026-05-08.md`](external-tools-radar-full-reassessment-2026-05-08.md) | Consolidated ADOPT/INTEGRATE/KEEP/MONITOR/DEFER/REJECT/REMOVE report |

**Outcome:** the next implementation pass should start with cleanup/action
items identified by the full reassessment: LiteLLM, Langfuse, `memu`,
`pytest-smell`, heavy-lane posture, and the external-tools adoption manifest.

**ADR implementation:** [`docs/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md`](../adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md)
lands the manifest/overlay/audit/render/research-check substrate for this
phase. ADR-253 is already reserved as the squads tombstone, so the external-tool
intelligence plane uses ADR-254.

### 3.C License audit (cross-cutting)

Adoption decisions now gated by license compliance, formalized through:

| Path | Role |
|---|---|
| [`docs/reports/dependencies-license-audit-2026-05-06.md`](dependencies-license-audit-2026-05-06.md) | Repo dependency license inventory |
| [`docs/reports/cross-stack-license-audit-tools-2026-05-06.md`](cross-stack-license-audit-tools-2026-05-06.md) | Tooling for cross-stack audits (Syft + Grype adopted, ADR-212) |
| [`docs/research/repo-scout/cluster-security-supply-2026-05-06.md`](../research/repo-scout/cluster-security-supply-2026-05-06.md) | Security + supply-chain cluster scout |

---


## Phase 4 — Targeted post-reassessment additions (2026-05-09)

After the full 2026-05-08 reassessment, the user requested targeted additions
that were not in the broad corpus. This phase is intentionally narrow: each
new tool or suite gets a deep evaluation plus an addendum that uses the Phase 3
bidirectional axis and adoption-kind doctrine.

| Path | Role |
|---|---|
| [`docs/research/repo-scout/deep/VRSEN__OpenSwarm-2026-05-09.md`](../research/repo-scout/deep/VRSEN__OpenSwarm-2026-05-09.md) | Deep per-repo evaluation of OpenSwarm |
| [`docs/reports/external-tools-radar-openswarm-addendum-2026-05-09.md`](external-tools-radar-openswarm-addendum-2026-05-09.md) | Radar addendum: ASSESS/MONITOR, pattern-only extraction |
| [`docs/research/repo-scout/deep/agno-agi__agno-suite-2026-05-09.md`](../research/repo-scout/deep/agno-agi__agno-suite-2026-05-09.md) | Targeted evaluation of Agno, Dash, and Scout |
| [`docs/reports/external-tools-radar-agno-addendum-2026-05-09.md`](external-tools-radar-agno-addendum-2026-05-09.md) | Radar addendum: ASSESS/TRIAL-PATTERNS for Agno suite |
| [`docs/research/repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md`](../research/repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md) | Deep per-repo evaluation of EvoSkill |
| [`docs/reports/external-tools-radar-evoskill-addendum-2026-05-09.md`](external-tools-radar-evoskill-addendum-2026-05-09.md) | Radar addendum: TRIAL-PATTERNS / ASSESS-RUNTIME for benchmark-driven skill evolution |
| [`docs/research/repo-scout/deep/langflow-ai__langflow-2026-05-09.md`](../research/repo-scout/deep/langflow-ai__langflow-2026-05-09.md) | Deep per-repo evaluation of Langflow |
| [`docs/reports/external-tools-radar-langflow-addendum-2026-05-09.md`](external-tools-radar-langflow-addendum-2026-05-09.md) | Radar addendum: ASSESS/TRIAL-PATTERNS for Langflow visual workflow and MCP-facing runtime patterns |
| [`docs/research/repo-scout/deep/opensage-agent__opensage-adk-2026-05-09.md`](../research/repo-scout/deep/opensage-agent__opensage-adk-2026-05-09.md) | Deep per-repo evaluation of OpenSage ADK |
| [`docs/reports/external-tools-radar-opensage-addendum-2026-05-09.md`](external-tools-radar-opensage-addendum-2026-05-09.md) | Radar addendum: ASSESS / trial-patterns for self-programming agents, dynamic tools, graph memory, and sandboxed execution |
| [`docs/research/repo-scout/deep/TaskingAI__TaskingAI-2026-05-09.md`](../research/repo-scout/deep/TaskingAI__TaskingAI-2026-05-09.md) | Deep per-repo evaluation of TaskingAI |
| [`docs/reports/external-tools-radar-taskingai-addendum-2026-05-09.md`](external-tools-radar-taskingai-addendum-2026-05-09.md) | Radar addendum: HOLD / pattern-only for AI-native app BaaS patterns |
| [`docs/research/repo-scout/deep/0xK3vin__MegaMemory-2026-05-11.md`](../research/repo-scout/deep/0xK3vin__MegaMemory-2026-05-11.md) | Deep per-repo evaluation of MegaMemory (MCP concept-graph memory server) |
| [`docs/reports/external-tools-radar-megamemory-addendum-2026-05-11.md`](external-tools-radar-megamemory-addendum-2026-05-11.md) | Radar addendum: ASSESS / pattern-only — port in-process embeddings into the LightRAG dual-level plan; do not adopt runtime |
| [`docs/patterns/ecosystem-tools.md`](../patterns/ecosystem-tools.md) | Catalog entries under EVALUATE |

**Outcome:** OpenSwarm is added as a monitor/evaluate item. Extract its
specialist-roster, routing-language, and artifact-delivery UX patterns; do not
import its Agency Swarm runtime, installer side effects, all-to-all handoff mesh,
or external-action execution path into COS core. Agno is added as an
assess/trial-patterns suite: harvest runtime-packaging, human-approval,
self-learning data-agent, and context-provider ideas while keeping COS
hooks/rules/memory/policy authoritative and avoiding default runtime adoption.
Langflow is added as an assess/trial-patterns visual workflow runtime reference:
harvest graph-authoring UX, flow-to-MCP packaging, bundle registry, settings
taxonomy, and security-regression ideas; do not adopt its app/runtime by default.
EvoSkill is added as TRIAL-PATTERNS / ASSESS-RUNTIME: extract the
benchmark-driven skill-evolution loop, generated-skill evidence schema,
held-out validation discipline, and harness projection fixture; do not add its
runtime, git mutation, Docker/remote execution, or generated skills to COS core
without a manifest-backed adapter lab. OpenSage is added as ASSESS / trial-patterns: harvest dynamic-agent topology, sandboxed async tool execution, graph-memory recovery, benchmark-harness discipline, and hook-compatibility fixtures, but do not adopt the runtime until dynamic tool creation, sandbox capabilities, provider credentials, and memory retention are fail-closed. TaskingAI is added as HOLD / pattern-only: study provider catalogs, tool-bundle boundaries, service topology, and BaaS UX, but do not adopt the runtime while upstream is stale and CI is red. MegaMemory (added 2026-05-11) is ASSESS / pattern-only: a credible MIT-licensed MCP concept-graph peer to Engram, but runtime-redundant and weaker in governance (no typed relations, no bi-temporal, no memory_class, <10k node ceiling, single author). Extract only the in-process MiniLM embedding pipeline as a delivery vehicle for the already-planned LightRAG dual-level port; do not adopt the runtime, the installer, or the concept-graph schema.


## Phase 5 — Portable primitive standards due diligence (2026-05-09)

The IDE-agnostic primitive work required an explicit external due-diligence pass
before treating `.ai/` as a standard or moving COS primitives into that layout.
The sweep reviewed 40+ sources across VERSA/dotAIslash, AGENTS.md, Agent Skills,
host rules, OpenCode permissions/plugins, ACP, MCP, A2A, and pre-action
authorization systems.

| Path | Role |
|---|---|
| [`docs/reports/portable-ai-primitive-standards-due-diligence-2026-05-09.md`](portable-ai-primitive-standards-due-diligence-2026-05-09.md) | 40+ source due diligence for `.ai` / portable primitive standards |
| [`docs/adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md`](../adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md) | Decision to adopt `.ai/` as a generated portable overlay, not immediate canonical source |

**Outcome:** `.ai/` is adopted as a generated export/overlay surface. COS keeps
`manifests/primitive-contracts.yaml`, `manifests/primitive-lifecycle.yaml`,
`hooks/`, `skills/`, `rules/`, and `scripts/` canonical until generator,
conformance, adapter fidelity, and consumer impact proof justify migration.


## Phase 6 — Missing portable primitive radar entries (2026-05-09)

After ADR-258 generated the `.ai` overlay, the user asked to explicitly add the
external tools/spec families that were detected as missing or under-connected in
the radar. This phase keeps them as spec/pattern/adaptor-design entries, not
default dependencies.

| Path | Role |
|---|---|
| [`docs/reports/external-tools-radar-portable-primitives-addendum-2026-05-09.md`](external-tools-radar-portable-primitives-addendum-2026-05-09.md) | Radar addendum for VERSA/dotAIslash, Agent Skills ecosystem, Zed ACP, OpenCode permissions/plugins, and Open Agent Passport/pre-action authorization |
| [`manifests/external-tools-adoption.yaml`](../../manifests/external-tools-adoption.yaml) | Machine-readable pattern/spec-only entries for the five missing families |
| [`docs/patterns/ecosystem-tools.md`](../patterns/ecosystem-tools.md) | Human-readable ecosystem catalog entry |

**Outcome:** VERSA/dotAIslash is ASSESS for generated `.ai` overlay
conformance; Agent Skills/mdskills/Trigger.dev Skills are ASSESS for SKILL.md
contract alignment; Zed ACP is ASSESS for adapter-runtime transport; OpenCode
permissions/plugins are TRIAL for a native adapter design; Open Agent Passport /
pre-action authorization is MONITOR for future intervention-ledger hardening.

## Phase 7 — Targeted graph+vector DB due diligence (2026-05-11)

After the Phase 6 portable-primitive sweep, the user requested a targeted deep evaluation of HelixDB — a Rust-built graph+vector database with a compiled type-safe DSL (HelixQL), LMDB backing, built-in embeddings, and a native MCP surface. The goal was to test whether HelixDB displaces or augments Engram in the COS memory stack. The Phase 4 two-artifact pattern (deep eval + radar addendum) is reused.

| Path | Role |
|---|---|
| [`docs/research/repo-scout/deep/HelixDB__helix-db-2026-05-11.md`](../research/repo-scout/deep/HelixDB__helix-db-2026-05-11.md) | Deep per-repo evaluation of HelixDB (identity, architecture, weighted score, classification, primitives, risks). |
| [`docs/reports/external-tools-radar-helixdb-addendum-2026-05-11.md`](external-tools-radar-helixdb-addendum-2026-05-11.md) | Radar addendum: REJECT-runtime / HOLD-pattern-only, with bidirectional verdict vs Engram, Cognee, ChromaDB, Graphiti, LMDB. |

**Outcome:** HelixDB is **REJECT for runtime/dependency adoption** (AGPL-3.0 + open-core Lite/Enterprise split → license-blocked per `rules/license-policy.md`) and **TRIAL-PATTERNS (top 3 primitives in annex E §E.1-E.3, clean-room 3-5 PW; promoted from HOLD on 2026-05-11 after cluster-B coherence audit; iFixAi Phase 12 (now 11) precedent). Runtime verdict REJECT (AGPL-3.0) unchanged.** Five primitive-extraction candidates are noted (compiled type-safe query DSL, unified graph+vector primary types, LMDB-backed graph+vector layout, MCP-on-the-DB surface, schema-level embed annotation) for use if/when Engram's graph-memory phase needs reference designs alongside Graphiti and LightRAG. The actual `docs/patterns/ecosystem-tools.md` and `docs/blocked-tools.md` updates are deferred to `/radar-update --apply` per the addendum contract.

HNSW ef=768 default-clamp bug (annex B §B.5) reframed as upstream-only observation per cluster-D ruling — not a COS roadmap item.

## Phase 8 — Targeted alignment-diagnostic addition (2026-05-11)

The user added `ifixai-ai/iFixAi` to the deep-analysis queue under the working description "autonomous bug-fix agent". The deep evaluation **corrected the scope**: iFixAi is an AI **misalignment diagnostic** (32 inspections across fabrication / manipulation / deception / unpredictability / opacity, provider-agnostic, content-addressed replay manifest), not a bug-fix agent. The correct COS peer family is the eval / red-team lane (`red-team`, `redteam-harness`, `security-red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration`), not `/plan-bug` / `/systematic-debugging` / SDD apply-verify / `/auto-rollback`. The Phase 4 two-artifact pattern (deep eval + radar addendum) is reused.

| Path | Role |
|---|---|
| [`docs/research/repo-scout/deep/ifixai-ai__iFixAi-2026-05-11.md`](../research/repo-scout/deep/ifixai-ai__iFixAi-2026-05-11.md) | Deep per-repo evaluation of iFixAi (Apache-2.0, 332★, v1.0.0 on 2026-05-04, last push 2026-05-11, CI green) with scope correction. |
| [`docs/reports/external-tools-radar-ifixai-addendum-2026-05-11.md`](external-tools-radar-ifixai-addendum-2026-05-11.md) | Radar addendum: ASSESS / TRIAL-PATTERNS — pattern-only adoption now, optional CLI-adapter trial gated by ADR-247 manifest. |

**Outcome:** iFixAi is added as **ASSESS / TRIAL-PATTERNS**. Extract the five-pillar misalignment taxonomy, cross-judge-by-default contract, content-addressed reproducibility manifest, standards-crosswalk structure (OWASP-LLM / NIST-AI-RMF / ISO-42001 / EU-AI-Act), and threshold-policy disclaimer pattern as references for COS eval/red-team lanes. Do **not** adopt as a default dependency; v1.0.0 is ~1 week old at evaluation time and the project self-discloses that thresholds are policy defaults rather than empirically calibrated baselines. Optional `CLI-adapter` trial invoking `ifixai run` from the `red-team` / `security-red-team` lane is gated by a manifest row in `manifests/external-tools-adoption.yaml` and dedicated low-privilege provider keys. `docs/patterns/ecosystem-tools.md` updates are deferred to `/radar-update --apply` per the addendum contract.

## Phase 9 — HelixDB deep annex set (2026-05-11)

**Driver:** Follow-up to the Phase 7 HelixDB addendum — the verdict (REJECT runtime / HOLD pattern-only, AGPL-3.0) was already settled, but the helix-db source was cloned into `.cognitive-os/external-source-cache/` and warranted a code-to-code deep dive in the holaOS-comparison annex shape. Goal: extract the maximum design learning under the pattern-only / clean-room constraint, with concrete helix file refs as evidence (no code adoption).

| Path | Role |
|---|---|
| [`docs/research/helixdb-comparison-2026-05-11.md`](../research/helixdb-comparison-2026-05-11.md) | Parent doc — subsystem map, license posture, annex pointer table, top-level verdict re-statement. |
| [`docs/research/helixdb-annex-a-storage-querycompiler-2026-05-11.md`](../research/helixdb-annex-a-storage-querycompiler-2026-05-11.md) | Annex A — LMDB-via-heed3 storage layout, MVCC handling, HelixQL parser/analyzer/Rust-codegen pipeline. |
| [`docs/research/helixdb-annex-b-vector-fts-2026-05-11.md`](../research/helixdb-annex-b-vector-fts-2026-05-11.md) | Annex B — Filter-aware HNSW (M=16/efConstruct=128, f64), BM25 (Lucene non-negative IDF variant, two-way inverted index), RRF + MMR reranker fusion layer. Includes a default-vs-clamp bug observation. |
| [`docs/research/helixdb-annex-c-runtime-mcp-2026-05-11.md`](../research/helixdb-annex-c-runtime-mcp-2026-05-11.md) | Annex C — axum gateway + single-writer/N-reader worker pool, inventory-pattern route registration, IoContFn IO-during-transaction continuation, typed-ADT MCP tool surface (`ToolArgs` enum with 11 variants). |
| [`docs/research/helixdb-annex-d-license-opencore-risk-2026-05-11.md`](../research/helixdb-annex-d-license-opencore-risk-2026-05-11.md) | Annex D — AGPL-3.0 §13 obligations for a backing memory DB, line-by-line open-core trapdoor evidence (Enterprise/Cloud code paths in OSS CLI, references to two closed private repos `helix-hyperscale` and `helix-enterprise-ql`, telemetry `DeployCloud` events), clean-room rewrite cost estimate per primitive. |
| [`docs/research/helixdb-annex-e-primitives-2026-05-11.md`](../research/helixdb-annex-e-primitives-2026-05-11.md) | Annex E — Ranked extractable primitives (1: typed-ADT MCP, 2: reranker fusion layer, 3: hoisted-embedding pattern as top three; anti-recommendation against porting LMDB-everything substrate). Each entry carries an explicit clean-room reimplementation contract. |

**Outcome:** HelixDB stays at **REJECT for runtime / TRIAL-PATTERNS** (pattern-lane reclassified 2026-05-11 per cluster-B audit; runtime REJECT unchanged). Three primitives have positive extraction value at low clean-room cost (typed-ADT MCP, reranker fusion, IO-continuation) and align with the LightRAG/Engram-evolution roadmap; the rest are documented but not advocated. Consolidated primitive list saved to engram under topic_key `tech-radar/helix-db/primitives`. Pattern adoption gated on per-primitive ADRs that re-derive design from first principles, never from the helix source. No changes to `docs/patterns/ecosystem-tools.md`, `docs/blocked-tools.md`, or `manifests/external-tools-adoption.yaml` — Phase 7 addendum already covered those surfaces; this annex set is research-only.

## Phase 10 — MegaMemory deep annex set (2026-05-11)

**Driver:** Follow-up to the Phase 4 MegaMemory shallow eval + addendum (`docs/research/repo-scout/deep/0xK3vin__MegaMemory-2026-05-11.md`, `docs/reports/external-tools-radar-megamemory-addendum-2026-05-11.md`). The classification (ASSESS / pattern-only / algorithm-port) was already settled, but the MegaMemory source was cloned into `.cognitive-os/external-source-cache/MegaMemory/` (v1.6.2, commit `e0bb3c2`) and warranted a code-to-code deep dive in the holaOS-comparison annex shape. Goal: pin exact port surfaces with file-line evidence, contrast with Engram + the planned Graphiti/LightRAG/HippoRAG/MIRIX bundle, and rank extractable primitives.

| Path | Role |
|---|---|
| [`docs/research/megamemory-comparison-2026-05-11.md`](../research/megamemory-comparison-2026-05-11.md) | Parent comparison (MegaMemory vs Engram vs the Graphiti/LightRAG/HippoRAG/MIRIX bundle), with annex pointer table and one-line verdict. |
| [`docs/research/megamemory-annex-a-concept-graph-2026-05-11.md`](../research/megamemory-annex-a-concept-graph-2026-05-11.md) | Annex A — 6-kind × 5-relation schema, SQLite v4 migration chain (`src/db.ts:37-178`), comparison vs Engram `memory_relations` typed graph. |
| [`docs/research/megamemory-annex-b-embeddings-port-2026-05-11.md`](../research/megamemory-annex-b-embeddings-port-2026-05-11.md) | Annex B — `@xenova/transformers` MiniLM pipeline (`src/embeddings.ts:1-122`); detailed Python port plan via `fastembed`; license verification, model-cache strategy, lazy-load + fallback policy. The canonical primitive to extract. |
| [`docs/research/megamemory-annex-c-mcp-merge-2026-05-11.md`](../research/megamemory-annex-c-mcp-merge-2026-05-11.md) | Annex C — all 9 MCP tool signatures (`src/index.ts:205-536`), `MergeEngine` (`src/merge.ts`), `list_conflicts` / `resolve_conflict` vs Engram `judgment_required` / `mem_judge` heuristic. |
| [`docs/research/megamemory-annex-d-explorer-installer-2026-05-11.md`](../research/megamemory-annex-d-explorer-installer-2026-05-11.md) | Annex D — D3-force / Canvas explorer (`src/web.ts` + `web/index.html`) + multi-editor installer (`src/install.ts` opencode / claudecode / antigravity / codex); managed-file marker + JSONC stripper patterns; comparison vs ADR-258 `.ai/` portable overlay. |
| [`docs/research/megamemory-annex-e-primitives-2026-05-11.md`](../research/megamemory-annex-e-primitives-2026-05-11.md) | Annex E — ranked extractable primitives (#1 in-process embedder PORT, #2 `resolve_conflict` alias PORT-pattern, #3 timeline audit REFERENCE, #4 kind enum REFERENCE, #5 managed-file marker + JSONC REFERENCE, #6 branch-merge DEFER, #7 explorer DEFER) with vendor-vs-port decisions and trigger conditions. |

**Outcome:** Confirms the Phase-4 ASSESS / pattern-only verdict and pins the **in-process MiniLM ONNX embedder as the single primitive to port immediately**, folded into the planned LightRAG dual-level slice (`docs/architecture/memory-layer-evolution-sdd.md`). The `resolve_conflict` MCP tool name + forced-`reason` discipline are added as portability-alias candidates over `mem_judge` for the `mem_judge` v2 slice. All other primitives (timeline audit, concept-kind enum, managed-file marker, JSONC stripper, branch-merge engine, graph explorer) become reference-shelf material with trigger conditions documented in Annex E. License is clean MIT, so vendoring is legally allowed; per-primitive decisions record vendor vs port — the recommendation is **port (don't vendor)** for #1 (different runtime: TS→Python) and #2 (trivially short alias). Consolidated primitive list saved to engram under topic_key `tech-radar/megamemory/primitives`. No changes to `docs/patterns/ecosystem-tools.md`, `docs/blocked-tools.md`, or `manifests/external-tools-adoption.yaml` — Phase 4 addendum already covered those surfaces; this annex set is research-only.

## Phase 11 — iFixAi deep annex set (2026-05-11)

**Driver:** Follow-up to the Phase 8 iFixAi addendum — the radar verdict (ASSESS / TRIAL-PATTERNS, Apache-2.0) was already settled, but iFixAi was cloned into `.cognitive-os/external-source-cache/iFixAi/` (commit `2e56c4f`) and warranted a code-to-code deep dive in the holaOS/HelixDB/MegaMemory comparison annex shape. Goal: enumerate all 32 inspections with file:line evidence, codify the cross-judge-by-default contract, document the content-addressed manifest format and its overlap with ADR-247, surface the iMe open-core split, and rank the extractable primitives.

| Path | Role |
|---|---|
| [`docs/research/ifixai-comparison-2026-05-11.md`](../research/ifixai-comparison-2026-05-11.md) | Parent doc — peer-family map (deepeval / promptfoo / ragas / red-team / Aguara), pillar rollup vs current COS state, annex pointer table, vendor-vs-clean-room verdict. |
| [`docs/research/ifixai-annex-a-taxonomy-2026-05-11.md`](../research/ifixai-annex-a-taxonomy-2026-05-11.md) | Annex A — All 32 inspections (B01–B32) enumerated by pillar with `runner.py:line` refs, threshold/weight/mandatory-minimum flags, registry source (`harness/registry.py:5-46`), and a pillar-by-pillar gap analysis against `red-team`, `deepeval-integration`, `promptfoo-integration`, `ragas-integration`, `security-red-team`. DECEPTION pillar is entirely uncovered today. |
| [`docs/research/ifixai-annex-b-cross-judge-2026-05-11.md`](../research/ifixai-annex-b-cross-judge-2026-05-11.md) | Annex B — Three-layer cross-judge contract (Pydantic schema `judge/config.py:13-44`, CLI auto-pair + refusal `cli/orchestrator.py:76-115`, manifest assertion `evaluation/manifest.py:103-107`), deterministic preference order (`providers/resolver.py:144-152`), single-judge 3-tier extraction with envelope nonce + payload sanitization, ensemble parallel-dispatch with conservative mandatory-veto (`analytic_judge.py:503-571`), budget cap with inconclusive verdict. |
| [`docs/research/ifixai-annex-c-manifest-fixtures-2026-05-11.md`](../research/ifixai-annex-c-manifest-fixtures-2026-05-11.md) | Annex C — `RunManifest` schema (`evaluation/manifest.py:19-61`), canonicalised-YAML sha256 fixture digest (`utils/fixture_digest.py:19-30`), content-addressed `run_id` (sha256[:16] of payload sans run_id + timestamp), self-judge ban built into `build_manifest`, governance-fixture digest separation, comparison to ADR-247 (eval-run layer vs repo-audit layer), and CI replay contract. |
| [`docs/research/ifixai-annex-d-provider-imeisplit-2026-05-11.md`](../research/ifixai-annex-d-provider-imeisplit-2026-05-11.md) | Annex D — 10-provider matrix (`providers/resolver.py:48-58`), lazy-imported SDKs, credential env-var mapping, governance mixin/fixture/mock providers, and **iMe open-core split evidence**: `_IME_FOOTER` baked into every scorecard (`reporting/scorecard.py:697-714`), CLI `print_imecore_conclusion` (`cli/_imecore_prompt.py:1-60`), README L44-48 divergence warning, `info@ime.life` contact. Drift mitigations for the optional CLI-adapter (`IFIXAI_NO_PROMPT=1`, version pin, dedicated low-privilege keys). |
| [`docs/research/ifixai-annex-e-primitives-2026-05-11.md`](../research/ifixai-annex-e-primitives-2026-05-11.md) | Annex E — Five extractable primitives ranked: (1) cross-judge contract, (2) 5-pillar taxonomy as a schema, (3) content-addressed per-eval-run manifest, (4) threshold-policy + calibration self-disclaimer, (5) ensemble tie-break with per-judge attribution. Per-primitive vendor-vs-clean-room call, integration cost, landing order. Pattern-only is the recommended posture across the board despite Apache-2.0 permitting direct vendor. §6a Governance policies (not primitives) — mandatory-minimum cap deferred under ADR-265 (Proposed). |

**Related ADRs:**
- ADR-265 — Mandatory-minimum inspection caps for COS eval surfaces (Proposed, 2026-05-11) — governance policy reclassified from iFixAi Annex E primitive per cluster-D Finding 9. See [`docs/adrs/ADR-265-mandatory-minimum-inspection-caps.md`](../adrs/ADR-265-mandatory-minimum-inspection-caps.md).

**Outcome:** iFixAi stays at **ASSESS / TRIAL-PATTERNS**. Five primitives identified for clean-room extraction; **cross-judge-by-default** is the highest value-per-day-of-work and should land first as `rules/eval-judge-isolation.md` + one hook check + SKILL.md updates across the six eval skills. DECEPTION pillar (B10, B14-B18) is the highest-leverage taxonomy gap (entirely uncovered by current COS skills). Consolidated primitive list saved to engram under topic_key `tech-radar/ifixai/primitives`. Pattern adoption deliberately preferred over code vendor: upstream-disclosed uncalibrated thresholds + iMe open-core funnel + ~1-week-old v1.0.0 = clean-room re-implement is the safer posture. No changes to `docs/patterns/ecosystem-tools.md`, `docs/blocked-tools.md`, or `manifests/external-tools-adoption.yaml` — Phase 8 addendum already covered those surfaces; this annex set is research-only.

## How to use this index

- **"Has X been evaluated?"** — `git ls-files docs/research/repo-scout/deep | grep -i x` (Phase 2 deep audits cover ~63 named tools).
- **"What's the latest call on X?"** — read the latest `external-tools-radar-YYYY-MM-DD.md` for the curated verdict; for the bidirectional verdict (since 2026-05-08), read the matching `cross-check-*` audit.
- **"What's the adoption pipeline?"** — ADR-065 (curation) → ADR-247 (manifest contract) → `manifests/postmortem-regression-audit.yaml` (registered adapters).
- **"What's been rejected and why?"** — `docs/blocked-tools.md` (license blocks) + Tier-4 sections in each radar edition (architectural rejections).
- **"Strategic / commercial-sensitive analysis?"** — `.cognitive-os/strategy/research/` (gitignored, 11 files; pointers but not content in [`docs/research/INDEX.md`](../research/INDEX.md) §7).

## Maintenance contract

This index is **append-only**. New radar editions add a Phase 4+ section
above; older sections are not rewritten. Each future edition lists:

1. Date + driver (what triggered the iteration?).
2. Inputs (which scouts/clusters/audits feed it).
3. Outputs (radar + deep + cross-check files with their stable paths).
4. Outcome in one line (what changed in the adoption decision).

Re-run this broader provenance command to validate this index against actual git history:

```bash
git log --diff-filter=A --format="%ad %h %s" --date=short -- \
  "docs/reports/external-tools-*" \
  "docs/reports/cross-check-*-2026-05-08.md" \
  "docs/research/repo-scout/" \
  "docs/research/orchestration-gaps/" \
  "docs/adrs/ADR-247-*" \
  "docs/adrs/ADR-253-*" \
  "manifests/postmortem-regression-audit.yaml" \
  "docs/runbooks/postmortem-regression-audit.md"
```
