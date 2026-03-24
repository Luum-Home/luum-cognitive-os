# Changelog

All notable changes to Cognitive OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-24

### Added

- Core Cognitive OS framework (`.cognitive-os/` portable directory)
- `cognitive-os.yaml` configuration with phase-aware governance
- `/cognitive-os-init` skill for automatic stack detection and project setup
- 3-layer architecture: Core (universal) / Project (specific) / Generated (auto-detected)

#### Hooks (21)
- Session lifecycle hooks (SessionStart, PreToolUse, PostToolUse, Stop)
- Error learning and auto-repair (MAPE-K loop)
- Skill metrics tracking
- Tool loop detection and circuit breaker
- Pre-compaction memory flush
- Auto-test on edit, auto-refine, auto-verify
- Secret detection and dangerous command blocking

#### Skills (42+)
- Spec-Driven Development (SDD) 10-phase workflow
- Systematic debugging, TDD, verification
- SRE agent with self-healing
- Model optimizer and cost tracker
- Squad manager and agent orchestration
- Skill auto-generation and adaptation
- Context optimizer and error analyzer

#### Rules (19)
- Fault tolerance and SRE protocol
- Secret hygiene and license compliance
- Phase-aware governance (reconstruction/stabilization/production/maintenance)
- Definition of Done (trivial through critical)
- Squad protocol and agent quality standards

#### Infrastructure
- Docker Compose stack (PostgreSQL, Valkey, Langfuse, LiteLLM, NeMo Guardrails)
- Engram persistent memory (MCP server)
- Metrics rotation and auto-calibration

#### Documentation
- 60+ documents covering architecture, features, and business case
- Open-source design document with core/plugin separation
- Public roadmap

#### Testing
- Test suite with unit, integration, infrastructure, quality, and arena tests
- Master test runner (`tests/run-all-tests.sh`)
