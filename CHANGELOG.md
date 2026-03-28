# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.2.0] - 2026-03-28

### Security
- security: pin all Docker images to SHA256 digests (supply chain defense)
- security: supply_chain config section in cognitive-os.yaml
- fix: rate limiter blocked attempts no longer inflate counter

### Added
- feat: Bifrost dual-gateway — LiteLLM complement with 11us latency, failover chain
- feat: Scout Pattern + sdd-explore skills — pre-implementation reconnaissance (3 depth levels)
- feat: WorkloadScheduler — proactive agent dispatch across rate limit windows
- feat: Smart file reader — auto-pagination for files >10K tokens + advisory hook
- feat: User prompt auto-capture — bilingual EN/ES classifier for engram persistence
- feat: Rate limiter phase awareness — reconstruction 1.5x, production 0.75x
- feat: Graceful rate limits — priority queue, batch suggestions, structured QUEUED messages
- feat: Agent Bus on-demand — dedicated Valkey via smart_infra auto-start
- feat: Non-blocking retry scheduler — CronCreate-based deferred agent re-launch
- feat: cos status — show packages with unreleased changes
- feat: cos release-all — batch release for monorepo (--patch/--minor/--dry-run)
- feat: cos release --check — validate release readiness
- feat: cos publish scoped tags — @luum/{name}@{version} format
- feat: cos_version compatibility check on install
- feat: cos CLI README — full documentation with CI/CD examples
- feat: agent preamble — long-running commands must use run_in_background

### Fixed
- fix: self-install.sh legacy symlink cleanup (relative path matching)
- fix: rootCmd.Version dynamic (ldflags + runtime VERSION file read)
- fix: SearchGitHub() GITHUB_TOKEN auth support
- fix: 47 legacy symlinks removed from .claude/rules/ root

### Changed
- 87 rules (was 83), 88 skills, 73 hooks
- Rules consolidation safety tests (42 tests) as pre-consolidation baseline
- EXPECTED_RULE_COUNT now dynamic (no manual updates needed)
- 3600+ Python tests, 230+ Go tests — all passing

### Documentation
- docs: versioning strategy — dual OS core + package independent semver
- docs: WISC framework analysis — context loading impact on performance
- docs: AI gateway landscape — 11 gateways compared
- docs: cos-package-manager updated with new commands

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
