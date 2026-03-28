# Cognitive OS Skills Catalog

> Compact index loaded at session start. Full SKILL.md loaded on demand (Level 2).

## Universal Skills

| Skill | Description | Invoke | Tag |
|-------|-------------|--------|-----|
| cognitive-os-init | Initialize Cognitive OS for a project: detect stack, generate config and project-specific files | `/cognitive-os-init` | [universal] |
| model-optimizer | Analyze skill metrics, recommend optimal model routing | `/model-optimizer` | [universal] |
| error-analyzer | Analyze accumulated errors, propose skill improvements | `/error-analyzer` | [universal] |
| sre-agent | Monitor services, detect errors, auto-repair safe actions | `/sre-agent` | [universal] |
| squad-manager | Evaluate squad performance, propose reconfigurations | `/squad-report` | [universal] |
| systematic-debugging | 4-phase debugging: reproduce, isolate, hypothesize, verify. Use on bugs | _auto_ | [universal] |
| test-driven-development | RED-GREEN-REFACTOR cycle. Use when implementing features | _auto_ | [universal] |
| verification-before-completion | Evidence gate before claiming done. Run tests, check output | _auto_ | [universal] |
| coverage-enforcement | Run test coverage, enforce thresholds from cognitive-os.yaml | `/coverage-report` | [universal] |
| retrospective | Weekly cross-squad analysis with trend data and reconfig proposals | `/retrospective` | [universal] |
| resume-tasks | Check for incomplete tasks from previous sessions | `/resume-tasks` | [universal] |
| doc-sync | Detect and update stale documentation after code changes | `/doc-sync` | [universal] |
| private-mode | Toggle private conversation (no persistence, no metrics) | `/private` | [universal] |
| optimize-skill | Iteratively improve a skill using evals and feedback | `/optimize-skill` | [universal] |
| agent-kpis | Calculate and report Cognitive OS KPIs, OKRs, health dashboard | `/agent-kpis` | [universal] |
| auto-refine | PITER loop: analyze failed agent output, re-launch with refined instructions | `/auto-refine` | [universal] |
| compose-prompt | Compose reusable prompt fragments into complete prompts | `/compose-prompt` | [universal] |
| exhaustive-prompt | Generate exhaustive agent prompts with scope enumeration and acceptance criteria | `/exhaustive-prompt` | [universal] |
| evaluate-plan | Evaluate a plan before implementation, score 0-50 | `/evaluate-plan` | [universal] |
| plan-bug | Plan bug resolution with systematic approach | `/plan-bug` | [universal] |
| plan-feature | Plan feature implementation with phases | `/plan-feature` | [universal] |
| resource-governor | Budget enforcement, model downgrade chain, efficiency metrics | `/resource-governor` | [universal] |
| cognitive-os-status | Report Cognitive OS status: hooks, rules, skills, squads, metrics | `/cognitive-os-status` | [universal] |
| cognitive-os-benchmark | Run benchmark comparisons | `/benchmark` | [universal] |
| cognitive-os-test | Run the Cognitive OS automated test suite (infra, behavior, quality) | `/cognitive-os-test` | [universal] |
| compat-test | Smoke test: verify model compatibility with Cognitive OS (8 checks, < 30s) | `/cognitive-os-compat-test` | [universal] |
| readiness-check | Implementation readiness gate: validates prerequisites before coding | `/readiness-check` | [universal] |
| sdd-continue | Enhanced SDD continuation: state inspection, determines optimal next action | `/sdd-continue` | [universal] |
| sprint | Lightweight sprint tracking: plan, status, retro, course-correct | `/sprint` | [universal] |
| validate-config | Validate all Cognitive OS config files: agents, squads, skills, rules, hooks | `/validate-config` | [universal] |
| recommend-library | Search npm/PyPI/Go registries, rank by relevance, adoption, license compliance | `/recommend-library` | [universal] |
| dod-check | Verify Definition of Done criteria for a task at a given complexity level | `/dod-check` | [universal] |
| session-manager | Manage concurrent sessions: list active, show current, cleanup stale | `/sessions` | [universal] |
| self-improve | Self-improvement protocol: detect patterns, create/update skills/rules | `/self-improve` | [universal] |
| secret-audit | Scan all services for env var usage, cross-reference definitions, report gaps | `/secret-audit` | [universal] |
| capability-snapshot | Snapshot, diff, and restore Cognitive OS capabilities to prevent feature loss | `/capability-snapshot` | [universal] |
| devbox-checkpoint | Save/restore environment state snapshots | `/checkpoint` | [universal] |
| arena | Run competitive benchmarks against AI coding tools | `/arena` | [universal] |
| trust-audit | Analyze trust scores: overclaiming detection, trend analysis, review recommendations | `/trust-audit` | [universal] |
| repair-status | Report auto-repair system health, circuit breaker states, registry stats | `/repair-status` | [universal] |
| metrics-calibrator | Analyze KPI distributions, auto-adjust thresholds, propose derived metrics | `/metrics-calibrator` | [universal] |
| conversation-memory | Search past sessions, surface patterns, self-referential learning | `/conversation-memory` | [universal] |
| tool-discovery | Discover new open-source tools via GitHub scan, classify, evaluate, propose | `/tool-discovery` | [universal] |
| eval-repo | Evaluate external git repos for tech radar classification (3-level: DeepWiki, clone, deep) | `/eval-repo` | [universal] |
| harness-audit | Evaluate harness components for relevance, identify retirement candidates | `/harness-audit` | [universal] |
| opik-integration | Configure Opik for LLM observability, tracing, and evaluation | `/opik-setup` | [universal] |
| cognee-integration | Configure Cognee for knowledge graph memory and MCP integration | `/cognee-setup` | [universal] |
| deepeval-integration | LLM unit testing, trajectory eval, red teaming (60+ metrics) | `/deepeval-setup` | [universal] |
| ragas-integration | Memory quality testing, retrieval eval, synthetic test generation | `/ragas-setup` | [universal] |
| promptfoo-integration | Prompt regression testing and red teaming in CI/CD | `/promptfoo-setup` | [universal] |
| strands-evals-integration | Trace-based agent trajectory evaluation (OpenTelemetry) | `/strands-setup` | [universal] |
| automaker-bridge | Configure AutoMaker to use Cognitive OS as its execution brain | `/automaker-bridge` | [universal] |
| batch-runner | Execute multiple SDD changes sequentially with timing, reporting, and failure handling | `/batch-run` | [universal] |
| contract-drift | Detect drift between HTTP calls in source code and OpenAPI/Swagger contract definitions | `/contract-drift` | [universal] |
| document-feature | Generate or update structured feature documentation using 3-layer detection | `/document-feature` | [universal] |
| gpu-sandbox | Execute Python code in Jupyter runtime for compute-heavy tasks (ML, data, financial) | `/gpu-sandbox` | [universal] |
| issue-pipeline | Fetch a GitHub issue, run the SDD pipeline, and open a pull request | `/issue-to-pr` | [universal] |
| memu-context | Query memU proactive memory for relevant context before starting work | _auto_ | [universal] |
| paperclip-dashboard | View Cognitive OS metrics in Paperclip dashboard (SDD projects, agent status, spend, org chart) | `/paperclip-dashboard` | [universal] |
| resolve-blockers | Automatically resolve blockers reported by readiness-check | `/resolve-blockers` | [universal] |
| sandbox-sample | Classify, sample, sandbox-verify, then scale changes across large file sets | `/sandbox-sample` | [universal] |
| sdd-resume | Resume an SDD pipeline from its last completed phase with timing and state visibility | `/sdd-resume` | [universal] |
| singularity | Autonomous MAPE-K control loop: monitor, classify, and route codebase events | `/singularity` | [universal] |
| webhook-trigger | GitHub webhook server that receives issue events and launches SDD pipelines | `/webhook-trigger` | [universal] |
| auto-rollback | Automatically revert commits from a failed sdd-apply when verify exhausts all retries | `/auto-rollback` | [universal] |
| cognee-search | Semantic knowledge graph search via Cognee — relationship-aware retrieval | `/cognee-search` | [universal] |
| impact-analysis | Analyze the blast radius of changed files: importers, coverage, services, risk | `/impact-analysis` | [universal] |
| jupyter-execute | Execute code in a Jupyter kernel sandbox for data analysis and benchmarks | `/jupyter-exec` | [universal] |
| nemo-guardrails | Generate and configure NeMo Guardrails Colang 2.0 rules from Cognitive OS rules | `/nemo-guardrails` | [universal] |
| semgrep-scan | Run Semgrep SAST security scanning, report in adversarial review format | `/semgrep-scan` | [universal] |
| security-audit | Comprehensive security audit: secrets, permissions, hooks, infrastructure, Docker ports | `/security-audit` | [universal] |
| smoke-test | Run end-to-end smoke tests that validate the real Cognitive OS system works | `/smoke-test` | [universal] |
| confidence-check | Pre-implementation confidence assessment: 5-dimension readiness check before coding | `/confidence-check` | [universal] |
| self-review | Lightweight 4-question post-implementation checklist for non-SDD work | `/self-review` | [universal] |
| web-crawler | Fetch and convert web pages to LLM-ready markdown using Crawl4AI | `/web-crawler` | [universal] |
| deep-research | Multi-hop research with configurable depth (quick/standard/deep/exhaustive), structured reports | `/deep-research` | [universal] |
| research-protocol | Meta-skill: systematic investigation methodology (DISCOVER/ANALYZE/COMPARE/SYNTHESIZE) with per-type reading protocols and quality rubrics | `/research-protocol` | [universal] |
| audit-website | 6-category website audit (SEO, Performance, Security, Content/UX, Accessibility, Schema.org) with scored checkpoints and graded report | `/audit-website` | [universal] |
| persistent-agent | Create persistent agents with state across sessions: identity profile, event log, auto-fixation checklist | `/create-persistent-agent` | [universal] |
| estimation-report | View estimation calibration report: bias factors, accuracy, confidence per agent | `/estimation-report` | [universal] |
| planning-poker | Multi-agent Planning Poker: 3 independent complexity estimates, divergence detection, consensus building with calibration | `/planning-poker` | [universal] |
| pentest-self | Self-penetration testing: validate safety mesh across 6 categories (injection, permissions, secrets, flooding, scope, integrity) | `/pentest-self` | [universal] |
| performance-dashboard | Show performance metrics: latency percentiles, throughput, overhead, bottlenecks, component health | `cos perf` | [universal] |
| cost-predictor | Predict task cost from historical data, show confidence level, per-phase breakdown, measured model prices | `/cost-predict` | [universal] |
| simulation-arena | Run scripted scenarios simulating developer workflows, measure safety mesh, cost, learning evolution | `/simulate` | [universal] |
| scout | Quick pre-implementation codebase reconnaissance with 3 depth levels (quick/standard/deep) | `/scout` | [universal] |
| sdd-explore | Deep feasibility analysis for SDD pipeline explore phase — builds on scout report | `/sdd-explore` | [universal] |

## Project Skills [generated]

These skills are project-specific and live in `{project}/.claude/skills/`. They are generated by `/cognitive-os-init` based on detected stack. Examples:

| Skill | Description | Generated For |
|-------|-------------|---------------|
| framework-patterns | Framework-specific patterns (ginext, NestJS, Spring Boot, etc.) | All projects |
| start-stack | Start the full local stack | Multi-service projects |
| check-health | Health check with project endpoints | All projects |
| add-mock-provider | Add mock for external provider | Projects with external APIs |
| sre-agent-config | SRE overlay with project container map | All projects |

## Loading Protocol

1. **Level 1** (always): This catalog (~2K tokens)
2. **Level 2** (on demand): Full SKILL.md when skill is invoked or triggered (~1-3K tokens each)
3. **Level 3** (rare): references/ files for detailed examples (~2-5K tokens each)
4. **Max active**: 5 skills simultaneously. Unload after 5 min inactivity.
