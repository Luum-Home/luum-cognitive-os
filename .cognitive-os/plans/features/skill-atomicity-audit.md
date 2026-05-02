<!--
RECONCILIATION STATUS: LIVE
Related ADRs: ws4 Phase 1 shipment (commit 01c4c6d — 10 new atomic skills across release-os/cognitive-os-init/self-improve)
Reconciled: 2026-04-21
Remaining scope: Phase 1 split the top-3 fattest skills; the remaining ~95 SKILL.md files classified as SPLIT-CANDIDATE/EMBEDDED/COUPLED in this audit have NOT been processed. This is the actionable backlog for atomicity work.
-->

# Skill Atomicity Audit — Cognitive OS

**Date**: 2026-04-10
**Scope**: All 98 SKILL.md files across `skills/` and `packages/*/skills/`
**Purpose**: Identify skills that violate atomicity, embed domain knowledge, or lack composability contracts

---

## Classification Dimensions

### Atomicity
- **ATOMIC**: Does exactly one thing, produces exactly one output artifact
- **COMPOSITE**: Multiple tightly-coupled phases acceptable as a workflow unit
- **SPLIT-CANDIDATE**: Multiple independent concerns that should be separate skills
- **META**: Thin orchestration wrapper around other skills (acceptable)

### Knowledge Separation
- **CLEAN**: Procedure only; references external knowledge (rules/config/runtime)
- **EMBEDDED**: Contains domain/architecture knowledge that belongs in rules or config
- **COUPLED**: Tightly coupled to specific project structure (hardcoded paths/services/frameworks)

### Composability
- **COMPOSABLE**: Clear input/output contract enabling pipeline chaining
- **STANDALONE**: Works alone; output is a human report, not machine-readable
- **PIPELINE**: Explicitly designed to be part of a chain (reads prior phases, writes next-phase inputs)

---

## Full Classification Table

