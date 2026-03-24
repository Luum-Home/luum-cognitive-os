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
