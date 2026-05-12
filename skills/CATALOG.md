<!-- SCOPE: both -->
<!-- Cleaned: removed phantom entries without SKILL.md implementations -->
# Cognitive OS Skills Catalog

> Compact index loaded at session start. Full SKILL.md loaded on demand (Level 2).

## Universal Skills

| Skill | Description | Invoke | Audience |
|-------|-------------|--------|----------|
| add-hook | Add a new lifecycle hook to the OS: create script, register in settings.json, add to efficiency profile, write test | `/add-hook` | os |
| add-rule | Add a new always-active or contextual rule: create .md file, symlink, update RULES-COMPACT.md | `/add-rule` | os |
| add-skill | Add a new skill: create SKILL.md with frontmatter, add to CATALOG.md, write structure test | `/add-skill` | os |
| adr-tombstone | Create neutral ADR tombstones while preserving ADR numbering integrity | `/adr-tombstone` | maintainer |
| add-mcp | Integrate a new MCP server: register in settings.json, document in ecosystem-tools.md, add graceful degradation | `/add-mcp` | os |
| cognitive-os-init | Initialize Cognitive OS for a project: detect stack, generate config and project-specific files | `/cognitive-os-init` | os-dev |
| cognitive-os-test | Run the Cognitive OS automated test suite (infra, behavior, quality) | `/cognitive-os-test` | os-dev |
| cognitive-os-benchmark | Run benchmark comparisons | `/benchmark` | os-dev |
| cognitive-os-status | Report Cognitive OS status: hooks, rules, skills, squads, metrics | `/cognitive-os-status` | both |
| compat-test | Smoke test: verify model compatibility with Cognitive OS (8 checks, < 30s) | `/cognitive-os-compat-test` | os-dev |
| component-classifier | Classify new agentic primitives as CORE or PACKAGE | `/component-classifier` | os-dev |
| validate-config | Validate all Cognitive OS config files: agents, squads, skills, rules, hooks | `/validate-config` | both |
| capability-snapshot | Snapshot, diff, and restore Cognitive OS capabilities to prevent feature loss | `/capability-snapshot` | os-dev |
| self-improve | Self-improvement protocol: detect patterns, create/update skills/rules | `/self-improve` | os-dev |
| metrics-calibrator | Analyze KPI distributions, auto-adjust thresholds, propose derived metrics | `/metrics-calibrator` | os-dev |
| harness-audit | Evaluate harness agentic primitives for relevance, identify retirement candidates | `/harness-audit` | os-dev |
| smoke-test | Run end-to-end smoke tests that validate the real Cognitive OS system works | `/smoke-test` | os-dev |
| proof-drill | Select and run opt-in proof drills and smoke checks for SO self-build and consumer-project validation without polluting default lanes | `/proof-drill` | both |
| test-contract-repair | Repair failing or misleading tests without greenwashing: classify the contract, confirm history, fix runtime when needed, strengthen structural checks into behavioral proof | `/test-contract-repair` | os-dev |
| detect-patterns | Detect systemic problems: dead metadata, broken chains, phantom entries, structural tests | `/detect-patterns` | os-dev |
| security-audit | Comprehensive security audit: secrets, permissions, hooks, infrastructure, Docker ports | `/security-audit` | os-dev |
| security-red-team | Unified security red-team: inventory, threat model, abuse probes, primitive scoring, mitigation backlog | `/security-red-team` | os-dev |
| pentest-self | Self-penetration testing: validate safety mesh across 6 categories | `/pentest-self` | os-dev |
| arena | Run competitive benchmarks against AI coding tools | `/arena` | os-dev |
| simulation-arena | Run scripted scenarios simulating developer workflows, measure safety mesh | `/simulate` | os-dev |
| so-vs-vanilla | A/B governance value benchmark: compare full SO governance vs ungoverned baseline | `/so-vs-vanilla` | os-dev |
| tool-discovery | Discover new open-source tools via GitHub scan, classify, evaluate, propose | `/tool-discovery` | os-dev |
| deps-update | Audit and upgrade Cognitive OS dependencies (engram, brew packages, Python deps, Docker images, Claude plugins) using the canonical `scripts/deps-update.sh` primitive | `/deps-update` | os |
| release-os | META — orchestrate full OS release by chaining 5 atomic release skills | `/release-os` | os |
| validate-release | Pre-release readiness check: clean tree, correct branch, VERSION, CHANGELOG | `/validate-release` | os |
| bump-version | Calculate and write new version to VERSION file (patch/minor/major or explicit) | `/bump-version` | os |
| generate-changelog | Move [Unreleased] CHANGELOG entries into a versioned release section | `/generate-changelog` | os |
| tag-release | Create the release commit (VERSION + CHANGELOG) and annotated git tag | `/tag-release` | os |
| push-release | Push the release commit and tags to remote — always requires explicit confirmation | `/push-release` | os |
| cognee-integration | Configure Cognee for knowledge graph memory and MCP integration | `/cognee-setup` | os-dev |
| deepeval-integration | LLM unit testing, trajectory eval, red teaming (60+ metrics) | `/deepeval-setup` | os-dev |
| ragas-integration | Memory quality testing, retrieval eval, synthetic test generation | `/ragas-setup` | os-dev |
| promptfoo-integration | Prompt regression testing and red teaming in CI/CD | `/promptfoo-setup` | os-dev |
| strands-evals-integration | Trace-based agent trajectory evaluation (OpenTelemetry) | `/strands-setup` | os-dev |
| automaker-bridge | Configure AutoMaker to use Cognitive OS as its execution brain | `/automaker-bridge` | os-dev |
| nemo-guardrails | Generate and configure NeMo Guardrails Colang 2.0 rules from Cognitive OS rules | `/nemo-guardrails` | os-dev |
| agent-kpis | Calculate and report Cognitive OS KPIs, OKRs, health dashboard | `/agent-kpis` | both |
| model-optimizer | Analyze skill metrics, recommend optimal model routing | `/model-optimizer` | both |
| trust-audit | Analyze trust scores: overclaiming detection, trend analysis, review recommendations | `/trust-audit` | both |
| sdd-continue | Enhanced SDD continuation: state inspection, determines optimal next action | `/sdd-continue` | project |
| sdd-resume | Resume an SDD pipeline from its last completed phase with timing and state visibility | `/sdd-resume` | project |
| sdd-explore | Deep feasibility analysis for SDD pipeline explore phase — builds on scout report | `/sdd-explore` | project |
| scout | Quick pre-implementation codebase reconnaissance with 3 depth levels (quick/standard/deep) | `/scout` | project |
| error-analyzer | Analyze accumulated errors, propose skill improvements | `/error-analyzer` | project |
| sre-agent | Monitor services, detect errors, auto-repair safe actions | `/sre-agent` | project |
| squad-manager | Evaluate squad performance, propose reconfigurations | `/squad-report` | project |
| systematic-debugging | 4-phase debugging: reproduce, isolate, hypothesize, verify. Use on bugs | _auto_ | project |
| test-driven-development | RED-GREEN-REFACTOR cycle. Use when implementing features | _auto_ | project |
| verification-before-completion | Evidence gate before claiming done. Run tests, check output | _auto_ | project |
| coverage-enforcement | Run test coverage, enforce thresholds from cognitive-os.yaml | `/coverage-report` | project |
| retrospective | Weekly cross-squad analysis with trend data and reconfig proposals | `/retrospective` | project |
| resume-tasks | Check for incomplete tasks from previous sessions | `/resume-tasks` | project |
| session-backlog | Inventory all pending work across plans, engram, tasks, audits, and git — produces prioritized backlog for future sessions | `/session-backlog` | both |
| decision-triage | Aggregate unanswered operator decisions from research reports and ADRs into a single ranked view. Complements /session-backlog (tasks) — this counts decisions. | `/decision-triage` | both |
| session-wrapup | End-of-session routine: backlog inventory + engram save + session summary | `/session-wrapup` | both |
| session-pending-brief | Bridge prompt → cos-session-start-projector → ranked attack list. |
| session-pending-close | Atomic close of pending-truth task and/or ADR-decision items with audit trail. |
| doc-sync | Detect and update stale documentation after code changes | `/doc-sync` | project |
| doc-review-personas | Multi-persona adversarial doc review: N lenses in parallel, severity-tiered consolidation | `/doc-review-personas` | both |
| private-mode | Toggle private conversation (no persistence, no metrics) | `/private` | project |
| optimize-skill | Iteratively improve a skill using evals and feedback | `/optimize-skill` | project |
| auto-refine | PITER loop: analyze failed agent output, re-launch with refined instructions | `/auto-refine` | project |
| compose-prompt | Compose reusable prompt fragments into complete prompts | `/compose-prompt` | project |
| exhaustive-prompt | Generate exhaustive agent prompts with scope enumeration and acceptance criteria | `/exhaustive-prompt` | project |
| evaluate-plan | Evaluate a plan before implementation, score 0-50 | `/evaluate-plan` | project |
| plan-bug | Plan bug resolution with systematic approach | `/plan-bug` | project |
| plan-feature | Plan feature implementation with phases | `/plan-feature` | project |
| resource-governor | Budget enforcement, model downgrade chain, efficiency metrics | `/resource-governor` | project |
| readiness-check | Implementation readiness gate: validates prerequisites before coding | `/readiness-check` | project |
| sprint | Lightweight sprint tracking: plan, status, retro, course-correct | `/sprint` | project |
| recommend-library | Search npm/PyPI/Go registries, rank by relevance, adoption, license compliance | `/recommend-library` | project |
| dod-check | Verify Definition of Done criteria for a task at a given complexity level | `/dod-check` | project |
| session-manager | Manage concurrent sessions: list active, show current, cleanup stale | `/sessions` | project |
| secret-audit | Scan all services for env var usage, cross-reference definitions, report gaps | `/secret-audit` | project |
| devbox-checkpoint | Save/restore environment state snapshots | `/checkpoint` | project |
| repair-status | Report auto-repair system health, circuit breaker states, registry stats | `/repair-status` | project |
| conversation-memory | Search past sessions, surface patterns, self-referential learning | `/conversation-memory` | project |
| repo-scout | Scout external git repos for tech radar classification (bulk mode, markdown artifacts, adoption signals) | `/repo-scout` | both |
| radar-update | Merge /repo-scout evaluations into ecosystem-tools.md and blocked-tools.md, preserving human-authored prose. Dry-run by default, --apply writes | `/radar-update` | os-dev |
| eval-repo | [DEPRECATED] Renamed to /repo-scout (2026-04-24) | `/eval-repo` | both |
| batch-runner | Execute multiple SDD changes sequentially with timing, reporting, and failure handling | `/batch-run` | project |
| contract-drift | Detect drift between HTTP calls in source code and OpenAPI/Swagger contract definitions | `/contract-drift` | project |
| document-feature | Generate or update structured feature documentation using 3-layer detection | `/document-feature` | project |
| gpu-sandbox | Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data, financial) | `/gpu-sandbox` | project |
| issue-pipeline | Fetch a GitHub issue, run the SDD pipeline, and open a pull request | `/issue-to-pr` | project |
| memu-context | Query memU proactive memory for relevant context before starting work | _auto_ | project |
| resolve-blockers | Automatically resolve blockers reported by readiness-check | `/resolve-blockers` | project |
| sandbox-sample | Classify, sample, sandbox-verify, then scale changes across large file sets | `/sandbox-sample` | project |
| singularity | Autonomous MAPE-K control loop: monitor, classify, and route codebase events | `/singularity` | project |
| webhook-trigger | GitHub webhook server that receives issue events and launches SDD pipelines | `/webhook-trigger` | project |
| auto-rollback | Automatically revert commits from a failed sdd-apply when verify exhausts all retries | `/auto-rollback` | project |
| cognee-search | Semantic knowledge graph search via Cognee — relationship-aware retrieval | `/cognee-search` | project |
| impact-analysis | Analyze the blast radius of changed files: importers, coverage, services, risk | `/impact-analysis` | project |
| jupyter-execute | Execute code in a Jupyter kernel sandbox for data analysis and benchmarks | `/jupyter-exec` | project |
| semgrep-scan | Run Semgrep SAST security scanning, report in adversarial review format | `/semgrep-scan` | project |
| confidence-check | Pre-implementation confidence assessment: 5-dimension readiness check before coding | `/confidence-check` | project |
| code-review | Engram-integrated code review: quality, security, conventions, test coverage with memory | `/code-review` | project |
| pr-review | Pull Request review: diff-based review with test verification and PASSED/FAILED verdict | `/pr-review` | project |
| self-review | Lightweight 4-question post-implementation checklist for non-SDD work | `/self-review` | project |
| web-crawler | Fetch and convert web pages to LLM-ready markdown using Crawl4AI | `/web-crawler` | project |
| deep-research | Multi-hop research with configurable depth (quick/standard/deep/exhaustive), structured reports | `/deep-research` | project |
| deep-tool-research | Canonical 7-annex deep evaluation of an external tool (A–G fixed taxonomy) after repo-scout pass; produces parent comparison doc + annexes for cross-tool comparability | `/deep-tool-research <tool>` | both |
| research-protocol | Meta-skill: systematic investigation methodology (DISCOVER/ANALYZE/COMPARE/SYNTHESIZE) | `/research-protocol` | project |
| audit-website | 6-category website audit (SEO, Performance, Security, Content/UX, Accessibility, Schema.org) | `/audit-website` | project |
| persistent-agent | Create persistent agents with state across sessions: identity profile, event log | `/create-persistent-agent` | project |
| planning-poker | Multi-agent Planning Poker: 3 independent complexity estimates, divergence detection | `/planning-poker` | project |
| cost-predictor | Predict task cost from historical metrics, routing defaults, and measured model prices | `/cost-predict` | project |
| run-tests | Auto-detect project test framework and run tests with structured pass/fail reporting | `/run-tests` | project |
| install-recommended | Detect project stack and recommend relevant skills to install | `/install-recommended` | project |
| repo-forensics | Deep forensic analysis of git repos: clone, scan all code, deps, architecture, tools, features, COS comparison | `/repo-forensics` | both |
| reverse-engineer | Deep source code analysis of dependencies: extract config schemas, env vars, CLI commands, API routes, Docker setup, auth flows | `/reverse-engineer` | both |
| red-team | Red team testing for agent prompts: detects injection, jailbreak, and manipulation vulnerabilities via Promptfoo | `/red-team` | os-dev |
| vulnerability-scan | Run LLM vulnerability probes using Garak against configured endpoints | `/vulnerability-scan` | os-dev |
| agent-stress-test | Stress-test agent cognitive health to detect context-induced degradation | `/agent-stress-test` | os-dev |
| audit-integrity | Verify integrity of skills, hooks, libs, and config against the OS manifest | `/audit-integrity` | os-dev |