| # | Skill | Package | Atomicity | Knowledge | Composability | Notes |
|---|-------|---------|-----------|-----------|---------------|-------|
| 1 | scout | skills/ | ATOMIC | CLEAN | COMPOSABLE | Clear input (task+depth), output (SCOUT REPORT) |
| 2 | sdd-explore | skills/ | ATOMIC | CLEAN | PIPELINE | Phase 1 of SDD; reads nothing, writes explore artifact |
| 3 | sdd-continue | skills/ | ATOMIC | CLEAN | PIPELINE | Inspects all SDD state, recommends next phase |
| 4 | sdd-resume | skills/ | ATOMIC | CLEAN | PIPELINE | Resumes SDD from last completed phase |
| 5 | cognitive-os-init | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Detects stack + generates config + creates project files (3 independent concerns) |
| 6 | cognitive-os-status | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Checks 7 subsystems; should be 7 targeted probes or grouped by layer |
| 7 | cognitive-os-test | skills/ | COMPOSITE | CLEAN | STANDALONE | 3-layer pyramid: infra/behavior/quality — tightly coupled by design |
| 8 | release-os | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Validation + version bump + changelog + git tag + push = 5 independent steps |
| 9 | skill-creator | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Creates SKILL.md AND scaffolds cos package — two separate concerns |
| 10 | repo-forensics | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Deep forensic analysis + optional COS comparison = 2 independent paths |
| 11 | run-tests | skills/ | ATOMIC | CLEAN | COMPOSABLE | Auto-detects framework, runs tests, returns exit code + summary |
| 12 | validate-config | skills/ | COMPOSITE | CLEAN | COMPOSABLE | Validates 5 config sources; coupled by shared validation report |
| 13 | reverse-engineer | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Separate analysis per dimension: schema/env/cli/routes/docker/auth |
| 14 | session-manager | skills/ | COMPOSITE | CLEAN | STANDALONE | list/inspect/cleanup are related sub-commands of one domain |
| 15 | session-report-executive | skills/ | ATOMIC | EMBEDDED | STANDALONE | Good single purpose but hardcodes metric categories from project |
| 16 | queue-drain | skills/ | ATOMIC | CLEAN | COMPOSABLE | Single concern: drain dispatch queue and launch ready agents |
| 17 | red-team | skills/ | ATOMIC | CLEAN | COMPOSABLE | Runs Promptfoo red-team; clear input (skill) and output (report) |
| 18 | resource-governor | skills/ | SPLIT-CANDIDATE | CLEAN | STANDALONE | Multi-source analysis (tokens + infra + budget) + 5 efficiency metrics + dashboard |
| 19 | compat-test | skills/ | COMPOSITE | CLEAN | STANDALONE | 8 compatibility tests are logically one suite |
| 20 | vulnerability-scan | skills/ | ATOMIC | CLEAN | COMPOSABLE | Runs Garak probes; clear scope and output |
| 21 | caveman | skills/ | ATOMIC | CLEAN | STANDALONE | Ultra-compressed communication mode — single behavioral toggle |
| 22 | caveman-compress | skills/ | ATOMIC | CLEAN | COMPOSABLE | Compress memory files to caveman format |
| 23 | caveman-es | skills/ | ATOMIC | CLEAN | STANDALONE | Spanish variant of caveman — nearly duplicate of caveman |
| 24 | agent-stress-test | skills/ | COMPOSITE | CLEAN | STANDALONE | 4-phase cognitive load test — phases are tightly ordered |
| 25 | code-review | skills/ | ATOMIC | CLEAN | STANDALONE | Adversarial code review with Engram integration |
| 26 | pr-review | skills/ | COMPOSITE | CLEAN | STANDALONE | PR diff + review + test/coverage/lint — naturally ordered |
| 27 | component-classifier | skills/ | ATOMIC | CLEAN | COMPOSABLE | CORE vs PACKAGE decision; clear input/output |
| 28 | install-recommended | skills/ | COMPOSITE | CLEAN | STANDALONE | Detect stack + recommend skills — two steps, but tightly coupled |
| 29 | plan-feature | sdd-compound | ATOMIC | EMBEDDED | COMPOSABLE | References ginext/clean arch; architecture knowledge belongs in rules |
| 30 | plan-bug | sdd-compound | ATOMIC | EMBEDDED | COMPOSABLE | RCA + fix plan; references project-specific service patterns |
| 31 | sdd-compound | sdd-compound | META | CLEAN | PIPELINE | Post-archive learning extraction; thin wrapper |
| 32 | auto-refine | sdd-compound | ATOMIC | CLEAN | PIPELINE | Analyze failure + build refined prompt + re-launch |
| 33 | batch-runner | sdd-compound | META | CLEAN | PIPELINE | Runs multiple SDD changes sequentially; thin orchestration |
| 34 | impact-analysis | sdd-compound | ATOMIC | CLEAN | COMPOSABLE | Blast radius analysis via lib/impact_analysis.py |
| 35 | issue-pipeline | sdd-compound | SPLIT-CANDIDATE | EMBEDDED | STANDALONE | GitHub issue → full SDD → PR; chains 8+ independent skills |
| 36 | evaluate-plan | sdd-compound | ATOMIC | EMBEDDED | COMPOSABLE | Hardcodes ginext/clean arch as evaluation criteria |
| 37 | singularity | sdd-compound | SPLIT-CANDIDATE | CLEAN | STANDALONE | MAPE-K loop (status/run/daemon/dry-run) — 4 independent modes |
| 38 | webhook-trigger | sdd-compound | SPLIT-CANDIDATE | CLEAN | STANDALONE | GitHub webhook server + pipeline launcher = 2 concerns |
| 39 | error-analyzer | skill-governance | COMPOSITE | CLEAN | COMPOSABLE | Error pattern clustering + skill improvement proposals — tightly ordered |
| 40 | self-improve | skill-governance | SPLIT-CANDIDATE | CLEAN | STANDALONE | KPI analysis + propose improvements + apply improvements = 3 concerns |
| 41 | optimize-skill | skill-governance | ATOMIC | CLEAN | COMPOSABLE | Karpathy loop for iterative skill optimization — single concern |
| 42 | model-optimizer | skill-governance | ATOMIC | CLEAN | COMPOSABLE | Analyze metrics → update routing table |
| 43 | metrics-calibrator | skill-governance | COMPOSITE | CLEAN | COMPOSABLE | Calibrate thresholds + propose + apply — tightly ordered pipeline |
| 44 | agent-kpis | task-management | SPLIT-CANDIDATE | CLEAN | STANDALONE | 5 OKR categories from multi-source aggregation — each OKR is independent |
| 45 | capability-snapshot | task-management | COMPOSITE | CLEAN | COMPOSABLE | save/diff/restore are related sub-commands |
| 46 | sprint | task-management | SPLIT-CANDIDATE | CLEAN | STANDALONE | plan/status/retro/blockers/close = 5 independent sprint operations |
| 47 | systematic-debugging | verification-audit | COMPOSITE | CLEAN | PIPELINE | 4-phase root cause investigation — phases are sequentially dependent |
| 48 | test-driven-development | verification-audit | COMPOSITE | CLEAN | PIPELINE | Red-Green-Refactor is inherently 3-phase |
| 49 | trust-audit | verification-audit | ATOMIC | CLEAN | COMPOSABLE | Trust score aggregation + overclaiming detection — single domain |
| 50 | verification-before-completion | verification-audit | ATOMIC | CLEAN | COMPOSABLE | Evidence-before-claims gate — single purpose |
| 51 | cognitive-os-benchmark | verification-audit | COMPOSITE | EMBEDDED | STANDALONE | COS vs BMAD v6 benchmarks; embeds benchmark criteria |
| 52 | coverage-enforcement | verification-audit | ATOMIC | COUPLED | COMPOSABLE | Hardcodes `backend-go/apps/` service paths |
| 53 | harness-audit | verification-audit | ATOMIC | CLEAN | COMPOSABLE | Evaluates hooks/rules/skills for continued relevance |
| 54 | smoke-test | verification-audit | COMPOSITE | EMBEDDED | STANDALONE | 5-phase E2E; embeds expected service/endpoint assumptions |
| 55 | readiness-check | quality-gates | ATOMIC | EMBEDDED | COMPOSABLE | Hardcodes ginext/clean arch as readiness criteria |
| 56 | dod-check | quality-gates | ATOMIC | CLEAN | COMPOSABLE | Verifies DoD criteria per complexity level — single purpose |
| 57 | security-audit | quality-gates | COMPOSITE | CLEAN | STANDALONE | Secrets + hooks + permissions + infra = 4 domains, but logically one audit |
| 58 | confidence-check | quality-gates | ATOMIC | CLEAN | COMPOSABLE | 5-dimension pre-implementation confidence gate |
| 59 | pentest-self | quality-gates | COMPOSITE | CLEAN | STANDALONE | Multiple penetration test categories — single domain |
| 60 | resolve-blockers | quality-gates | META | CLEAN | PIPELINE | Dispatches sub-agents to fix readiness blockers |
| 61 | nemo-guardrails | quality-gates | ATOMIC | COUPLED | COMPOSABLE | Generates NeMo Guardrails rules from COS rules — coupled to NeMo schema |
| 62 | self-review | adaptive-workflow | ATOMIC | CLEAN | COMPOSABLE | 4-question post-impl checklist — clear single purpose |
| 63 | retrospective | agent-coordination | COMPOSITE | CLEAN | STANDALONE | Weekly org analysis: collect + compare + analyze + propose = ordered pipeline |
| 64 | squad-manager | agent-coordination | COMPOSITE | CLEAN | STANDALONE | Load squads + collect metrics + calculate + compare + report |
| 65 | persistent-agent | agent-lifecycle | ATOMIC | CLEAN | COMPOSABLE | Creates agent scaffolding (SKILL.md + data/) — single output |
| 66 | resume-tasks | agent-lifecycle | ATOMIC | CLEAN | COMPOSABLE | Recovery skill: check tasks + present summary + offer re-launch |
| 67 | auto-rollback | auto-repair-rollback | ATOMIC | CLEAN | PIPELINE | Reverts failed apply commits; clear trigger and output |
| 68 | compose-prompt | context-optimization | ATOMIC | CLEAN | COMPOSABLE | Assembles sub-agent prompt from templates — single output |
| 69 | exhaustive-prompt | context-optimization | ATOMIC | CLEAN | COMPOSABLE | Scope enumeration + exhaustive prompt — single output artifact |
| 70 | doc-sync | document-sync | ATOMIC | CLEAN | STANDALONE | Processes stale-docs.jsonl and updates docs — single concern |
| 71 | document-feature | document-sync | COMPOSITE | CLEAN | STANDALONE | 3-layer detection + write docs; tightly coupled |
| 72 | arena | dry-run-simulation | SPLIT-CANDIDATE | CLEAN | STANDALONE | Benchmark runner + evaluator + reporter = 3 independent modes |
| 73 | simulation-arena | dry-run-simulation | COMPOSITE | CLEAN | STANDALONE | Scenario runner + comparison + evolution report — ordered pipeline |
| 74 | audit-website | ecosystem-tools | COMPOSITE | CLEAN | STANDALONE | 6-category website audit — logically one assessment |
| 75 | automaker-bridge | ecosystem-tools | ATOMIC | CLEAN | STANDALONE | Configure AutoMaker + COS integration — single setup task |
| 76 | cognee-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + add knowledge + search = 3 independent sub-commands |
| 77 | cognee-search | ecosystem-tools | ATOMIC | CLEAN | COMPOSABLE | Semantic graph search — single clear purpose |
| 78 | deepeval-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + test skills + red-team = 3 independent sub-commands |
| 79 | jupyter-execute | ecosystem-tools | ATOMIC | CLEAN | COMPOSABLE | Execute code in Jupyter sandbox — single purpose |
| 80 | opik-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + trace + eval = 3 independent sub-commands |
| 81 | promptfoo-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + regression test + red-team = 3 independent sub-commands |
| 82 | ragas-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + eval-memory + generate-tests = 3 sub-commands |
| 83 | recommend-library | ecosystem-tools | ATOMIC | CLEAN | COMPOSABLE | Search registries + rank + recommend — single output |
| 84 | secret-audit | ecosystem-tools | ATOMIC | COUPLED | STANDALONE | Hardcodes TypeScript/Go/Java service paths |
| 85 | semgrep-scan | ecosystem-tools | ATOMIC | CLEAN | COMPOSABLE | Run Semgrep on scope — single output format |
| 86 | strands-evals-integration | ecosystem-tools | SPLIT-CANDIDATE | CLEAN | STANDALONE | Setup + instrument + evaluate = 3 sub-commands |
| 87 | tool-discovery | ecosystem-tools | ATOMIC | CLEAN | STANDALONE | Scan GitHub/web for new tools — single report output |
| 88 | web-crawler | ecosystem-tools | ATOMIC | CLEAN | COMPOSABLE | Fetch + convert web content to LLM markdown |
| 89 | devbox-checkpoint | infra-lifecycle | COMPOSITE | CLEAN | COMPOSABLE | save/restore/list/diff are sub-commands of one domain |
| 90 | gpu-sandbox | infra-lifecycle | ATOMIC | CLEAN | COMPOSABLE | Connect to Jupyter runtime for compute-heavy tasks |
| 91 | repair-status | infra-lifecycle | ATOMIC | CLEAN | STANDALONE | Read repair metrics + format report — single purpose |
| 92 | sre-agent | infra-lifecycle | COMPOSITE | CLEAN | STANDALONE | Discover + collect + scan + repair + report — ordered monitoring pipeline |
| 93 | paperclip-dashboard | paperclip-integration | COMPOSITE | CLEAN | STANDALONE | Gather metrics + push to Paperclip + format terminal output |
| 94 | private-mode | privacy-mode | ATOMIC | CLEAN | STANDALONE | Toggle private mode flag — single behavioral state |
| 95 | conversation-memory | recall-search | COMPOSITE | CLEAN | STANDALONE | Search + pattern mining + self-referential learning — ordered |
| 96 | memu-context | recall-search | ATOMIC | CLEAN | COMPOSABLE | Query memU + Engram for context summary — single output |
| 97 | recall-search | recall-search | ATOMIC | CLEAN | COMPOSABLE | Search raw transcripts via recall CLI — single output |
| 98 | contract-drift | scope-governance | ATOMIC | CLEAN | COMPOSABLE | Detect OpenAPI drift — single output artifact |
| 99 | deep-research | scope-governance | COMPOSITE | CLEAN | STANDALONE | Multi-hop research: discover + analyze + compare + synthesize |
| 100 | eval-repo | scope-governance | COMPOSITE | CLEAN | STANDALONE | 3-level assessment: DeepWiki + shallow + deep — ordered |
| 101 | planning-poker | scope-governance | COMPOSITE | CLEAN | COMPOSABLE | 3-perspective estimation + reconciliation — ordered phases |
| 102 | research-protocol | scope-governance | META | CLEAN | COMPOSABLE | Meta-skill defining HOW to research — thin methodology wrapper |
| 103 | sandbox-sample | scope-governance | COMPOSITE | CLEAN | COMPOSABLE | classify + sample + sandbox + verify + scale — ordered safety protocol |

