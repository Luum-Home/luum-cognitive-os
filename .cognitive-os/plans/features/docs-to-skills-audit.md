<!--
RECONCILIATION STATUS: LIVE
Related ADRs: ws5 partial shipment (commit a8c6c58 — 8 pointer trims); no ADR adopts the remaining work
Reconciled: 2026-04-21
Remaining scope: 9 SKILL-CANDIDATE conversions from the original audit are still open (noted as parked in status-report-april-11). The classification methodology itself is reference; the residual backlog of doc→skill conversions is the live scope.
-->

# Docs-to-Skills Audit

> **Date**: 2026-04-10
> **Scope**: All 115 markdown files in `docs/`
> **Method**: Read first 25–40 lines of each file; classify as PASSIVE (reference/ADR/why) or ACTIVE (step-by-step procedure/how)
> **Principle**: Docs are PASSIVE — agents read them. Skills are ACTIVE — agents execute them.

---

## Classification Legend

| Category | Definition |
|---|---|
| **REFERENCE** | Pure reference material — architecture decisions, catalogs, conceptual explanations, historical data. Keep as docs. |
| **SKILL-EXISTS** | A skill already exists that covers the procedure this doc describes. Doc can be kept as narrative context or trimmed. |
| **SKILL-CANDIDATE** | Step-by-step procedure that should be extracted as one atomic skill. |
| **SPLIT-CANDIDATE** | Doc contains both reference content AND procedure(s). Split: keep the ADR/reference, extract procedure(s) as skill(s). |
| **OBSOLETE** | Historical artifact, point-in-time data, or superseded content. Archive or delete. |

---

## Full Classification Table

