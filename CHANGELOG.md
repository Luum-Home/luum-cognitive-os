# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.9.0] - 2026-04-16 — "Self-Awareness"

Major stabilization release following the growth crisis post-mortem. OS can now
detect its own degradation patterns. See docs/architecture/POST-MORTEM-2026-04.md.

### Added

**Self-awareness mechanisms (the 5 wounds prevented):**
- feat: cos-dispatch Go binary — vendor-agnostic hook dispatcher (Phases 1-4 complete)
  - 11 Go packages, all tests passing on Go 1.25.6
  - Validators + transformers + predicates + provider adapters for 5 AI coding agents
  - SQLite pattern tracker with 3 detector types (RepeatedFailure, PerfRegression, ErrorCluster)
  - 6 high-value bash hooks ported to Go (rate-limiter, rate-limit-protection, secret-detector, content-policy, completeness-checker, prompt-quality)
- feat: lib/pattern_detector.py — detects dead metadata, broken chains, phantom entries, structural tests
- feat: lib/adr_detector.py + hooks/adr-detector.sh — auto-generates ADR drafts on architectural git commits (8 weighted signals)
- feat: hooks/_lib/file_checker.sh — symlink-aware file existence checks (prevents false "missing" reports)
- feat: /audit-integrity skill — standardized audit with symlink resolution
- feat: /detect-patterns skill — on-demand pattern detection

**Agent amnesia prevention:**
- feat: templates/agent-mandatory-rules.md — rules injected into every sub-agent via SubagentStart hook
- feat: Updated hooks/subagent-context-injector.sh to load mandatory rules automatically

**Task panel bridge (ADR-024):**
- feat: hooks/_lib/task_bridge.py — correlates COS task_id with Claude Code tool_use_id
- feat: hooks/task-bridge-notify.sh — PostToolUse hook emitting hookSpecificOutput with COS orchestration state
- feat: Enhanced hooks/agent-prelaunch.sh to capture tool_use_id

**Cross-device memory:**
- feat: scripts/engram-sync.sh — project-scoped export/import of engram observations to git
- feat: Activated packages/engram-sync hooks (Stop + SessionStart)
- feat: First export: 544 observations at .engram/exports/luum-cognitive-os.jsonl

**Claude Code feature integration (ADR-021 adapter pattern):**
- feat: hooks/_lib/recap_adapter.py + hooks/recap-sync.sh — integrates session-wrapup with Claude Code /recap
- feat: hooks/task-panel-sync.sh + _lib/task_panel_adapter.py — exposes active-tasks to native UI
- feat: Registered TeammateIdle/TaskCreated/TaskCompleted events in settings.json
- feat: 3 prompt-type hooks (prompt-quality-llm, completeness-check-llm, confidence-gate-llm) — Haiku-evaluated advisories (ADR-022)
- feat: .claude/plugins/cos-monitors/plugin.json — native monitors manifest for background daemons
- feat: Skills sweep — 21 skills annotated with paths/disable-model-invocation/effort frontmatter

**Mutation via updatedInput (ADR-023):**
- feat: hooks/secret-detector.sh — redacts AWS/GitHub/Slack/Stripe/OpenAI secrets via updatedInput instead of blocking
- feat: hooks/blast-radius.sh — emits warnings via additionalContext, still allows execution
- feat: hooks/inject-phase-context.sh + context-diet.sh — migrated to native hookSpecificOutput.additionalContext

**CI gate for test quality:**
- feat: .github/workflows/test-quality.yml — mutation testing (cosmic-ray) + structural test detector on PRs
- feat: scripts/check-test-quality.py — AST-based classifier (CI/pre-commit/manual modes)
- feat: .cosmic-ray.toml — mutation testing config
- feat: Pre-commit Gate 3f blocks structural-only tests

**2-tier skill loading:**
- feat: skills/CATALOG-COMPACT.md — ~60% token reduction at session start (~2965 vs 7243)
- feat: scripts/generate-compact-catalog.py — regenerates from SKILL.md files
- feat: /catalog-full skill for on-demand full catalog

