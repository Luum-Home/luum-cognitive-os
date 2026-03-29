# Cognitive OS Skills Catalog

> Compact index loaded at session start. Full SKILL.md loaded on demand (Level 2).

## Universal Skills

| Skill | Description | Invoke | Audience |
|-------|-------------|--------|----------|
| cognitive-os-init | Initialize Cognitive OS for a project: detect stack, generate config and project-specific files | `/cognitive-os-init` | os-dev |
| cognitive-os-test | Run the Cognitive OS automated test suite (infra, behavior, quality) | `/cognitive-os-test` | os-dev |
| cognitive-os-benchmark | Run benchmark comparisons | `/benchmark` | os-dev |
| cognitive-os-status | Report Cognitive OS status: hooks, rules, skills, squads, metrics | `/cognitive-os-status` | both |
| compat-test | Smoke test: verify model compatibility with Cognitive OS (8 checks, < 30s) | `/cognitive-os-compat-test` | os-dev |
| component-classifier | Classify new components as CORE or PACKAGE | `/component-classifier` | os-dev |
| validate-config | Validate all Cognitive OS config files: agents, squads, skills, rules, hooks | `/validate-config` | both |
| capability-snapshot | Snapshot, diff, and restore Cognitive OS capabilities to prevent feature loss | `/capability-snapshot` | os-dev |
| self-improve | Self-improvement protocol: detect patterns, create/update skills/rules | `/self-improve` | os-dev |
| metrics-calibrator | Analyze KPI distributions, auto-adjust thresholds, propose derived metrics | `/metrics-calibrator` | os-dev |
| harness-audit | Evaluate harness components for relevance, identify retirement candidates | `/harness-audit` | os-dev |
| smoke-test | Run end-to-end smoke tests that validate the real Cognitive OS system works | `/smoke-test` | os-dev |
| security-audit | Comprehensive security audit: secrets, permissions, hooks, infrastructure, Docker ports | `/security-audit` | os-dev |
| pentest-self | Self-penetration testing: validate safety mesh across 6 categories | `/pentest-self` | os-dev |
| arena | Run competitive benchmarks against AI coding tools | `/arena` | os-dev |
| simulation-arena | Run scripted scenarios simulating developer workflows, measure safety mesh | `/simulate` | os-dev |
| tool-discovery | Discover new open-source tools via GitHub scan, classify, evaluate, propose | `/tool-discovery` | os-dev |
| release-os | Validate, version, tag, and release the Cognitive OS | `/release-os` | os-dev |
| opik-integration | Configure Opik for LLM observability, tracing, and evaluation | `/opik-setup` | os-dev |
| cognee-integration | Configure Cognee for knowledge graph memory and MCP integration | `/cognee-setup` | os-dev |
| deepeval-integration | LLM unit testing, trajectory eval, red teaming (60+ metrics) | `/deepeval-setup` | os-dev |
| ragas-integration | Memory quality testing, retrieval eval, synthetic test generation | `/ragas-setup` | os-dev |
| promptfoo-integration | Prompt regression testing and red teaming in CI/CD | `/promptfoo-setup` | os-dev |
| strands-evals-integration | Trace-based agent trajectory evaluation (OpenTelemetry) | `/strands-setup` | os-dev |
| automaker-bridge | Configure AutoMaker to use Cognitive OS as its execution brain | `/automaker-bridge` | os-dev |
| nemo-guardrails | Generate and configure NeMo Guardrails Colang 2.0 rules from Cognitive OS rules | `/nemo-guardrails` | os-dev |
| paperclip-dashboard | View Cognitive OS metrics in Paperclip dashboard | `/paperclip-dashboard` | os-dev |
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
| doc-sync | Detect and update stale documentation after code changes | `/doc-sync` | project |
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
| eval-repo | Evaluate external git repos for tech radar classification (3-level: DeepWiki, clone, deep) | `/eval-repo` | project |
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
| research-protocol | Meta-skill: systematic investigation methodology (DISCOVER/ANALYZE/COMPARE/SYNTHESIZE) | `/research-protocol` | project |
| audit-website | 6-category website audit (SEO, Performance, Security, Content/UX, Accessibility, Schema.org) | `/audit-website` | project |
| persistent-agent | Create persistent agents with state across sessions: identity profile, event log | `/create-persistent-agent` | project |
| estimation-report | View estimation calibration report: bias factors, accuracy, confidence per agent | `/estimation-report` | project |
| planning-poker | Multi-agent Planning Poker: 3 independent complexity estimates, divergence detection | `/planning-poker` | project |
| performance-dashboard | Show performance metrics: latency percentiles, throughput, overhead, bottlenecks | `cos perf` | project |
| cost-predictor | Predict task cost from historical data, show confidence level, per-phase breakdown | `/cost-predict` | project |
| run-tests | Auto-detect project test framework and run tests with structured pass/fail reporting | `/run-tests` | project |
| repo-forensics | Deep forensic analysis of git repos: clone, scan all code, deps, architecture, tools, features, COS comparison | `/repo-forensics` | both |
| red-team | Red team testing for agent prompts: detects injection, jailbreak, and manipulation vulnerabilities via Promptfoo | `/red-team` | os-dev |
| vulnerability-scan | Run LLM vulnerability probes using Garak against configured endpoints | `/vulnerability-scan` | os-dev |
| agent-stress-test | Stress-test agent cognitive health to detect context-induced degradation | `/agent-stress-test` | os-dev |

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
