# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.7.0] - 2026-04-09

### Added
- feat: Task DAG runner — declarative dependency graph for multi-agent workflows (lib/task_dag.py, 27 tests)
- feat: Agent health monitor — file-based dead/stuck agent detection without Valkey (lib/agent_health_monitor.py, 34 tests)
- feat: Queue drain on completion — blocked agents auto-enqueue and launch when slots free (lib/queue_drainer.py, 18 tests)
- feat: CronCreate scheduled drain — periodic 5-min fallback for stuck queues (lib/scheduled_drain.py, 15 tests)
- feat: Auto-repair with worktree isolation — fixes applied in isolated git worktree, verify, merge or discard (20 tests)
- feat: Auto-rewrite on skill failure — 3+ failures triggers /optimize-skill suggestion (9 tests)
- feat: Escalation detection wired — agents emit ESCALATION: markers, completion-gate detects (20 tests)
- feat: PromptBuilder — integrates context_diet + prompt_cache for token-efficient agent prompts (36 tests)
- feat: Dynamic model routing — DEGRADE/PROMOTE feed into model selection, budget-aware downgrade (16 tests)
- feat: E2E self-repair smoke test — 5 scenarios proving full feedback loop works (29 tests)
- feat: Closed-loop consequence tests — DEGRADE/PROMOTE/DISABLE validated end-to-end (22 tests)
- feat: cos-bootstrap.sh — one-command project setup (env, Docker, Langfuse, rules sync) (16 tests)
- feat: cos-update.sh — idempotent update for existing installations
- feat: scripts/test-all.sh — unified test runner with pytest-xdist parallel execution
- feat: Claude HUD — real-time statusline showing context %, costs, agents (ADOPT, MIT)
- feat: Langfuse v3 integration — traces + scores via OTEL API, auto-provisioned API keys
- feat: scripts/setup-langfuse.sh — fully automated Langfuse key provisioning (no manual steps)
- docs: self-repair-guide.md — user guide explaining what developers will experience
- docs: getting-started.md — updated with bootstrap, test runner, self-repair sections

### Fixed
- fix: agent preamble injection — sub-agents now emit TRUST_REPORT (was missing, cascade root cause)
- fix: cost tracking $0.00 — tool_response parsed as string, model-aware pricing (was always zero)
- fix: detect_success false positive — "0 failed" in Trust Report matched FAIL pattern
- fix: SeaweedFS healthcheck — localhost→127.0.0.1 (IPv6 resolution bug in Alpine)
- fix: integration test timeout — 30s→300s for testcontainers (was killing Docker fixtures)
- fix: hardcoded project path in test_e2e_flows.py — now uses Path(__file__).parents[2]
- fix: record_completion.py Langfuse API updated to v3 (OTEL-based spans + generations)
- fix: consequence-history.jsonl cleaned — 83% test data removed (600→102 real entries)

### Wired (hooks connected to settings.json)
- error-learning.sh (PostToolUse/Bash) — captures test/lint/build failures
- consequence-evaluator.sh (PostToolUse/Agent) — PROMOTE/DEGRADE/DISABLE decisions
- pre-compaction-flush.sh (PreCompact) — saves state before context reset
- resource-check.sh (PreToolUse/Agent) — budget enforcement blocks over-spend
- confidence-gate.sh (PostToolUse/Agent) — blocks low-confidence results in production

### Changed
- requirements.txt: langfuse>=3.0, pytest-xdist>=3.5 added
- rules/RULES-COMPACT.md: added skill-rewrite and task-dag references
- templates/agent-preamble.md: full escalation protocol with 5 signal types

## [Unreleased]

### Added
- docs: package migration plan — 10 integrations mapped to future cos packages
- docs: plugin marketplace design -- cos install with 6-gate security audit pipeline
- feat: dual-mode installer -- local source auto-detection + `--from` flag for `install.sh`
- docs: tech radar update — 26 Claude Code ecosystem tools analyzed (7 ADOPT, 19 WATCH, 5 BLOCK)
- docs: multi-tool architecture — adapter layer for OpenCode, Aider, Cursor support
- docs: 7 ecosystem integrations documented (agnix, claude-code-action, parry, Trail of Bits, recall, Usage Monitor, hcom)
- docs: 19 WATCH repos deep-analyzed — 22 extractable patterns prioritized (P0-P3)

## [0.1.0] - 2026-03-27

### Added
- SDD Pipeline: 12-phase structured development (explore -> archive)
- Safety Mesh: 13-layer defense system (clarification gate, blast radius, scope proportionality, etc.)
- Anti-Hallucination: ground truth checker, cross-verifier, claim validator
- Agent Security: least privilege permissions, audit trail, time-scoped access
- Performance Monitor: p50/p95/p99 latency, overhead tracking, bottleneck detection
- Token Economy: cost dashboard, decomposition rule, 5 token principles
- Cost Predictor: historical predictions based on real API response data
- Planning Poker: multi-agent task estimation with consensus algorithm
- System Knowledge Graph: 232 components, 430 edges, `cos map` command
- Agent Bus: Valkey pub/sub with heartbeat, progress tracking, file lock registry
- Estimation Calibration: predict -> actual -> adjust loop with per-agent factors
- Singularity Controller: MAPE-K autonomous loop (7 monitors, 9 event types)
- Issue-to-PR Pipeline: GitHub issue -> SDD -> PR (automated)
- Webhook Trigger: FastAPI server for GitHub event-driven automation
- Batch Runner: sequential multi-change SDD execution
- Component Linter: overlap detection, size warnings, registration checks
- Research Protocol: systematic investigation methodology (DISCOVER -> ANALYZE -> COMPARE -> SYNTHESIZE)
- 80+ skills including: contract-drift, deep-research, audit-website, confidence-check, self-review, persistent-agent, security-audit, pentest-self
- 60+ rules covering: quality, security, performance, cost, architecture
- 60+ hooks for lifecycle automation
- 30+ Python lib modules
- 2 Go CLI tools: cos (package manager v0.1) and cos-test (TUI test runner)
- 2200+ automated tests (pytest + Go tests)
- Testcontainers for 17 Docker services
- Coexistence with existing .claude/ configurations (cos/ namespace)
- Self-hosting (dogfooding): the OS builds itself using its own tools

### Architecture
- 5-Layer Clean Architecture for Agent OS (Rules -> Skills -> Hooks -> Libs -> Externals)
- Dependency rule: dependencies only point inward
- UX Principles: invisible safety, AI as driver, progressive disclosure

### Infrastructure
- Docker Compose with 18 services (Langfuse, Opik, Cognee, Valkey, LiteLLM, etc.)
- Multi-model routing (Anthropic, OpenAI, Google, DeepSeek, local)
- Engram persistent memory with organized topic keys