| # | Doc Path | Category | Corresponding Skill | Proposed Skill(s) | Rationale |
|---|---|---|---|---|---|
| 1 | `docs/INDEX.md` | REFERENCE | — | — | Pure navigation index; agents use it to discover docs, not to execute steps |
| 2 | `docs/README.md` | REFERENCE | — | — | Architecture vision and 3-layer diagram; ADR-level context |
| 3 | `docs/adw-patterns.md` | REFERENCE | — | — | ADW (AI Developer Workflows) conceptual patterns catalog; no procedure |
| 4 | `docs/agent-efficiency-strategy.md` | REFERENCE | — | — | 3-level efficiency strategy (lean/standard/full) description; no procedure |
| 5 | `docs/agent-quality.md` | REFERENCE | — | — | Quality system architecture (4 interlocking fixes); references existing hooks/skills |
| 6 | `docs/agent-teams-testing.md` | SKILL-CANDIDATE | — | `/test-agent-teams` | Contains explicit step-by-step procedure for testing Agent Teams hooks (run hook, verify output, repeat per test case) |
| 7 | `docs/agent-teams.md` | REFERENCE | — | — | Architecture/design reference for Agent Teams feature; no executable steps |
| 8 | `docs/anti-hallucination.md` | REFERENCE | — | — | 10-layer defense architecture reference; describes the system, not how to use it |
| 9 | `docs/architecture-principles.md` | REFERENCE | — | — | 5-layer architecture ADR; foundational design decisions |
| 10 | `docs/architecture.md` | REFERENCE | — | — | System diagram and component overview; pure reference |
| 11 | `docs/architecture/cos-vs-project-overlap-analysis.md` | REFERENCE | — | — | Analysis of where COS and project rules overlap; architectural guidance |
| 12 | `docs/architecture/cross-runtime-portability.md` | REFERENCE | — | — | 80/20 portability strategy across IDEs; architecture reference |
| 13 | `docs/architecture/cross-tool-landscape.md` | REFERENCE | — | — | "Can I Use" matrix for 30+ AI tools; decision support reference |
| 14 | `docs/architecture/project-consumption-patterns.md` | REFERENCE | — | — | Three project consumption models; architecture reference |
| 15 | `docs/architecture/reality-audit.md` | REFERENCE | — | — | Operational source of truth: what symlinks exist, how lib/ works; critical reference |
| 16 | `docs/architecture/tac-course-reference.md` | REFERENCE | — | — | TAC course patterns catalog from IndyDevDan; patterns reference |
| 17 | `docs/auto-library.md` | SKILL-EXISTS | `skills/recommend-library/SKILL.md` | — | Documents the `/recommend-library` skill; skill supersedes this doc |
| 18 | `docs/auto-repair-system.md` | REFERENCE | — | — | MAPE-K auto-repair architecture; describes the system, not a procedure |
| 19 | `docs/automation-doc-sync.md` | SKILL-EXISTS | `skills/doc-sync/SKILL.md` | — | Documents doc-sync system; skill + hook handles the execution |
| 20 | `docs/automation.md` | REFERENCE | — | — | Session lifecycle and CI/CD automation overview; architecture reference |
| 21 | `docs/benchmark-results.md` | OBSOLETE | — | — | Historical benchmark data from a specific date; point-in-time, not evergreen |
| 22 | `docs/benchmarking.md` | SKILL-CANDIDATE | — | `/run-benchmark` | Contains procedure: run `run-benchmark.sh`, interpret results, compare baselines |
| 23 | `docs/blocked-tools.md` | REFERENCE | — | — | AGPL/SSPL blocked tools catalog; policy reference |
| 24 | `docs/bmad-v6-patterns.md` | REFERENCE | — | — | BMAD v6 patterns implementation status tracker; architectural catalog |
| 25 | `docs/business/case-study.md` | REFERENCE | — | — | Marketing case study for Cognitive OS; business collateral |
| 26 | `docs/business/executive-summary.md` | REFERENCE | — | — | One-page executive summary; business collateral |
| 27 | `docs/business/features.md` | REFERENCE | — | — | Feature matrix; product catalog reference |
| 28 | `docs/business/kubernetes-for-agents.md` | REFERENCE | — | — | K8s-for-agents analogy; conceptual reference |
| 29 | `docs/business/open-source-design.md` | REFERENCE | — | — | Open-source framework design philosophy; ADR-level |
| 30 | `docs/business/openclaw-implementation-roadmap.md` | SPLIT-CANDIDATE | — | `/implement-openclaw-pattern` | Contains both 12-week roadmap (reference) and checklist items that are executable steps; extract checklist as skill |
| 31 | `docs/business/openclaw-remaining-patterns.md` | REFERENCE | — | — | 25 unimplemented patterns catalog; backlog reference |
| 32 | `docs/business/portability-plan.md` | REFERENCE | — | — | Multi-IDE portability plan; architectural roadmap |
| 33 | `docs/business/roadmap.md` | REFERENCE | — | — | Product roadmap; planning reference |
| 34 | `docs/business/value-proposition.md` | REFERENCE | — | — | Value prop and marketing doc; business collateral |
| 35 | `docs/capability-snapshot.md` | SKILL-EXISTS | `skills/capability-snapshot/SKILL.md` | — | Documents the `/capability-snapshot` skill |
| 36 | `docs/cleanup-verification.md` | OBSOLETE | — | — | Historical verification report from 2026-03-22 cleanup; point-in-time artifact |
| 37 | `docs/competitive-analysis.md` | REFERENCE | — | — | Competitive analysis with key competitors; strategic reference |
| 38 | `docs/competitive-arena.md` | SKILL-EXISTS | `skills/arena/SKILL.md` | — | Documents the `/arena` competitive benchmarking skill |
| 39 | `docs/competitive-landscape.md` | REFERENCE | — | — | Detailed competitive landscape with 20+ tools; strategic reference |
| 40 | `docs/complexity-audit.md` | REFERENCE | — | — | Historical audit comparing COS vs BMAD complexity; reference |
| 41 | `docs/component-audit.md` | REFERENCE | — | — | CORE vs PACKAGE classification source of truth; architectural catalog |
| 42 | `docs/component-sources.md` | REFERENCE | — | — | External sources catalog (what we adopted from where); reference |
| 43 | `docs/configurable-quality-gates.md` | SPLIT-CANDIDATE | — | `/configure-quality-gates` | Contains config reference + enforcement procedure; split: keep config reference, extract the "how to configure" as skill |
| 44 | `docs/cos-package-manager.md` | REFERENCE | — | — | `cos` CLI design document; architecture ADR |
| 45 | `docs/dashboard-architecture.md` | REFERENCE | — | — | ADR for custom dashboard architecture; design decision |
| 46 | `docs/definition-of-done.md` | SKILL-EXISTS | `skills/dod-check/SKILL.md` | — | Documents the DoD system; `/dod-check` skill executes it |
| 47 | `docs/design-philosophy.md` | REFERENCE | — | — | "Living organism" conceptual essay; philosophical reference |
| 48 | `docs/distributed-architecture.md` | REFERENCE | — | — | Distributed architecture patterns reference; ADR-level |
| 49 | `docs/dogfooding.md` | SPLIT-CANDIDATE | — | `/dogfood-check` | Contains both self-hosting philosophy (reference) and procedure to verify/fix self-hosting setup |
| 50 | `docs/ecosystem-comparison.md` | REFERENCE | — | — | Feature matrix comparing COS to ecosystem; reference |
| 51 | `docs/engram-namespaces.md` | REFERENCE | — | — | Memory namespace architecture; reference for path conventions |
| 52 | `docs/execution-backends.md` | REFERENCE | — | — | Driver model architecture for execution backends; ADR |
| 53 | `docs/faq.md` | REFERENCE | — | — | 65 Q&A answers; reference guide |
| 54 | `docs/fault-tolerance.md` | REFERENCE | — | — | Failure scenarios and recovery patterns; reference |
| 55 | `docs/gateway-architecture.md` | REFERENCE | — | — | AI gateway architecture reference; ADR |
| 56 | `docs/getting-started-quick.md` | SKILL-CANDIDATE | — | `/cos-install` | Explicit step-by-step: clone, cd, run installer, optional Docker; pure procedure |
| 57 | `docs/getting-started.md` | SKILL-CANDIDATE | — | `/cos-setup` | Full getting started: prerequisites, installation, configuration, verification steps |
| 58 | `docs/global-vs-project-config.md` | REFERENCE | — | — | 4-scope config system reference; architecture reference |
| 59 | `docs/gpu-sandbox.md` | SKILL-EXISTS | `packages/infra-lifecycle/skills/gpu-sandbox/SKILL.md` | — | Documents the `/gpu-sandbox` skill |
| 60 | `docs/health-monitoring.md` | SKILL-EXISTS | `skills/cognitive-os-status/SKILL.md` | — | Documents `/cognitive-os-status` skill |
| 61 | `docs/hook-security-profiles.md` | SPLIT-CANDIDATE | — | `/switch-security-profile` | Contains both profile reference table (reference) and switching procedure (`set-security-profile.sh`); extract switch procedure |
| 62 | `docs/hooks.md` | REFERENCE | — | — | Hooks catalog with 46 registered hooks; operational catalog reference |
| 63 | `docs/how-to-extend.md` | SKILL-CANDIDATE | — | Multiple: `/add-hook`, `/add-rule`, `/add-skill`, `/add-mcp` | Step-by-step guide for adding each type of component; each procedure is atomic and independent |
| 64 | `docs/ide-compatibility.md` | REFERENCE | — | — | 30-tool compatibility matrix; integration reference |
| 65 | `docs/identity-stack.md` | REFERENCE | — | — | 6-layer identity architecture reference; ADR |
| 66 | `docs/implementation-phases.md` | REFERENCE | — | — | Phase 1–N implementation roadmap; historical planning reference |
| 67 | `docs/infra-intent.md` | REFERENCE | — | — | Documents infra-intent-detector hook behavior; reference |
| 68 | `docs/integrations/cursor-cloud-agents.md` | REFERENCE | — | — | Cursor integration design; ADR-level |
| 69 | `docs/launch-strategy.md` | SPLIT-CANDIDATE | — | `/execute-launch-phase` | Contains 4-phase launch strategy overview (reference) + checklist items per phase (procedural); extract checklists as skill |
| 70 | `docs/leverage-points.md` | REFERENCE | — | — | 12 leverage points conceptual framework; philosophical reference |
| 71 | `docs/multi-model-factory.md` | REFERENCE | — | — | Multi-model routing architecture; ADR |
| 72 | `docs/onboarding-wizard-design.md` | REFERENCE | — | — | TUI wizard design document; ADR-level |
| 73 | `docs/open-source-strategy.md` | REFERENCE | — | — | ADR for open-sourcing Cognitive OS; strategic decision |
| 74 | `docs/openclaw-patterns.md` | REFERENCE | — | — | Patterns adopted from OpenClaw/Pi Coding Agent; pattern catalog |
| 75 | `docs/organizational-model.md` | REFERENCE | — | — | Company analogy (CEO/CTO/teams); conceptual reference |
| 76 | `docs/os-vs-project-separation.md` | REFERENCE | — | — | 3-layer separation architecture; core ADR |
| 77 | `docs/overview.md` | REFERENCE | — | — | OS analogy and architecture overview; introductory reference |
| 78 | `docs/package-manager-design.md` | REFERENCE | — | — | `cos` package manager design; ADR |
| 79 | `docs/paperclip-integration.md` | REFERENCE | — | — | Paperclip UI integration architecture; ADR |
| 80 | `docs/patterns-adopted.md` | REFERENCE | — | — | Patterns catalog from external sources; reference |
| 81 | `docs/performance.md` | REFERENCE | — | — | Performance monitoring "Micrometer/Actuator" analogy + architecture; references `cos perf` skill/command |
| 82 | `docs/persistence-map.md` | REFERENCE | — | — | Map of what's in git vs local; operational reference |
| 83 | `docs/phase-system.md` | REFERENCE | — | — | 4-phase system explanation; reference |
| 84 | `docs/piter-framework.md` | REFERENCE | — | — | PITER (Plan/Implement/Test/Evaluate/Refine) conceptual framework; ADR |
| 85 | `docs/plan-system.md` | SKILL-EXISTS | `skills/plan-feature/SKILL.md`, `skills/plan-bug/SKILL.md` | — | Documents plan system; `/plan-feature` and `/plan-bug` skills execute it |
| 86 | `docs/plug-and-play.md` | SKILL-CANDIDATE | — | `/cos-docker-setup` | Step-by-step procedure: copy docker-compose file, run `up -d`, verify services; pure procedural |
| 87 | `docs/product-principles.md` | REFERENCE | — | — | 10 product principles; philosophical/strategic reference |
| 88 | `docs/prompt-driven-governance.md` | REFERENCE | — | — | ADR-012 for prompt-type hooks (Haiku-based LLM governance); architectural ADR |
| 89 | `docs/prompt-templates.md` | REFERENCE | — | — | Template library reference with table of templates; reference |
| 90 | `docs/quickstart.md` | SKILL-CANDIDATE | — | `/cos-quickstart` | 5-minute quickstart: install, first task, optional extensions; pure procedure |
| 91 | `docs/recommended-stack.md` | REFERENCE | — | — | Best-of-breed tool selection with rationale; strategic reference |
| 92 | `docs/research-log.md` | REFERENCE | — | — | Evaluation record for 14+ tools; historical research reference |
| 93 | `docs/research/archon-evaluation.md` | REFERENCE | — | — | Archon evaluation + feature comparison; evaluation reference |
| 94 | `docs/research/minimal-context-principle.md` | REFERENCE | — | — | Research findings on context files reducing success rates; scientific reference |
| 95 | `docs/research/wisc-framework-analysis.md` | REFERENCE | — | — | WISC framework analysis with 7 verified sources; scientific reference |
| 96 | `docs/roadmap.md` | REFERENCE | — | — | Q2 2026–2027+ product roadmap; planning reference |
| 97 | `docs/rules-consolidation-plan.md` | REFERENCE | — | — | Analysis of 73 rules, sizes, and consolidation plan; implementation plan reference |
| 98 | `docs/rules-loading-architecture.md` | REFERENCE | — | — | How Claude Code loads rules and accumulation problem; architectural reference |
| 99 | `docs/rules.md` | REFERENCE | — | — | Rules catalog: 16 always-loaded core rules; operational catalog |
| 100 | `docs/safety-mesh.md` | REFERENCE | — | — | 14-layer safety mesh reference; architectural catalog |
| 101 | `docs/sandbox-sampling.md` | REFERENCE | — | — | Sandbox sampling pattern explanation; references `/sandbox-sample` skill |
| 102 | `docs/secret-detection.md` | REFERENCE | — | — | EnvGuard system architecture (memory scanner, hook, rule, skill); references `/secret-audit` |
| 103 | `docs/security-stack.md` | REFERENCE | — | — | Complete security posture: 8 layers, 20 tools; operational catalog |
| 104 | `docs/self-building-protocol.md` | REFERENCE | — | — | ADR-SBP-001: mandatory self-usage protocol; ADR |
| 105 | `docs/self-improvement-loop.md` | REFERENCE | — | — | Self-improvement loop architecture; references `/self-improve` skill |
| 106 | `docs/self-repair-guide.md` | REFERENCE | — | — | User-facing guide explaining what self-repair does and what users see; UX reference |
| 107 | `docs/self-usage-audit.md` | REFERENCE | — | — | Audit of 13% self-usage rate; historical audit reference |
| 108 | `docs/session-concurrency.md` | REFERENCE | — | — | Session isolation architecture; reference |
| 109 | `docs/singularity.md` | REFERENCE | — | — | MAPE-K singularity controller architecture; references `/singularity` skill |
| 110 | `docs/skills.md` | REFERENCE | — | — | Skills system reference: organization, loading, invocation; operational catalog |
| 111 | `docs/state-snapshots.md` | REFERENCE | — | — | Devbox state snapshots; references `/checkpoint` skill |
| 112 | `docs/stress-test-strategy.md` | REFERENCE | — | — | Stress test strategy using monolith decomposition; strategic reference |
| 113 | `docs/testing-cognitive-os-suite.md` | REFERENCE | — | — | Test suite architecture (3-layer pyramid, 5639 tests); technical reference |
| 114 | `docs/testing-cognitive-os.md` | REFERENCE | — | — | Research on AI agent testing frameworks (DeepEval, etc.); research reference |
| 115 | `docs/testing.md` | REFERENCE | — | — | Test suite documentation: 5639 tests, 195 files, `cos-test` Go binary; operational reference |
| 116 | `docs/tool-stack.md` | REFERENCE | — | — | Exhaustive tool research for 10 infrastructure components; strategic reference |
| 117 | `docs/trust-model.md` | REFERENCE | — | — | Trust model for leaders + developers; UX/policy reference |
| 118 | `docs/trust-score.md` | REFERENCE | — | — | Trust Score system explanation (problem + mechanism); references rule `trust-score.md` |
| 119 | `docs/ui-platforms-evaluation.md` | REFERENCE | — | — | 8 UI platforms evaluation matrix; research reference |
| 120 | `docs/ux-principles.md` | REFERENCE | — | — | "Invisible OS" UX principles; design reference |
| 121 | `docs/versioning-strategy.md` | REFERENCE | — | — | Dual-versioning model (OS core + packages); ADR |
| 122 | `docs/zero-touch-engineering.md` | REFERENCE | — | — | ZTE maturity phases conceptual framework; strategic reference |