> Note: 98 SKILL.md files were found; after deduplication and full enumeration, 103 distinct skill identities exist (some packages contain multiple sub-commands grouped under one SKILL.md file that were counted separately above for accuracy).

---

## Top 10 Refactoring Candidates

### 1. `issue-pipeline` (sdd-compound) — CRITICAL
**Classification**: SPLIT-CANDIDATE / EMBEDDED / STANDALONE

**Problem**: Chains 8+ independent skills in a single skill: GitHub issue fetch → SDD explore → propose → spec → design → tasks → apply → verify → PR creation. This is not a skill; it is a hardcoded orchestration pipeline. Each phase has independent failure modes, independent retry strategies, and independent outputs. The current design makes it impossible to:
- Retry a single failed phase without re-running everything
- Reuse any phase in a different pipeline
- Monitor progress per phase

**Fix**: Delete `issue-pipeline` and replace with a DAG-based orchestration in the orchestrator using existing SDD phase skills. The GitHub issue fetch and PR creation are the only novel concerns; extract as `gh-issue-fetch` and `gh-pr-create` atomic skills.

---

### 2. `cognitive-os-init` (skills/) — HIGH
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Conflates three independent concerns: (a) stack detection, (b) config generation, and (c) project file creation. Each can fail independently. Stack detection requires reading project files; config generation requires the detection output; project file creation writes to disk. These are sequentially dependent but have different failure modes, different outputs, and could be usefully invoked independently.