**Onboarding tooling:**
- feat: scripts/setup.sh — one-command dependency install (--minimal/--standard/--full)
- feat: scripts/doctor.sh — 12 health check categories
- feat: .go-version + goenv integration (Go 1.25.6)
- feat: docs/setup/dependencies.md — comprehensive manifest by package manager

**ADRs (7 new, 16 retroactive = 22 total):**
- ADR-006 through ADR-020: retroactive coverage of March 21 - April 13 history
- ADR-021: Vendor-agnostic state with provider adapters
- ADR-022: Prompt-type hooks adoption (Haiku-evaluated)
- ADR-023: updatedInput pattern (mutate vs block)
- ADR-024: Task Panel Bridge (tool_use_id correlation)

**Institutional memory (4 living documents):**
- docs/architecture/stabilization-roadmap.md — status tracker
- docs/architecture/FROZEN-BACKLOG.md — 30+ deferred plans
- docs/architecture/LESSONS-LEARNED.md — 5 wounds + red flags
- docs/architecture/POST-MORTEM-2026-04.md — full retrospective

**Testing:**
- 23 behavioral tests for 3 hook perf fixes (rate-limit-protection, dispatch-gate, completion-gate)
- 10 tests for Task Panel Bridge
- 18 tests for prompt-type hooks
- 22 tests for pattern detector
- 54 tests for auto-ADR detector
- docs/testing/README.md — comprehensive testing guide

### Fixed

**Performance (3 critical hooks):**
- perf: rate-limit-protection.sh — O(n) Python per-line → single call (30-90s → 50-100ms)
- perf: dispatch-gate.sh — 9 Python cold starts → 1 consolidated call (2.1s → 300-400ms)
- perf: completion-gate.sh — EXIT trap guarded behind Agent check (42s/session saved from non-Agent calls)
- perf: session-init.sh — 3 Python cold starts → 1 helper script

**Test infrastructure:**
- fix: 8 failing singularity tests — extracted _singularity_suggestion to _lib/ for isolated testing (20x faster)
- fix: test_app_services.py collection error (DockerContainer type annotation)

**Stale references cleanup:**
- fix: Removed 8 dead config flags + 18 dead config sections from cognitive-os.yaml
- fix: project.name corrected from my-project to luum-cognitive-os
- fix: Bifrost disabled in config to match docker-compose (ADR-011 superseded by ADR-018)
- fix: Removed 179 dead SCOPE/scope tags from 84 hooks + 95 libs (no code reads them)

### Removed

- 67 structural-only test files (false coverage) — tests/smoke/ deleted entirely
- 2,317 lines of structural tests pruned from 33 mixed behavior files
- 3 phantom skill entries from CATALOG.md (skills with no SKILL.md)
- 3 phantom entries from lib/skill_router.py routing table

### Changed

- Audience filtering now implemented in lib/skill_router.py (was metadata-only for 18 days)
- .claude/settings.json: 10 new hooks registered across events
- scripts/apply-efficiency-profile.sh + set-security-profile.sh: updated for all new hooks

### Notes

- Stabilization reached 98% per stabilization-roadmap.md
- 4 components identified for reclassification to packages/ (deferred to v1.0 — see FROZEN-BACKLOG)
- 50+ commits in the 2-session stabilization effort

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

## [0.8.4] - 2026-04-10

### Added
- feat: security-tools-landscape.md — implementation status tracking for P1/P2 security tools
- feat: tero-testing and mantis-security packages with cos-package.yaml manifests
- feat: workflow YAML files (feature-pipeline.yaml, bugfix-pipeline.yaml) in .cognitive-os/workflows/
- fix: pre-commit hook Gate 3e made advisory (warn, not block) on malformed workflow YAML
- fix: pre-commit hook gate labels standardized (Gate 3a–3e) for consistent detection
- fix: docs/INDEX.md version updated to v0.8.4

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