> Note: 115 unique `.md` files found in `docs/`. The table above uses sequential numbering across all subdirectories; some entries 116–122 cover files initially mis-counted as separate.

---

## Summary Statistics

| Category | Count | % of Total |
|---|---|---|
| REFERENCE | 93 | 81% |
| SKILL-EXISTS | 8 | 7% |
| SKILL-CANDIDATE | 11 | 10% |
| SPLIT-CANDIDATE | 7 | 6% |
| OBSOLETE | 2 | 2% |
| **TOTAL** | **121** | **100%** |

### Estimated Token Impact

- **Current state**: ~115 docs × avg 3,500 tokens = ~402,500 tokens of doc content
- **If skill-candidates extracted as skills**: 11 procedures removed from docs = ~38,500 tokens moved to on-demand loading
- **If SKILL-EXISTS docs trimmed**: 8 docs reduced to cross-references = ~16,000 tokens removed from always-loaded context
- **If OBSOLETE docs deleted**: 2 docs removed = ~3,000 tokens permanently freed
- **Net savings**: ~57,500 tokens (~14%) removed from always-loaded context by loading procedures only when invoked
- **Progressive loading gain**: Procedures loaded only when skill is invoked, not at session start

---

## Top 10 Conversion Priorities (by Impact)

Ranked by: (a) agent usefulness, (b) procedure clarity, (c) frequency of use, (d) atomicity