**Fix**: Split into `detect-stack` (reads project, produces `detected-stack.json`), `generate-config` (reads detection, produces `cognitive-os.yaml`), and `scaffold-project` (creates `.claude/` structure).

---

### 3. `release-os` (skills/) — HIGH
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Validation + version bump + changelog + git tag + push = 5 sequential operations that are each independently valuable and independently risky. A failed push should not require re-running validation. The current monolith makes rollback ambiguous: if the git push fails, was the tag already applied?

**Fix**: Extract as `validate-release`, `bump-version`, `generate-changelog`, `tag-release`, `push-release`. The orchestrator composes them. Matches the existing SDD pipeline pattern.

---

### 4. `singularity` (sdd-compound) — HIGH
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Four completely independent modes (`status`, `run`, `daemon`, `dry-run`) are bundled into one skill with a long routing table. Each mode does fundamentally different work: status reads metrics, run executes one MAPE-K cycle, daemon runs continuously, dry-run previews. The bundling makes each mode harder to test and harder to invoke from scripts.

**Fix**: Separate into `singularity-run` (one cycle), `singularity-status` (read-only dashboard), `singularity-daemon` (background loop). The `dry-run` flag is a parameter on `singularity-run`, not a separate mode.

---

### 5. `self-improve` (skill-governance) — HIGH
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Three independent phases: (a) KPI analysis and pattern detection, (b) improvement proposal generation, and (c) automated application. The analysis and proposal are read-only; the application is destructive (modifies rule/skill files). Conflating them removes the human gate between analysis and application.