## Pre-Development & Audit Skills [project-discovery / project-audit]

> Located at `.cognitive-os/skills/`. Installed via the project-discovery and project-audit packages.

| Skill | Description | Invoke | Audience |
|-------|-------------|--------|----------|
| context-analysis | Analyze project business context, stakeholders, constraints | `/context-analysis` | project |
| threat-model | STRIDE-based threat identification and severity scoring | `/threat-model` | project |
| competitive-research | Benchmarking, library evaluation, competitive analysis | `/competitive-research` | project |
| execution-plan | Phased execution plan with budget estimation | `/execution-plan` | project |
| audience-summaries | Audience-targeted summaries from pre-dev artifacts | `/audience-summaries` | project |
| audit-report | Comprehensive audit report for sprint or date range | `/audit-report` | project |
| traceability-check | Requirement-to-test traceability gap detection | `/traceability-check` | project |

## Communication Skills — Caveman [plugin]

> Ported from `.claude/plugins/caveman/`. License: MIT. See `rules/os-vs-project.md`.
> Caveman-compress scripts live at `.claude/plugins/caveman/caveman-compress/scripts/`.

| Skill | Description | Invoke | Audience |
|-------|-------------|--------|----------|
| caveman | Ultra-compressed communication mode (~75% token reduction). Intensity levels: lite/full/ultra | `/caveman [lite\|full\|ultra]` | both |
| caveman-es | Modo cavernícola en español. Misma compresión, soporte nativo español | `/caveman-es [lite\|full\|ultra]` | both |
| caveman-compress | Compress natural language memory files (CLAUDE.md, todos) into caveman format | `/caveman:compress <filepath>` | both |