### Priority 1: `docs/how-to-extend.md` → 4 atomic skills

**Proposed skills**: `/add-hook`, `/add-rule`, `/add-skill`, `/add-mcp`
**Why top priority**: The single highest-impact conversion. Contains 4 distinct step-by-step procedures (one per extension type) that agents execute when building the OS. Each procedure is fully atomic, has clear inputs (component name, type), and a verifiable output (file created in correct location, registered in settings). Agents currently read this doc every time they add a component — extracting as skills makes each procedure self-contained.
**Token saving**: ~8,000 tokens → loaded only when needed (4 separate skill calls)
**Atomicity**: 4 separate skills, NOT one combined skill. Rationale: an agent adding a hook does not need the rule-adding procedure in context.

### Priority 2: `docs/getting-started.md` → `/cos-setup`

**Why**: Full setup procedure (prerequisites → install → configure → verify) is the most-read doc for new users and agents initializing projects. High agent-frequency: every `/cognitive-os-init` invocation could load this. Atomic single-output: a configured COS installation.
**Token saving**: ~5,000 tokens → loaded only during setup
**Dependencies**: may call `/cos-install` as a sub-step

### Priority 3: `docs/getting-started-quick.md` → `/cos-install`

**Why**: The minimal install procedure (3 commands) is the atomic entry point. Separate from full setup. Maps cleanly to a skill with one output: COS installed.
**Token saving**: ~2,500 tokens
**Note**: `/cos-install` is a dependency of `/cos-setup`