**Fix**: Split into `analyze-improvements` (read-only analysis, outputs proposals), `propose-improvements` (human-reviewable proposal document), and `apply-improvements` (the destructive phase, requires explicit invocation). This aligns with the SDD pattern of separation between planning and applying.

---

### 6. `coverage-enforcement` (verification-audit) — HIGH
**Classification**: ATOMIC / COUPLED / COMPOSABLE

**Problem**: Hardcodes `backend-go/apps/` as the path to scan. This makes the skill useless for any project that is not the specific luum backend. The skill name implies universal applicability, but the implementation is project-specific.

**Fix**: Read the service root from `cognitive-os.yaml -> project.infrastructure.services_root` or accept it as a parameter. Remove the hardcoded `backend-go/apps/` path. Pattern: `find ${SERVICES_ROOT:-./apps} -name '*.go'`.

---

### 7. `evaluate-plan` (sdd-compound) — MEDIUM
**Classification**: ATOMIC / EMBEDDED / COMPOSABLE

**Problem**: Hardcodes ginext framework and clean architecture layer names as evaluation criteria. A plan for a FastAPI Python project would be incorrectly scored as violating "architecture alignment" because it doesn't use ginext. The domain knowledge (what counts as good architecture) belongs in project-specific rules or config, not in the skill.

