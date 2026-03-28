# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- feat: dual-mode installer -- local source auto-detection + `--from` flag for `install.sh`
- docs: tech radar update — 26 Claude Code ecosystem tools analyzed (7 ADOPT, 19 WATCH, 5 BLOCK)
- docs: multi-tool architecture — adapter layer for OpenCode, Aider, Cursor support
- docs: 7 ecosystem integrations documented (agnix, claude-code-action, parry, Trail of Bits, recall, Usage Monitor, hcom)

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