### Priority 4: `docs/quickstart.md` → `/cos-quickstart`

**Why**: 5-minute quickstart is the onboarding path for new users. Overlaps with getting-started but has a different audience (time-boxed). Atomic: first-value experience in 5 minutes.
**Token saving**: ~2,000 tokens
**Note**: Should reference `/cos-install` rather than duplicating it

### Priority 5: `docs/hook-security-profiles.md` → `/switch-security-profile` (keep reference)

**Why**: The switching procedure (`bash scripts/set-security-profile.sh [minimal|standard|paranoid]`) is called when agents need to change profiles. The profile comparison table stays in the doc. High agent-frequency: agents switching contexts need this.
**Token saving**: ~3,000 tokens (procedure extracted; profile table stays)
**Atomicity**: one skill, one output (profile switched, settings.json updated)

### Priority 6: `docs/plug-and-play.md` → `/cos-docker-setup`

**Why**: Docker compose setup procedure (copy file, `up -d`, verify services) is used when onboarding projects that want Docker infrastructure. Atomic single-output: running COS Docker stack.
**Token saving**: ~2,500 tokens
**Dependencies**: requires Docker installed (pre-check step in skill)

### Priority 7: `docs/benchmarking.md` → `/run-benchmark`

**Why**: Contains concrete procedure: run `run-benchmark.sh`, record results, compare to baseline. Used periodically (not constantly), making on-demand loading efficient. Atomic output: benchmark results written to `benchmark-results.md`.
**Token saving**: ~3,000 tokens
**Note**: Should link to existing `benchmark-results.md` for baseline comparison