**Fix**: Replace hardcoded architecture criteria with a read from `.claude/rules/architecture.md` or a configurable criteria file. The skill becomes a generic "score plan against criteria" engine; the criteria are project-specific.

---

### 8. `readiness-check` (quality-gates) — MEDIUM
**Classification**: ATOMIC / EMBEDDED / COMPOSABLE

**Problem**: Same issue as `evaluate-plan` — hardcodes ginext/clean arch patterns as readiness criteria. A project using Gin (not ginext) would fail readiness even if its architecture is correct. The readiness criteria belong in project config.

**Fix**: Extract architecture-specific checks into `.cognitive-os/templates/readiness-architecture.md`. The skill reads from this file; the file is generated by `cognitive-os-init` based on detected stack.

---

### 9. `agent-kpis` (task-management) — MEDIUM
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Aggregates 5 independent OKR categories (Quality, Efficiency, Self-improvement, Velocity, Security) from different data sources. Each category has independent data requirements and independent interpretation logic. The skill reads from 6+ JSONL files and joins them inline.

**Fix**: Each OKR category becomes a `kpi-quality`, `kpi-efficiency`, `kpi-velocity` etc. atomic skill with a clear output schema. The `agent-kpis` skill becomes a thin META that aggregates and presents the results from each. This makes individual OKRs testable and reusable.

---

### 10. `resource-governor` (skills/) — MEDIUM
**Classification**: SPLIT-CANDIDATE / CLEAN / STANDALONE

**Problem**: Token analysis + Docker container utilization + cost dashboard + model downgrade recommendations + skill efficiency metrics = 5 independent efficiency dimensions. Each has different failure modes (Docker may not be running; cost data may be incomplete) and different remediation actions.

**Fix**: Split into focused probes: `token-efficiency-report`, `infra-utilization-report`, `cost-health-report`. The `resource-governor` becomes a META skill that runs all probes and formats the combined dashboard.

---

## Summary Statistics

### Atomicity Distribution

| Classification | Count | % |
|----------------|-------|---|
| ATOMIC | 44 | 42.7% |
| COMPOSITE | 28 | 27.2% |
| SPLIT-CANDIDATE | 25 | 24.3% |
| META | 6 | 5.8% |

**Key finding**: 25 skills (24%) need splitting. The composite skills are mostly acceptable — they represent natural workflows where phases are sequentially dependent.

### Knowledge Separation Distribution

| Classification | Count | % |
|----------------|-------|---|
| CLEAN | 93 | 90.3% |
| EMBEDDED | 6 | 5.8% |
| COUPLED | 4 | 3.9% |

**Key finding**: Only 10 skills (9.7%) have knowledge contamination. The embedded/coupled issues are concentrated in verification and quality-gates packages, where architecture assumptions leak into generic evaluation logic.

**Skills with EMBEDDED knowledge**:
- `plan-feature`, `plan-bug` (reference ginext/clean arch patterns)
- `evaluate-plan`, `readiness-check` (hardcode architecture as criteria)
- `session-report-executive` (hardcodes metric categories)
- `cognitive-os-benchmark` (embeds benchmark criteria inline)

**Skills with COUPLED knowledge**:
- `coverage-enforcement` (hardcodes `backend-go/apps/`)
- `secret-audit` (hardcodes TypeScript/Go/Java service paths)
- `smoke-test` (assumes specific service endpoints)
- `nemo-guardrails` (coupled to NeMo schema format)

### Composability Distribution

| Classification | Count | % |
|----------------|-------|---|
| COMPOSABLE | 46 | 44.7% |
| STANDALONE | 42 | 40.8% |
| PIPELINE | 15 | 14.5% |

**Key finding**: Pipeline skills are well-represented and appropriately scoped to SDD phases. The standalone skills are mostly correct — reporting and analysis skills naturally produce human output. However, 10+ standalone skills that should be composable lose their composability due to SPLIT-CANDIDATE issues.

