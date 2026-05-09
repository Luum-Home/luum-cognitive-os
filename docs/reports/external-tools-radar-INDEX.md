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
| [`docs/patterns/ecosystem-tools.md`](../patterns/ecosystem-tools.md) | Catalog entries under EVALUATE |

**Outcome:** OpenSwarm is added as a monitor/evaluate item. Extract its
specialist-roster, routing-language, and artifact-delivery UX patterns; do not
import its Agency Swarm runtime, installer side effects, all-to-all handoff mesh,
or external-action execution path into COS core. Agno is added as an
assess/trial-patterns suite: harvest runtime-packaging, human-approval,
self-learning data-agent, and context-provider ideas while keeping COS
hooks/rules/memory/policy authoritative and avoiding default runtime adoption.

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