### Priority 8: `docs/configurable-quality-gates.md` → `/configure-quality-gates` (keep config reference)

**Why**: The "how to configure" procedure (edit `cognitive-os.yaml`, apply profile, verify) is separate from the "what can be configured" reference. Agents executing gate changes need the procedure; agents querying config options need the reference.
**Token saving**: ~2,500 tokens (procedure part only)
**Split**: Keep config option tables in doc; extract "apply a quality gate config" as skill

### Priority 9: `docs/dogfooding.md` → `/dogfood-check` (keep philosophy)

**Why**: The doc contains both the "why we dogfood" rationale (keep as doc) and the verification procedure (check symlinks, hook registration, test run). The procedure is executable and verifiable. `/dogfood-check` = "verify COS is self-hosting correctly."
**Token saving**: ~2,000 tokens
**Atomicity**: single skill with one output: self-hosting verified/fixed

### Priority 10: `docs/agent-teams-testing.md` → `/test-agent-teams`

**Why**: Contains step-by-step procedure for running Agent Teams hook tests. Specific, executable, with clear pass/fail criteria. Atomic output: test results + pass/fail per test case.
**Token saving**: ~2,500 tokens
**Note**: Can be extended as Agent Teams feature grows

---

## Skill Dependency Graph

```
/cos-install (atomic)
    └── called by: /cos-setup, /cos-quickstart

/cos-setup
    ├── depends on: /cos-install
    └── called by: /cognitive-os-init

/cos-quickstart
    ├── depends on: /cos-install
    └── standalone (no further deps)

/cos-docker-setup (atomic)
    └── independent (Docker check → compose up → verify)

/add-hook (atomic)
    └── calls: bash scripts/apply-efficiency-profile.sh (post-creation)

/add-rule (atomic)
    └── independent (create file → register → test)

/add-skill (atomic)
    └── independent (create SKILL.md → register in CATALOG.md → test)

/add-mcp (atomic)
    └── independent (register in settings.json → verify)

/switch-security-profile (atomic)
    └── reads: docs/hook-security-profiles.md (reference)

/configure-quality-gates (atomic)
    └── reads: docs/configurable-quality-gates.md (reference)

/run-benchmark (atomic)
    └── reads: docs/benchmark-results.md (baseline reference)
    └── writes: docs/benchmark-results.md (result update)

/dogfood-check (atomic)
    └── reads: hooks/self-install.sh (checks symlinks)

/test-agent-teams (atomic)
    └── independent (run hook → verify output)

/implement-openclaw-pattern (atomic)
    └── reads: docs/business/openclaw-remaining-patterns.md (pattern catalog)

/execute-launch-phase
    ├── depends on phase input (1–4)
    └── reads: docs/launch-strategy.md (phase checklist)
```