---

## Proposed Skill Dependency Graph

### SDD Pipeline Chain (well-defined)
```
sdd-explore → sdd-propose → sdd-spec + sdd-design (parallel) → sdd-tasks → [readiness-check] → sdd-apply → sdd-verify → sdd-archive
                                                                                     ↑
                                                                           evaluate-plan (pre-apply)
```

### Scout → Implementation Chain
```
scout → impact-analysis → exhaustive-prompt → [agent-launch] → self-review → verification-before-completion
```

### Quality Gate Chain (pre-commit)
```
confidence-check → dod-check → self-review → trust-audit → verification-before-completion
```

### Repair/Recovery Chain
```
run-tests → error-analyzer → auto-refine → [retry] → auto-rollback (if exhausted)
resume-tasks → [re-launch failed tasks]
```

### Memory Search Fallback Chain
```
mem_search (Engram) → conversation-memory → recall-search
                           ↓
                      memu-context (if memU running)
                           ↓
                      cognee-search (if Cognee running)
```

### Monitoring/Observability Chain
```
repair-status → sre-agent → paperclip-dashboard
agent-kpis → resource-governor → model-optimizer
```

### Skill Governance Chain
```
error-analyzer → optimize-skill → [test optimized skill] → skill-creator (if new skill needed)
self-improve → metrics-calibrator → model-optimizer
```

### Research Chain
```
research-protocol (meta) → deep-research | eval-repo | repo-forensics
scout (codebase) | recommend-library (library) | tool-discovery (tools)
```

### Agent Lifecycle Chain
```
persistent-agent → [agent runs] → resume-tasks (recovery) | conversation-memory (context)
```

### Context Management Chain
```
compose-prompt → [sub-agent launch] → exhaustive-prompt (if epic task)
sandbox-sample (large tasks) → [scaled execution]
```

---

## Priority Refactoring Plan

### Phase 1: High-Impact Splits (immediate value, low risk)

1. **Split `release-os`** into 5 atomic steps — zero knowledge contamination risk, pure structural split
2. **Split `cognitive-os-init`** into `detect-stack`, `generate-config`, `scaffold-project`
3. **Split `self-improve`** into `analyze-improvements` + `apply-improvements` to enforce the human gate
4. **Replace `issue-pipeline`** with DAG orchestration using existing skills

### Phase 2: Knowledge Extraction (medium-term)

5. **Parameterize `coverage-enforcement`** to read service root from config
6. **Parameterize `readiness-check`** and `evaluate-plan`** to read architecture criteria from `.claude/rules/`
7. **Parameterize `secret-audit`** to discover service paths from `docker-compose.yml` or config
8. **Externalize `plan-feature`/`plan-bug` architecture references** to the architecture rules file

### Phase 3: Composability Improvements (incremental)

9. **Split `agent-kpis`** into per-OKR atomic skills with `agent-kpis` as a META aggregator
10. **Split `singularity`** into `singularity-run`, `singularity-status`, `singularity-daemon`

### Phase 4: Integration sub-command deduplication

11. **Standardize ecosystem tool integration pattern**: `cognee-integration`, `deepeval-integration`, `opik-integration`, `promptfoo-integration`, `ragas-integration`, `strands-evals-integration` all follow setup+use+eval pattern — extract a reusable `tool-integration-template` meta-skill with consistent sub-command protocol

---

## Metric Summary

| Dimension | Good | Needs Work | Critical |
|-----------|------|------------|----------|
| Atomicity | 78 (75.7%) | 25 SPLIT-CANDIDATES | `issue-pipeline`, `release-os`, `cognitive-os-init` |
| Knowledge | 93 (90.3%) | 10 embedded/coupled | `coverage-enforcement`, `readiness-check`, `evaluate-plan` |
| Composability | 61 (59.2%) | 42 standalone | Standalone is often correct; 10 could be improved |

**Overall skill health**: The Cognitive OS skill catalog is in good shape. The majority of atomicity issues are in large orchestration skills that grew organically. The knowledge contamination is limited and concentrated in a few identifiable files. The composability story is strong for the pipeline skills.

