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
| os-session-wrapup | SO-only session close addendum that runs component-reality-check when primitive surfaces changed | `/os-session-wrapup` | os-dev |
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
| graphify-query | Query/build Graphify repository knowledge graphs for maintainer context selection without installing hooks or persistent IDE instructions | `/graphify-query` | os-dev |
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
| browser-task | Drive a real browser for navigation, extraction, and form-fill workflows when static HTTP fetches are insufficient | `/browser-task` | both |
| wiki-ingest | Ingest raw URLs, files, or pasted text into the compiled docs vault with raw-source indexing | `/wiki-ingest` | both |
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
- **__contracts__** — Use when you need this Cognitive OS skill: Structural namespace for
- **add-hook** — Use when you need this Cognitive OS skill: Step-by-step guide for adding
- **add-mcp** — Use when you need this Cognitive OS skill: Step-by-step guide for integrating
- **add-rule** — Use when you need this Cognitive OS skill: Step-by-step guide for adding
- **add-skill** — Use when you need this Cognitive OS skill: Step-by-step guide for adding
- **adr-tombstone** — Use when you need this Cognitive OS skill: Create or repair neutral
- **agent-control** — Use when you need this Cognitive OS skill: Send governed bidirectional
- **agent-dashboard** — Use when you need this Cognitive OS skill: Show real-time status of
- **agent-kpis** — Calculate and report Cognitive OS KPIs and OKRs. Shows agent health,
- **agent-stress-test** — Use when you need this Cognitive OS skill: Stress-test agent cognitive
- **analyze-improvements** — Use when you need this Cognitive OS skill: Analyze KPIs, error patterns,
- **apply-improvements** — Use when you need this Cognitive OS skill: Apply approved self-improvement
- **architecture-map-answer** — Use when you need a commercial-safe Cognitive OS architecture map from
- **arena** — Run competitive benchmarks comparing Cognitive OS against other AI coding
- **audit-integrity** — Use when you need this Cognitive OS skill: Symlink-aware integrity audit
- **audit-website** — Perform a comprehensive 6-category website audit (SEO, Performance,
- **auto-refine** — Analyze a failed agent's output, determine root cause, and re-launch
- **auto-rollback** — Prepare a human-approved rollback plan when SDD verify-apply exceeds
- **automaker-bridge** — Configure AutoMaker to use Cognitive OS as its execution brain
- **batch-runner** — Execute multiple SDD changes sequentially with timing, reporting, and
- **branch-worktree-closure** — Use when an agent finds leftover codex/* or claude/* branches, extra
- **browser-task** — Use when an agent or operator needs to drive a real web browser - navigate
- **bump-version** — Use when you need this Cognitive OS skill: Calculate and write the new
- **capability-snapshot** — Snapshot, diff, and restore Cognitive OS capabilities to prevent feature
- **catalog-full** — Use when the compact Level-1 catalog does not have enough detail. Purpose:
- **caveman** — Use when user says "caveman mode", "talk like caveman", "use caveman",
- **code-review** — Use when you need this Cognitive OS skill: Engram-integrated code review
- **cognee-integration** — Configure and use Cognee for knowledge graph memory. Provides structured
- **cognee-search** — Semantic knowledge graph search via Cognee — complements Engram FTS5
- **cognitive-os-benchmark** — Run benchmark comparisons between Cognitive OS and BMAD METHOD v6
- **cognitive-os-init** — Use when you need this Cognitive OS skill: META skill — initialize Cognitive
- **cognitive-os-status** — Use when you need this Cognitive OS skill: Full health check of all
- **cognitive-os-test** — Use when you need this Cognitive OS skill: Run the Cognitive OS test
- **compat-test** — Use when you need this Cognitive OS skill: Smoke test suite verifying
- **component-reality-check** — Use when you need this Cognitive OS skill: Measure declared-but-unwired
- **compose-prompt** — Compose a sub-agent prompt from reusable templates. Use when launching
- **compress** — Use when you need this Cognitive OS skill: Compress natural language
- **confidence-check** — Pre-implementation confidence assessment. Before writing code, check
- **contract-drift** — Detect drift between HTTP calls in source code and OpenAPI/Swagger contract
- **conversation-memory** — Search and learn from past Cognitive OS sessions — the system's long-term
- **coordination-status** — Use when you need this Cognitive OS skill: Inspect active multi-session
- **cos-install-operations** — Use when installing, bootstrapping, upgrading, uninstalling, onboarding,
- **cos-maintainer-operations** — Use when maintaining Cognitive OS capability/audit/control-plane scripts
- **cos-status** — Use when a user asks about OS state, installation verification, or troubleshooting.
- **cost-predict** — Use when you need this Cognitive OS skill: Predict task cost from Cognitive
- **coverage-enforcement** — Run Go test coverage for all services, enforce thresholds from cognitive-os.yaml,
- **decision-triage** — Use when you need this Cognitive OS skill: Surface all pending operator
- **deep-research** — Multi-hop research skill for deep investigation of topics. Executes
- **deep-tool-research** — Use when an external tool has passed the shallow `repo-scout` gate and
- **deepeval-integration** — Configure and use DeepEval for LLM unit testing, agent trajectory evaluation,
- **deps-update** — Use when you need this Cognitive OS skill: Audit and upgrade Cognitive
- **detect-patterns** — Use when you need this Cognitive OS skill: Detect systemic problems
- **detect-stack** — Use when you need this Cognitive OS skill: Scan a project root and produce
- **devbox-checkpoint** — Save and restore environment state snapshots using devbox
- **doc-review-personas** — Use when you need this Cognitive OS skill: Multi-persona adversarial
- **doc-sync** — Synchronize documentation that became stale after code changes
- **docs-execution-audit** — Use when you need this Cognitive OS skill: Classify documentation items
- **document-feature** — Generate or update structured feature documentation using 3-layer detection
- **dod-check** — Run a deterministic Definition of Done check before claiming implementation, review, prompt-modernization, hook, skill, rule, or release-prep work is complete.
- **dogfood-score** — Use when you need this Cognitive OS skill: Measure the SO''s self-build
- **domain-model** — Use when you need this Cognitive OS skill: Scaffold a DDD domain-model.md
- **error-analyzer** — Analyze accumulated errors from test/lint/build runs and propose skill
- **eval-repo** — Use when you need this Cognitive OS skill: DEPRECATED — renamed to /repo-scout
- **evaluate-plan** — Evaluate any existing plan file with a 0-50 scoring system. Proposes
- **exhaustive-prompt** — Generate exhaustive agent prompts with scope enumeration and acceptance
- **experimental** — Use when you need this Cognitive OS skill: Structural namespace for
- **generate-changelog** — Use when you need this Cognitive OS skill: Move [Unreleased] CHANGELOG
- **generate-config** — Use when you need this Cognitive OS skill: Read detected-stack.json
- **gpu-sandbox** — Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data
- **graphify-query** — Use when a Cognitive OS maintainer asks to use Graphify, query or build a repository knowledge graph, inspect graph paths, explain graph nodes, run graph affected analysis, benchmark a Graphify gra...
- **harness-audit** — Evaluate harness agentic primitives (hooks, rules, skills) for continued
- **hook-timing** — Use when you need this Cognitive OS skill: Report hook execution timing
- **impact-analysis** — Analyze downstream blast radius: imports, tests, configs, services, and SDD artifacts affected
- **install-hook** — Use when you need this Cognitive OS skill: Install an extension hook
- **install-recommended** — Use when you need this Cognitive OS skill: Detect project stack and
- **install-skill** — Use when you need this Cognitive OS skill: Install an extension skill
- **invariant-check** — Use when you need this Cognitive OS skill: Scans a target file pair
- **issue-pipeline** — Fetch a GitHub issue, run the SDD pipeline, and open a pull request
- **jupyter-execute** — Execute code in a Jupyter kernel sandbox for data analysis, Python snippets,
- **llm-status** — Use when user asks about LLM provider state, rate-limit diagnosis, dispatch
- **memory-scan** — Use when you need this Cognitive OS skill: Scan text content (or a file)
- **memu-context** — Query memU proactive memory for relevant context before starting work
- **metrics-calibrator** — Analyze KPI history and auto-calibrate thresholds for meaningful alerting
- **model-optimizer** — Analyze skill execution metrics and recommend optimal model routing
- **nemo-guardrails** — Generate and configure NeMo Guardrails Colang 2.0 rules from Cognitive
- **ops-runbook** — Use when you need this Cognitive OS skill: Scaffold operations.md +
- **optimize-skill** — Iteratively optimize a Claude Code skill with evaluations, score measurement, and prompt refinement.
- **os-session-wrapup** — Use when closing or reviewing a Cognitive OS maintainer session after touching agentic primitives, projection settings, harness contracts, or release/public-readiness surfaces. Runs the generic ses...
- **patch-release** — Use when preparing, validating, publishing, or diagnosing a Cognitive OS patch release without running the full laptop lane.
- **pattern-audit** — Use when you need this Cognitive OS skill: Pattern/regex audit of a
- **peer-card** — Use when you need this Cognitive OS skill: Local user-memory peer card
- **pentest-self** — Self-penetration testing for Cognitive OS safety mesh. Validates that
- **persistent-agent** — Create persistent agents that maintain their own state across sessions.
- **phoenix-trace-ui** — Use when you need this Cognitive OS skill: Start the Arize Phoenix LLM-native
- **plan-bug** — Create a bug fix plan with root cause analysis and evaluation scoring.
- **plan-feature** — Create a feature implementation plan with evaluation scoring. Use before
- **planning-poker** — Multi-agent complexity estimation using planning-poker rounds — triangulate
- **pr-review** — Use when you need this Cognitive OS skill: Pull Request review skill.
- **preserved-wip-cleanup** — Use when you need this Cognitive OS skill: Archive-first cleanup for
- **primitive-authoring** — Use when building a new skill/rule/hook/script/workflow, converting
- **primitive-classifier** — Use when adding new functionality to determine if it belongs in the
- **primitive-harness-coverage** — Use when you need this Cognitive OS skill: Measure effective agentic
- **primitive-harvester** — Use when you need this Cognitive OS skill: Classify whether a conversation
- **primitive-surface-reduction** — Use when you need this Cognitive OS skill: Plan or apply conservative
- **primitive-usage-map** — Use when you need this Cognitive OS skill: Map which Cognitive OS skills,
- **private-mode** — Toggle private conversation mode. When active, nothing is saved to Engram,
- **product-answer** — Use when the user asks a Cognitive OS product/commercial question such
- **project-scaffold** — Use when you need this Cognitive OS skill: Scaffold the 10-category
- **promptfoo-integration** — Configure Promptfoo for prompt regression testing and red teaming of
- **proof-drill** — Use when you need this Cognitive OS skill: Select and run opt-in proof
- **push-release** — Use when you need this Cognitive OS skill: Push the release commit and
- **pyrefly-typecheck** — Use when Python files changed and you need fast advisory static type/API-shape checking with Pyrefly before finishing Cognitive OS work.
- **queue-drain** — Use when you need this Cognitive OS skill: Periodic agent queue drain
- **radar-update** — Use when you need this Cognitive OS skill: Tech radar curation pipeline.
- **ragas-integration** — Configure and use RAGAS for memory quality testing, retrieval evaluation,
- **readiness-check** — Implementation readiness gate — validates all prerequisites before coding
- **recall-search** — Search past Claude Code conversations using full-text search. Use when
- **recommend-library** — Search package registries and rank by relevance, adoption, maintenance,
- **red-team** — Use when you need this Cognitive OS skill: Red team testing for agent
- **redteam-harness** — Use when you need this Cognitive OS skill: Run red-team scenarios against
- **release-os** — Use when you need this Cognitive OS skill: META — orchestrate the full
- **repair-skill** — Use when you need this Cognitive OS skill: Drain the skill repair queue
- **repair-status** — Report on auto-repair system health and statistics
- **repo-forensics** — Use when you need this Cognitive OS skill: Deep forensic analysis of
- **repo-scout** — Scout external git repositories for potential inclusion in the tech
- **research-protocol** — Meta-skill that teaches agents HOW to investigate any source material
- **resolve-blockers** — Automatically resolve blockers reported by readiness-check. Maps each
- **resource-governor** — Use when you need this Cognitive OS skill: Master resource optimizer
- **resume-tasks** — Check for incomplete tasks from previous sessions and offer to resume
- **retrospective** — Weekly analysis of all squads with trend analysis and auto-reconfiguration
- **reverse-engineer** — Use when you need this Cognitive OS skill: Deep source code analysis
- **review-output** — Manually trigger review of a specific past sub-agent output or the most
- **risk-register** — Use when you need this Cognitive OS skill: Scaffold STRIDE-based risk-register.md
- **rules-export** — Use when you need this Cognitive OS skill: Export a snapshot of Cognitive
- **run-tests** — Use when you need this Cognitive OS skill: Auto-detect project test
- **sandbox-sample** — Classify, sample, sandbox-verify, then scale changes across large file
- **scaffold-project** — Use when you need this Cognitive OS skill: Create the .claude/ directory
- **scout** — Use when you need this Cognitive OS skill: Quick pre-implementation
- **sdd-apply** — Use when implementing SDD tasks against requirements and EAS acceptance rows.
- **sdd-compound** — Extract learnings and compound knowledge after completing an SDD change.
- **sdd-continue** — Use when you need this Cognitive OS skill: Enhanced SDD continuation
- **sdd-explore** — Use when you need this Cognitive OS skill: Explore and investigate ideas
- **sdd-resume** — Use when you need this Cognitive OS skill: Resume an SDD pipeline from
- **sdd-spec** — Use when creating or updating the SDD specification and emitting an Executable Acceptance Specification with EARS-style functional requirements when requested or risk warrants it.
- **sdd-tasks** — Use when converting SDD spec/design/EAS evidence into implementation tasks.
- **sdd-verify** — Use when verifying SDD implementation, including EAS coverage, detractor disposition, and executable evidence.
- **secret-audit** — Scan all services for env var usage, cross-reference with definitions,
- **security-audit** — Comprehensive security audit of Cognitive OS configuration, secrets,
- **security-red-team** — Use when you need this Cognitive OS skill: Unified red-team primitive
- **self-improve** — META skill — orchestrates analyze-improvements → (human reviews) → apply-improvements.
- **self-improvement-loop** — Use when running benchmark-bound Cognitive OS self-improvement loops with gated feedback and no automatic runtime mutation.
- **self-review** — Lightweight 4-question post-implementation checklist for non-SDD work.
- **semgrep-scan** — Run Semgrep SAST security scanning on a path or changed files. Reports
- **session-backlog** — Use when you need this Cognitive OS skill: Inventory all pending work
- **session-manager** — Use when you need this Cognitive OS skill: Manage concurrent Cognitive
- **session-pending-brief** — Use when starting a session OR when the operator asks 'what's pending?
- **session-pending-close** — Use when closing one or many pending-truth items with bilateral proof
- **session-report-executive** — Use when you need this Cognitive OS skill: Generate an executive-level
- **session-wrapup** — Use when you need this Cognitive OS skill: End-of-session routine —
- **simulation-arena** — Run scripted end-to-end agent workflow simulations to validate safety
- **singularity** — Codebase Singularity — autonomous MAPE-K control loop that monitors,
- **skill-creator** — Use when you need this Cognitive OS skill: Creates new AI agent skills
- **smoke-test** — Run end-to-end smoke tests that validate the real Cognitive OS system
- **so-vs-vanilla** — Use when you need this Cognitive OS skill: A/B benchmark harness that
- **sprint** — Lightweight agent-managed sprint tracking — plan, status, retro, course-correct
- **squad-manager** — Evaluate squad performance and propose reconfigurations
- **sre-agent** — SRE auto-repair agent. Monitors all project services, detects errors
- **stash-quarantine** — Use when safely isolating, inspecting, restoring, or discarding temporary Git stash quarantine entries without relying on positional refs.
- **strands-evals-integration** — Configure Strands Evals for trace-based agent trajectory evaluation
- **synthesize-skill** — Use when you need this Cognitive OS skill: Review the skill synthesis
- **systematic-debugging** — Use when encountering any bug, test failure, or unexpected behavior,
- **tag-release** — Use when you need this Cognitive OS skill: Create the release commit
- **test-contract-repair** — Use when you need this Cognitive OS skill: Repair failing or misleading
- **test-driven-development** — Use when implementing any feature or bugfix, before writing implementation
- **tool-discovery** — Discover new open-source tools that could enhance Cognitive OS capabilities
- **trust-audit** — Analyze trust scores across agents and tasks, identify patterns, recommend
- **validate-config** — Use when you need this Cognitive OS skill: Validate all Cognitive OS
- **validate-release** — Use when you need this Cognitive OS skill: Pre-release readiness check
- **verification-before-completion** — Use when about to claim work is complete, fixed, or passing, before committing
- **vuln-remediation-flow** — Use when you need this Cognitive OS skill: Lab-stage propose-only cloud
- **vulnerability-scan** — Use when you need this Cognitive OS skill: Run LLM vulnerability probes
- **web-crawler** — Fetch and convert web pages to LLM-ready markdown using Crawl4AI. Supports
- **webhook-trigger** — GitHub webhook server that receives issue events and launches SDD pipelines
- **wiki-ingest** — Use when raw URLs, files, or pasted text need to be ingested into the
- **worktree-triage** — Use when you need this Cognitive OS skill: Triage linked Git worktrees