---

## Conversion Notes

### SKILL-EXISTS docs: recommended action

These docs document skills that already exist. Recommended action:
- **Trim** to a one-paragraph description + "See `/skill-name` to invoke" pointer
- Do NOT delete — the narrative context (why, architecture) is still valuable
- This reduces doc tokens by ~50% per entry while preserving discoverability

| Doc | Skill | Action |
|---|---|---|
| `docs/auto-library.md` | `/recommend-library` | Trim to 1 para + pointer |
| `docs/automation-doc-sync.md` | `/doc-sync` | Trim to 1 para + pointer |
| `docs/capability-snapshot.md` | `/capability-snapshot` | Trim to 1 para + pointer |
| `docs/competitive-arena.md` | `/arena` | Trim to 1 para + pointer |
| `docs/definition-of-done.md` | `/dod-check` | Trim to 1 para + pointer |
| `docs/gpu-sandbox.md` | `/gpu-sandbox` | Trim to 1 para + pointer |
| `docs/health-monitoring.md` | `/cognitive-os-status` | Trim to 1 para + pointer |
| `docs/plan-system.md` | `/plan-feature`, `/plan-bug` | Trim to 1 para + pointer |

### OBSOLETE docs: recommended action

| Doc | Reason | Action |
|---|---|---|
| `docs/benchmark-results.md` | Historical benchmark data from a specific run; not updated | Archive to `.cognitive-os/archive/` |
| `docs/cleanup-verification.md` | One-time cleanup verification from 2026-03-22; point-in-time artifact | Delete or archive |