**Systemic pattern**: Integration skills (ecosystem-tools package) consistently use the setup+use+evaluate tri-command pattern without a shared template. Standardizing this would reduce 30+ lines of repeated pattern description.

---

## Execution Progress

### Phase 1: High-Impact Splits -- COMPLETED (2026-04-10)

10 skills created from 3 splits. See WS4 Phase 1 commit.

### Phase 2: Knowledge Extraction -- COMPLETED (2026-04-13)

Added `project.architecture` config section to `cognitive-os.yaml` with:
- `frameworks` (per-language framework mapping)
- `layers` (clean architecture layer paths)
- `services_root` (per-language service root directories)
- `service_paths` (explicit service paths for cross-stack scans)
- `evaluation_criteria` (architecture evaluation checklist)

**Skills parameterized (5/5)**:

| Skill | What Changed | Config Key Used |
|-------|-------------|-----------------|
| `coverage-enforcement` | Replaced hardcoded `backend-go/apps/` with config read | `project.architecture.services_root.go` |
| `readiness-check` | Replaced hardcoded "ginext, clean arch layers" with config read | `project.architecture.evaluation_criteria`, `project.architecture.frameworks` |
| `evaluate-plan` | Replaced hardcoded framework names in Architecture Alignment scoring | `project.architecture.evaluation_criteria`, `project.architecture.layers`, `project.architecture.frameworks` |
| `secret-audit` | Replaced hardcoded TS/Go/Java service paths with config read + auto-discovery | `project.architecture.service_paths` |
| `plan-feature` / `plan-bug` | Replaced hardcoded "ginext, clean architecture" references in evaluation | `project.architecture.evaluation_criteria` |

### Phase 3: Split Candidates -- ANALYSIS COMPLETE

**Top 3 fattest skills to split** (ranked by line count and independent concern count):

1. **`resource-governor`** (226 lines, 5 independent dimensions)
   - Split into: `token-efficiency-report`, `infra-utilization-report`, `cost-health-report`
   - `resource-governor` becomes META aggregator
   - Each probe has different failure modes (Docker may not be running; cost data may be incomplete)

2. **`agent-kpis`** (196 lines, 5 independent OKR categories)
   - Split into: `kpi-quality`, `kpi-efficiency`, `kpi-velocity`, `kpi-security`, `kpi-self-improvement`
   - `agent-kpis` becomes META aggregator
   - Each OKR reads from different data sources and can be tested independently

3. **`repo-forensics`** (183 lines, 2 independent analysis paths)
   - Split into: `repo-forensics-analyze` (deep forensic analysis) + `repo-forensics-compare` (COS comparison)
   - The comparison mode is entirely optional and orthogonal to forensic analysis

**Honorable mentions**: `reverse-engineer` (180 lines, 6 dimensions -- but dimensions are sequentially dependent, so COMPOSITE not SPLIT), `webhook-trigger` (138 lines, 2 concerns -- server + pipeline launcher).

### Phase 4: Integration Dedup -- ANALYSIS COMPLETE

**6 integration skills share a common pattern**:
- `cognee-integration` (121 lines)
- `deepeval-integration` (137 lines)
- `opik-integration` (121 lines)
- `promptfoo-integration` (117 lines)
- `ragas-integration` (134 lines)
- `strands-evals-integration` (87 lines)

**Shared structure** (all 6 have):
- `### Prerequisites` section (100% shared)
- `### Configuration` / `### Environment Variables` sections
- 3 sub-command steps (setup/instrument, evaluate/test, report/integrate)

**Recommendation**: Create a `tool-integration-template` meta-skill that defines the shared protocol:
1. Prerequisites check (pip install, env vars)
2. Configure (write config file or set env)
3. Execute primary function (test/evaluate/trace)
4. Report results (standard output format)

Each integration skill would reference the template for shared sections and only define its unique steps. Estimated savings: ~30 lines per skill (180 lines total across 6 skills).

**Additional dedup candidate**: `caveman` and `caveman-es` are identical (55 lines each) except for language. Merge into one skill with a `language` parameter.

### Next Steps

- Phase 3 execution: Split `resource-governor` and `agent-kpis` first (highest independent-concern counts)
- Phase 4 execution: Create `tool-integration-template` and refactor one integration skill as proof of concept
- Merge `caveman` / `caveman-es` into parameterized single skill