## External Skills — Trail of Bits [submodule]

> Installed via `bash scripts/install-tob-skills.sh` at `.claude/plugins/trailofbits-skills/`.
> License: CC-BY-SA-4.0. Skills are used unmodified. See `rules/trailofbits-skills.md`.
> Prerequisite: submodule must be initialised (`git submodule update --init`).

| Skill | Description | Invoke | Audience |
|-------|-------------|--------|----------|
| tob-static-analysis | Static code analysis for vulnerabilities and bug patterns (Trail of Bits) | `tob-static-analysis` | os-dev |
| tob-variant-analysis | Trace a bug pattern across the codebase to find similar vulnerabilities (Trail of Bits) | `tob-variant-analysis` | os-dev |
| tob-insecure-defaults | Detect fail-open / insecure default configurations (Trail of Bits) | `tob-insecure-defaults` | os-dev |
| tob-supply-chain-risk-auditor | Assess dependency supply-chain risks: typosquatting, malicious packages (Trail of Bits) | `tob-supply-chain-risk-auditor` | os-dev |
| tob-agentic-actions-auditor | Audit GitHub Actions workflows for injection and TOCTOU vulnerabilities (Trail of Bits) | `tob-agentic-actions-auditor` | os-dev |

## Project Skills [generated]

These skills are project-specific and live in `{project}/.claude/skills/`. They are generated by `/cognitive-os-init` based on detected stack. Examples:

| Skill | Description | Generated For |
|-------|-------------|---------------|
| framework-patterns | Framework-specific patterns (per `cognitive-os.yaml -> project.architecture.frameworks`) | All projects |
| start-stack | Start the full local stack | Multi-service projects |
| check-health | Health check with project endpoints | All projects |
| add-mock-provider | Add mock for external provider | Projects with external APIs |
| sre-agent-config | SRE overlay with project container map | All projects |

## Loading Protocol

1. **Level 1** (always): This catalog (~2K tokens)
2. **Level 2** (on demand): Full SKILL.md when skill is invoked or triggered (~1-3K tokens each)
3. **Level 3** (rare): references/ files for detailed examples (~2-5K tokens each)
4. **Max active**: 5 skills simultaneously. Unload after 5 min inactivity.
- **__contracts__** — Structural namespace for shared Cognitive OS skill contracts used by other agentic primitives.
- **add-hook** — Step-by-step guide for adding a new hook to the Cognitive OS
- **add-mcp** — Step-by-step guide for integrating a new MCP server into the Cognitive OS
- **add-rule** — Step-by-step guide for adding a new rule to the Cognitive OS
- **add-skill** — Step-by-step guide for adding a new skill to the Cognitive OS
- **adr-tombstone** — Create or repair neutral tombstones for removed ADR numbers; use when an ADR is deleted, purged, superseded without replacement text, or ADR numbering has gaps that must stay auditable without reus...
- **agent-dashboard** — Show real-time status of all running background agents
- **agent-kpis** — Calculate and report Cognitive OS KPIs and OKRs. Shows agent health, efficiency, quality metrics. Use periodically or when evaluating agent performance.
- **agent-stress-test** — Stress-test agent cognitive health to detect context-induced degradation
- **analyze-improvements** — Analyze KPIs, error patterns, and skill metrics to identify improvement opportunities. Produces a ranked list of proposed changes with AUTO vs HUMAN-APPROVAL classification. Output only — makes NO ...
- **apply-improvements** — Apply approved self-improvement changes from an analyze-improvements report. Applies AUTO changes immediately; presents HUMAN-APPROVAL changes for explicit confirmation before touching files.
- **arena** — Run competitive benchmarks comparing Cognitive OS against other AI coding tools
- **audit-integrity** — Symlink-aware integrity audit of hooks, libs, and skills. Resolves symlinks before classifying, preventing false ghost reports.
- **audit-website** — Perform a comprehensive 6-category website audit (SEO, Performance, Security, Content/UX, Accessibility, Schema.org) with scored checkpoints and a structured markdown report. Each item is PASS/FAIL...
- **auto-refine** — Analyze a failed agent's output, determine root cause, and re-launch with refined instructions. Implements the PITER Refine step.
- **auto-rollback** — Prepare a human-approved rollback plan when SDD verify-apply exceeds max retries
- **automaker-bridge** — Configure AutoMaker to use Cognitive OS as its execution brain
- **batch-runner** — Execute multiple SDD changes sequentially with timing, reporting, and failure handling
- **branch-worktree-closure** — Use when an agent finds leftover codex/* or claude/* branches, extra git worktrees, or open feature worktrees and must decide whether to merge, preserve, or remove them safely.
- **bump-version** — Calculate and write the new version to the VERSION file
- **capability-snapshot** — Snapshot, diff, and restore Cognitive OS capabilities to prevent feature loss during refactors
- **catalog-full** — Load and display the full skills catalog (skills/CATALOG.md) with invocations, sections, and audience columns. Use when the compact Level-1 catalog does not have enough detail.
- **caveman** — Ultra-compressed communication mode. Cuts token usage ~75% by speaking like caveman while keeping full technical accuracy. Supports intensity levels: lite, full (default), ultra. Use when user says...
- **caveman-es** — Modo cavernícola en español. Corta ~75% de tokens hablando como cavernícola técnico. Misma precisión técnica, menos palabrería. Niveles: lite, full (default), ultra. Usar cuando el usuario diga "mo...
- **code-review** — Engram-integrated code review with adversarial protocol. Reviews changed files for quality, security, conventions, and test coverage. Uses engram memory for past review patterns and saves findings ...
- **cognee-integration** — Configure and use Cognee for knowledge graph memory. Provides structured knowledge extraction, graph-based retrieval, and MCP server integration.
- **cognee-search** — Semantic knowledge graph search via Cognee — complements Engram FTS5 with relationship-aware retrieval
- **cognitive-os-benchmark** — Run benchmark comparisons between Cognitive OS and BMAD METHOD v6
- **cognitive-os-init** — META skill — initialize Cognitive OS for a project by chaining detect-stack → generate-config → scaffold-project.
- **cognitive-os-status** — Full health check of all Cognitive OS agentic primitives
- **cognitive-os-test** — Run the Cognitive OS test suite with persisted summary (junit + failures + tails). SO-only; not for adopting projects.
- **compat-test** — Smoke test suite verifying Cognitive OS works correctly with the current AI model. Checks skill triggers, rule compliance, phase awareness, memory, progressive loading, templates, budget awareness,...
- **component-reality-check** — Measure declared-but-unwired vs real agentic primitives of the SO using the audit classifier script. Reports REAL / DORMANT / UNWIRED / METADATA counts + worst offenders + trend. SO-only.
- **compose-prompt** — Compose a sub-agent prompt from reusable templates. Use when launching sub-agents to ensure consistent instructions.
- **compress** — Compress natural language memory files (CLAUDE.md, todos, preferences) into caveman format to save input tokens. Preserves all technical substance, code, URLs, and structure. Compressed version ove...
- **confidence-check** — Pre-implementation confidence assessment. Before writing code, check 5 dimensions to verify readiness: no duplicates, architecture compliance, documentation verified, prior art reviewed, and root c...
- **contract-drift** — Detect drift between HTTP calls in source code and OpenAPI/Swagger contract definitions. Scans for fetch, axios, http.*, requests, and httpx patterns, compares against the contract spec, and produc...
- **conversation-memory** — Search and learn from past Cognitive OS sessions — the system's long-term memory
- **coordination-status** — Inspect active multi-session edit locks and decide how to respond when a target file is held by another agent. Read-only introspection for sub-agents.
- **cos-status** — Display current Cognitive OS state — active profile, skills exposed, hooks wired, rules loaded, packages installed, and health checks. Use when a user asks about OS state, installation verification...
- **cost-predict** — Predict task cost from Cognitive OS history, phase routing, and measured model prices.
- **coverage-enforcement** — Run Go test coverage for all services, enforce thresholds from cognitive-os.yaml, report per-package results. Service root read from project.architecture.services_root.go config.
- **decision-triage** — Surface all pending operator decisions across research reports and ADRs. Companion to /session-backlog — counts decisions instead of tasks. Read-only inventory.
- **deep-research** — Multi-hop research skill for deep investigation of topics. Executes structured research with configurable depth levels (quick/standard/deep/exhaustive), multi-hop reasoning chains, confidence self-...
- **deepeval-integration** — Configure and use DeepEval for LLM unit testing, agent trajectory evaluation, and skill/hook quality assurance. Pytest-native with 60+ metrics.
- **deps-update** — Audit and upgrade Cognitive OS dependencies (engram, brew packages, Python deps, Docker images, Claude plugins) using the canonical scripts/deps-update.sh primitive
- **detect-patterns** — Detect systemic problems in the Cognitive OS codebase: dead metadata, broken chains, phantom entries, and structural tests.
- **detect-stack** — Scan a project root and produce detected-stack.json with detected languages, frameworks, databases, auth, cache, messaging, and services.
- **devbox-checkpoint** — Save and restore environment state snapshots using devbox
- **doc-review-personas** — Multi-persona adversarial review of a documentation corpus. Runs N Haiku sub-agents in parallel — each one reading the same docs with a different human-role lens (CFO, Tech Lead, Commercial, New De...
- **doc-sync** — Synchronize documentation that became stale after code changes
- **docs-execution-audit** — Classify documentation items as done, weak-proof, planned, proposed, stale, or unknown using repository evidence.
- **document-feature** — Generate or update structured feature documentation using 3-layer detection (SDD spec, git diff, CLI arg). Extension (v1.1, ADR-054 Phase 2): accepts --project-dir to append to docs/05-features/fea...
- **dod-check** — Verify Definition of Done criteria for a task at a given complexity level
- **dogfood-score** — Measure the SO's self-build maturity as a composite 0-100 score across test health, skill coverage, hook wiring, ADR discipline, harness portability, commit activity, and doc freshness. Analog to r...
- **domain-model** — Scaffold a DDD domain-model.md template under docs/03-dominio-riesgo/ (ADR-054 10-category convention). Emits bounded-contexts + entities + ubiquitous-language tables with TODO markers. Idempotent.
- **error-analyzer** — Analyze accumulated errors from test/lint/build runs and propose skill improvements. Use when error patterns repeat.
- **eval-repo** — DEPRECATED — renamed to /repo-scout (2026-04-24). This stub preserves backward compatibility for any documentation or workflows referencing /eval-repo. New work should use /repo-scout.
- **evaluate-plan** — Evaluate any existing plan file with a 0-50 scoring system. Proposes improvements if score is low.
- **exhaustive-prompt** — Generate exhaustive agent prompts with scope enumeration and acceptance criteria
- **experimental** — Structural namespace for experimental Cognitive OS skills that are not promoted to stable catalog surfaces yet.
- **generate-changelog** — Move [Unreleased] CHANGELOG entries into a versioned release section
- **generate-config** — Read detected-stack.json and generate or update cognitive-os.yaml with detected infrastructure, quality gates, and stack-specific settings.
- **gpu-sandbox** — Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data processing, financial calculations)
- **harness-audit** — Evaluate harness agentic primitives (hooks, rules, skills) for continued relevance. Identify candidates for simplification or retirement as models improve.
- **hook-timing** — Report hook execution timing statistics (p50/p95/p99) from the COS hook-timing wrapper. Supports live tail, event filtering, and session scoping.
- **impact-analysis** — Analyze change impact: imports, tests, configs, services, and SDD artifacts affected
- **install-recommended** — Detect project stack and recommend relevant skills to install
- **invariant-check** — Scans a target file pair (ADR + lib, or similar) for numeric-constant pairs, proposes invariants between them, and writes pytest assertions that enforce the relationship. Trigger when a review find...
- **issue-pipeline** — Fetch a GitHub issue, run the SDD pipeline, and open a pull request
- **jupyter-execute** — Execute code in a Jupyter kernel sandbox for data analysis, Python snippets, and benchmarks
- **llm-status** — Inspect LLM dispatch state for the current Cognitive OS install — which providers are configured (with tier and model_map), kill-switches active, cascade config from cognitive-os.yaml, active envir...
- **memory-scan** — Scan text content (or a file) for prompt injection, credential exfiltration, and invisible Unicode threats before persisting to memory.
- **memu-context** — Query memU proactive memory for relevant context before starting work
- **metrics-calibrator** — Analyze KPI history and auto-calibrate thresholds for meaningful alerting
- **model-optimizer** — Analyze skill execution metrics and recommend optimal model routing
- **nemo-guardrails** — Generate and configure NeMo Guardrails Colang 2.0 rules from Cognitive OS rules. Maps the safety mesh (clarification-gate, assumption-tracker, confidence-gate, credential-management) to NeMo input/...
- **ops-runbook** — Scaffold operations.md + admin-processes.md + monitoring.md under docs/06-backoffice/ (deploy/rollback/on-call/SLOs/alerting). Idempotent.
- **optimize-skill** — Optimizar un skill de Claude Code iterativamente usando evals, midiendo mejoras y refinando el prompt
- **pattern-audit** — Pattern/regex audit of a codebase with MANDATORY sample verification before publishing counts as severity. Prevents alarmist "N occurrences = problem" conclusions based on unverified regex hits.
- **peer-card** — Local user-memory peer card (read/edit/forget/explain) backed by Engram FTS5. ADR-077 Phase 1.
- **pentest-self** — Self-penetration testing for Cognitive OS safety mesh. Validates that prompt injection defenses, permission boundaries, secret protections, rate limiting, scope controls, and data integrity guards ...
- **persistent-agent** — Create persistent agents that maintain their own state across sessions. Generates a skill directory with identity profile, event log, and auto-fixation checklist for continuous learning.
- **phoenix-trace-ui** — Start the Arize Phoenix LLM-native trace UI locally (pip-based, no Docker)
- **plan-bug** — Create a bug fix plan with root cause analysis and evaluation scoring. Use before fixing any non-trivial bug.
- **plan-feature** — Create a feature implementation plan with evaluation scoring. Use before implementing any significant feature.
- **planning-poker** — Multi-agent complexity estimation using planning-poker rounds — triangulate task effort, surface disagreements, and calibrate estimates against actual outcomes.
- **pr-review** — Pull Request review skill. Gets PR diff against base branch, runs code review with engram context, checks tests/coverage/lint, and produces structured PR review output with file-level comments and ...
- **preserved-wip-cleanup** — Archive-first cleanup for preserved WIP stashes, temporary validation capsule worktrees, and zombie session registry entries after all agents stop.
- **primitive-classifier** — Classify a new agentic primitive (skill, hook, rule, lib) as CORE or PACKAGE. Use when adding new functionality to determine if it belongs in the OS kernel or should be a cos package.
- **primitive-harvester** — Classify whether a conversation should become a reusable agentic primitive, improve an existing primitive, use an existing primitive, become documentation only, or be discarded.
- **primitive-authoring** — Governed workflow for creating, modifying, or promoting agentic primitives with reuse, ownership, portable contract, projection fidelity, runtime evidence, and consumer-impact checks.
- **primitive-surface-reduction** — Plan or apply conservative surface reduction for Cognitive OS agentic primitives; OS source repo only, plan by default.
- **primitive-usage-map** — Map which Cognitive OS skills, hooks, rules, tests, docs, workflows, and configs reference each primitive or script.
- **private-mode** — Toggle private conversation mode. When active, nothing is saved to Engram, metrics, error logs, or git. Use for personal conversations, sensitive topics, or casual chat. Activate with /private, dea...
- **project-scaffold** — Scaffold the 10-category docs/ tree adopted by Cognitive OS projects. Creates 01-contexto through 10-resumenes with starter files and TODO markers. Idempotent. See ADR-054.
- **promptfoo-integration** — Configure Promptfoo for prompt regression testing and red teaming of skills in CI/CD pipelines.
- **proof-drill** — Select and run opt-in proof drills and smoke checks for COS self-build and consumer-project validation without polluting default test lanes.
- **push-release** — Push the release commit and tags to the remote — always requires explicit confirmation
- **queue-drain** — Periodic agent queue drain and health check
- **radar-update** — Tech radar curation pipeline. Evaluates one or more GitHub repos via /repo-scout, then merges the results into the canonical radar docs (ecosystem-tools.md, blocked-tools.md) while preserving all h...
- **ragas-integration** — Configure and use RAGAS for memory quality testing, retrieval evaluation, and synthetic test generation for agent scenarios.
- **readiness-check** — Implementation readiness gate — validates all prerequisites before coding starts
- **recall-search** — Search past Claude Code conversations using full-text search. Use when Engram mem_search doesn't find what you're looking for -- recall searches raw conversation transcripts.
- **recommend-library** — Search package registries and rank by relevance, adoption, maintenance, and license compliance
- **red-team** — Red team testing for agent prompts — detects injection, jailbreak, and manipulation vulnerabilities
- **redteam-harness** — Run red-team scenarios against the agent OS to detect false-done, partial-completion, and unwired-constant failure modes per ADR-105/ADR-106.
- **release-os** — META — orchestrate the full Cognitive OS release by chaining the 5 atomic release skills
- **repair-skill** — Drain the skill repair queue and propose regeneration or deprecation for degraded skills
- **repair-status** — Report on auto-repair system health and statistics
- **repo-forensics** — Deep forensic analysis of git repositories. Clones, analyzes ALL code, dependencies, architecture patterns, tools, features, API endpoints, and produces exhaustive structured reports. Optionally co...
- **repo-scout** — Scout external git repositories for potential inclusion in the tech radar. Three-level assessment: DeepWiki summary, shallow clone analysis, deep evaluation. Supports bulk mode (--batch <file>) for...
- **research-protocol** — Meta-skill that teaches agents HOW to investigate any source material systematically. Covers reading protocols per file type, comparison frameworks, quality assessment rubrics, and structured verdi...
- **resolve-blockers** — Automatically resolve blockers reported by readiness-check. Maps each blocker type to a resolution sub-agent, re-runs readiness-check after fixes, and escalates to human after 2 failed attempts.
- **resource-governor** — Master resource optimizer — coordinates budget, infrastructure, agents, skills, and tokens system-wide
- **resume-tasks** — Check for incomplete tasks from previous sessions and offer to resume them. Use when starting a new session or after a crash.
- **retrospective** — Weekly analysis of all squads with trend analysis and auto-reconfiguration proposals
- **reverse-engineer** — Deep source code analysis of a dependency to understand its internal APIs, config schemas, CLI commands, environment variables, and undocumented behavior. When docs are incomplete, reading source c...
- **review-output** — Manually trigger review of a specific past sub-agent output or the most recent N outputs. Bypasses sample-rate gate but respects the daily budget cap. Produces review findings in Engram and .cognit...
- **risk-register** — Scaffold STRIDE-based risk-register.md under docs/03-dominio-riesgo/ with impact/likelihood matrix and 6 seed rows (one per STRIDE category). Idempotent.
- **rules-export** — Export a snapshot of Cognitive OS rules/ (so-slo, definition-of-done, credential-management, etc.) into an adopting project's docs/08-estandares/ directory. Follows the 10-category convention (ADR-...
- **run-tests** — Auto-detect project test framework and run tests with structured reporting
- **sandbox-sample** — Classify, sample, sandbox-verify, then scale changes across large file sets
- **scaffold-project** — Create the .claude/ directory structure, symlink rules, and generate project-specific rules, skills, and hooks using detected-stack.json.
- **scout** — Quick pre-implementation codebase reconnaissance with 3 depth levels
- **sdd-compound** — Extract learnings and compound knowledge after completing an SDD change. Run after sdd-archive to crystallize patterns, update skill routing, and improve future iterations.
- **sdd-continue** — Enhanced SDD continuation with state inspection — determines optimal next action
- **sdd-explore** — Explore and investigate ideas before committing to a change — deep feasibility analysis
- **sdd-resume** — Resume an SDD pipeline from its last completed phase with timing and state visibility
- **secret-audit** — Scan all services for env var usage, cross-reference with definitions, report gaps
- **security-audit** — Comprehensive security audit of Cognitive OS configuration, secrets, hooks, permissions, and infrastructure. Reports findings with severity levels.
- **security-red-team** — Unified red-team primitive for Cognitive OS: inventories attack surface, models threats, runs deterministic abuse probes, scores security controls per primitive, and emits a mitigation backlog.
- **self-improve** — META skill — orchestrates analyze-improvements → (human reviews) → apply-improvements. The closing piece of the self-improvement loop.
- **self-review** — Lightweight 4-question post-implementation checklist for non-SDD work. Quick self-assessment before claiming a task is done.
- **semgrep-scan** — Run Semgrep SAST security scanning on a path or changed files. Reports findings in adversarial review format (BLOCKER/CONCERN/SUGGESTION).
- **session-backlog** — Inventory all pending work across plans, engram, tasks, todos, audits, and git. Classify by priority and produce a structured backlog document for future sessions.
- **session-manager** — Manage concurrent Cognitive OS sessions — list, inspect, and clean up
- **session-report-executive** — Generate an executive-level session report translating technical metrics into business language. For non-technical leaders who need to know what the Cognitive OS did during a session.
- **session-wrapup** — End-of-session routine — run session-backlog inventory, save to engram, write session summary, and report what was accomplished and what comes next.
- **simulation-arena** — Run scripted end-to-end agent workflow simulations to validate safety mesh, measure OS evolution (cost/speed/quality), and regression-test after hook/rule/skill changes.
- **singularity** — Codebase Singularity — autonomous MAPE-K control loop that monitors, classifies, and routes codebase events to the right pipeline
- **skill-creator** — Creates new AI agent skills following the Agent Skills spec, then generates cos package scaffolding for sharing.
- **smoke-test** — Run end-to-end smoke tests that validate the real Cognitive OS system works
- **so-vs-vanilla** — A/B benchmark harness that measures Cognitive OS governance value by running the same task under full governance AND with all governance disabled (COS_DISABLE_ALL_GOVERNANCE=1). Produces per-task v...
- **sprint** — Lightweight agent-managed sprint tracking — plan, status, retro, course-correct
- **squad-manager** — Evaluate squad performance and propose reconfigurations
- **sre-agent** — SRE auto-repair agent. Monitors all project services, detects errors in logs, searches Engram for known fixes, and auto-repairs or proposes fixes. Invoke with /sre-agent or let it run autonomously ...
- **strands-evals-integration** — Configure Strands Evals for trace-based agent trajectory evaluation using OpenTelemetry instrumentation.
- **synthesize-skill** — Review the skill synthesis queue, list proposed drafts, and accept/reject/defer promotion candidates
- **systematic-debugging** — Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- **tag-release** — Create the release commit (VERSION + CHANGELOG) and annotated git tag
- **test-contract-repair** — Repair failing or misleading tests without greenwashing. Classify the contract, confirm history, fix runtime when needed, and strengthen structural checks into behavioral proof.
- **test-driven-development** — Use when implementing any feature or bugfix, before writing implementation code
- **tool-discovery** — Discover new open-source tools that could enhance Cognitive OS capabilities
- **trust-audit** — Analyze trust scores across agents and tasks, identify patterns, recommend reviews
- **validate-config** — Validate all Cognitive OS configuration files — agents, squads, skills, rules, hooks
- **validate-release** — Pre-release readiness check — validates working tree, branch, changelog, and VERSION file
- **verification-before-completion** — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims
- **vuln-remediation-flow** — Lab-stage propose-only cloud flow contract for sandboxed vulnerability remediation.
- **vulnerability-scan** — Run LLM vulnerability probes using Garak against configured endpoints
- **web-crawler** — Fetch and convert web pages to LLM-ready markdown using Crawl4AI. Supports single-page fetch, structured data extraction, and multi-page site crawling.
- **webhook-trigger** — GitHub webhook server that receives issue events and launches SDD pipelines automatically via ClaudeExecutor.
- **worktree-triage** — Triage a linked Git worktree against a target branch, port only unapplied work, validate, and remove the worktree only when clean and safe.
- **agent-control** — Send governed bidirectional control and clarification signals between the orchestrator and live agents.
- **primitive-harness-coverage** — Measure effective agentic primitive implementation by surface so agents do not confuse `SCOPE: both` with equal Claude/Codex/CLI/UI behavior.