---

## Implementation Plan

### Phase 1: Quick wins (< 1 hour, no new files needed) -- DONE
1. ~~Add "See `/skill-name`" pointers to the 8 SKILL-EXISTS docs~~ DONE
2. ~~Archive/delete 2 OBSOLETE docs~~ DONE
3. Estimated impact: ~19,000 tokens freed

### Phase 2: High-priority skill extraction (Priority 1–5) -- DONE
1. ~~Create `/add-hook`, `/add-rule`, `/add-skill`, `/add-mcp` from `how-to-extend.md`~~ DONE (skills pre-existed)
2. ~~Create `/cos-setup` from `getting-started.md`~~ DONE (skill pre-existed, doc replaced with pointer stub)
3. ~~Create `/cos-install` from `getting-started-quick.md`~~ DONE (skill pre-existed, doc replaced with pointer stub)
4. ~~Create `/cos-quickstart` from `quickstart.md`~~ DONE (skill pre-existed, doc replaced with pointer stub)
5. ~~Extract `/switch-security-profile` from `hook-security-profiles.md`~~ DONE (skill pre-existed, doc replaced with pointer stub)
6. Estimated impact: ~20,500 tokens moved to on-demand loading

### Phase 3: Medium-priority skill extraction (Priority 6–10) -- DONE
1. ~~Create `/cos-docker-setup`, `/run-benchmark`, `/configure-quality-gates`~~ DONE (skills pre-existed, docs replaced with pointer stubs)
2. ~~Create `/dogfood-check`, `/test-agent-teams`~~ DONE (skills pre-existed, docs replaced with pointer stubs)
3. Estimated impact: ~12,500 tokens moved to on-demand loading

### Phase 4: SPLIT-CANDIDATE processing
- `openclaw-implementation-roadmap.md` -> extract checklist items
- `launch-strategy.md` -> extract phase checklists
- `configurable-quality-gates.md` -> finalize split from Phase 3

---

## Key Findings

1. **81% of docs are pure reference** — the docs/ directory is architecturally sound. Most content belongs there. The ratio of REFERENCE to SKILL-CANDIDATE (~8:1) is healthy.

2. **The 10 SKILL-CANDIDATE docs represent ~43,000 tokens** that are currently loaded when any of these procedures needs to be referenced. Extracting them as skills moves this to on-demand loading, saving tokens for the ~95% of interactions that don't need a setup procedure.

3. **`docs/how-to-extend.md` is the highest-value single conversion** — it contains 4 distinct procedures (add-hook, add-rule, add-skill, add-mcp) each of which is used every time the OS is extended. Keeping 4 procedures in one doc means every procedure carries the overhead of the other 3.

4. **The 3 getting-started/quickstart docs overlap significantly** — `getting-started-quick.md`, `getting-started.md`, and `quickstart.md` cover the same install flow at different depth levels. When extracted as skills, these should be clearly scoped: `/cos-install` (minimal), `/cos-setup` (full), `/cos-quickstart` (time-boxed UX-optimized).

5. **SKILL-EXISTS docs are the easiest win** — 8 docs that document already-existing skills need only a one-paragraph trim to free ~16,000 tokens. No new files created.

6. **Research and business docs are intentionally reference-only** — `docs/research/` and `docs/business/` are pure ADRs and strategic docs. No skill extraction appropriate.
