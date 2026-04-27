# Changelog

All notable changes to Cognitive OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.19.0] - 2026-04-27 — "ADR-068 Phase 1: Adaptive Pytest"

### Added — ADR-068 Phase 1: adaptive pytest worker selection

- `scripts/detect_runner_capacity.py` — cross-platform helper implementing the 6-row heuristic table (cores≤2→serial, load>70%→2, mem<2GB→4, battery<30% off-AC→serial, CI=true→auto, default→auto). Emits scalar token to stdout (`auto`/`0`/integer); `--json` flag exposes full diagnostics dict.
- `scripts/pytest-with-summary.sh` now invokes the detector when no `-n`/`--numprocesses` flag is present, preventing the 21-min serial regression that triggered the ADR. Explicit `-n` and `COS_PYTEST_WORKERS` env var both short-circuit detection per the override precedence chain.
- `tests/unit/test_detect_runner_capacity.py` — 9 unit tests covering each heuristic row, override precedence, and JSON diagnostics. psutil-missing path is exercised via mocked import failure; production path degrades to `auto` with a stderr warning.
- ADR-068 status: **Proposed → Accepted**.

## [0.18.0] - 2026-04-27 — "cos-init Python + Defense-in-Depth Complete"

### Added — cos-init.sh fully migrated to Python (strangler-fig complete)

- `scripts/cos_init.py` — full Python implementation of cos-init flow (Python 3.11+, stdlib + pyyaml)
- `scripts/cos-init.sh` collapsed from **711 → 5 lines** (exec shim for backward compat with `bash scripts/cos-init.sh`)
- 6 functions migrated through strangler-fig phases (2.1 → 2.final):
  - Phase 2.1 (`8a4778c`): `detect_harness()`
  - Phase 2.2 (`39dd40c`): `scope_allows()` + `skill_scope_allows()`
  - Phase 2.3 (`7fde5f9`): `install_rule()` + `install_hook()` + `install_skill_dir()`
  - Phase 2.final (`31f0002`): all 12 procedural sections (stack detection, mode components, dir structure, rules/hooks/skills install, templates, cognitive-os.yaml write, efficiency profile filtering, settings.json merge, install-meta, registry registration, gitignore update, summary)
- 47 unit tests + 29 parity tests + 72 integration tests pass post-migration
- Per ADR-066 polyglot policy: bash kebab-case shim retained, Python snake_case implementation owns the logic

### Added — ADR-067 Phase 2 defense-in-depth (rules + hooks + ADRs)

Extends the template + hook + audit pattern from `skills/*/SKILL.md` (Phase 1) to 3 more artifact types:

- `templates/rule-template.md`, `templates/hook-template.sh`, `templates/adr-template.md` — canonical skeletons with `<REQUIRED>` placeholders
- `hooks/rule-frontmatter-validator.sh` — PostToolUse Edit/Write hook for `rules/*.md`. Validates SCOPE, H1, opening section, conditional `## Contextual Trigger`. Advisory by default; BLOCK opt-in via `COS_STRICT_RULE_VALIDATION=1`.
- `hooks/hook-header-validator.sh` — for `hooks/*.sh`. Validates shebang, SCOPE, PURPOSE, EVENT, `set -euo pipefail`. Grandfathers existing 154 hooks (only enforces for new). `COS_STRICT_HOOK_VALIDATION=1`.
- `hooks/adr-section-validator.sh` — for `docs/adrs/ADR-*.md`. Validates required sections (Status, Context, Decision, Consequences, Alternatives rejected, Verification with ≥1 fenced code block). Cutoff at ADR-067 — pre-067 ADRs grandfathered. `COS_STRICT_ADR_VALIDATION=1`.
- All 3 hooks: fast-path filter (skip Python startup if input doesn't match path pattern), bash 3.x compatible
- Hook registration in: `apply-efficiency-profile.sh` + `set-security-profile.sh` + 3 hook-architecture-v2 profile JSONs
- Audit tests extended: `test_rules_enforcement.py` (+4 tests), `test_hooks_contracts.py` (+1 contract), new `test_adr_contracts.py` (+5 tests)
- `/add-rule` and `/add-hook` skills updated to reference their templates
- ADR-068 self-bootstrap fix: its own `## Verification` section now has a code block (caught by the new audit test)

### Added — deps-update v2 (MCP-aware)

Lessons from the 2026-04-27 engram MCP outage codified into tooling:

- `scripts/deps-update.sh` — engram section rewritten brew-first (instead of `go install`):
  - `brew update` + `brew install/upgrade` preferred (Operon-safe path)
  - `which -a engram` multi-path conflict detection with symlink fix suggestions
  - Backup-before-replace (timestamped `.bak`)
  - `⚠️  Restart Claude Code` reminder when binary changed
- `scripts/check_mcp_servers.py` — diagnostic script: reads MCP configs, resolves binaries via `which -a`, checks process via `pgrep`, reports version. `--json` mode for machine readers.
- `tests/unit/test_check_mcp_servers.py` — 8 tests covering standalone config, mcpServers format, plugin-bundled config, multi-path detection, missing-process WARN, missing-binary ERROR, JSON output validity.
- `docs/tooling-update-protocol.md` (new, 147 lines) — protocol for updating any Claude Code-integrated tool. Covers 3-paths trap, MCP restart requirement, brew vs go install vs manual, verification post-update, rollback. Living example: engram 2026-04-27 case study.
- `skills/deps-update/SKILL.md` — adds 4 new sections: brew-first flow, multi-path resolution trap, MCP server lifecycle, backup/rollback.

### Changed — Breaking (pre-1.0)

- **`scripts/cos-init.sh` is now a shim** — all logic lives in `scripts/cos_init.py`. Functionally backward compatible (CI / `install.sh` / docs all invoke `bash scripts/cos-init.sh`), but `--internal-call` dispatcher is the only Python-direct entry point now.

### Fixed

- **engram MCP server outage** (manual fix, no commit): `~/go/bin/engram v1.13.1` was SIGKILL'd by macOS Operon Sandbox when spawned from Claude Code. Resolution: `brew install gentleman-programming/tap/engram` → v1.14.5 + symlinks unified across `~/.local/bin/engram` + `~/go/bin/engram` → both point to brew canonical install. Engram MCP now operational, `mem_save`/`mem_search` available across sessions. Documented in engram observation `tooling/engram-mcp-fix` (#13280).

### Added — Tests

- `tests/unit/test_cos_init_py.py` — 47 unit tests across 6 functions
- `tests/behavior/test_cos_init_parity_2_1.py` + `_2_2.py` + `_2_3.py` — 29 parity tests (Python output == bash output, byte-for-byte)
- `tests/audit/test_adr_contracts.py` (new) — 5 tests including monotonic-warn for ADR numbering gaps
- `tests/unit/test_check_mcp_servers.py` — 8 tests

### Verified

- 76 unit + parity tests pass (2.59s)
- 72 integration tests pass (3m 26s) including `test_fresh_install_canary` full + idempotent upgrade
- 1813 audit tests pass, 0 failures (post-Phase-2 add)
- Live install test: 3 scratch directories (node --default, python --full, go --harness=codex) all produce correct output

### Operator decisions accepted (from research-first triage)

- **9 cos-init migration decisions**: pyyaml, defer generate-project-settings, inline detect_harness, keep bash shim, subprocess.run, tomllib+tomli fallback, both unit+parity tests, strangler-fig, drop bash 3.x constraint
- **9 ADR-067 Phase 2 decision points + 5 open questions**: WARN advisory default, ADR-067 cutoff (no pre-067 backfill), grandfather 154 existing hooks, flat templates/, extend existing audit tests where possible, CI-gated, integrate with /add-rule + /add-hook skills, conditional Contextual Trigger enforcement, ≥1 fenced code block in ADR Verification, monotonic ADR numbering WARN not BLOCK

### Known issues (deferred)

- **125 unanswered operator decisions** still surfaced by `/decision-triage` (mostly historical ADR open questions; today's research reports' decisions all answered).
- **`rich 14→15`**: blocked by cognee[memory] pin `rich<13.7.0` — pending cognee upstream upgrade.
- **`wrapt 1→2`**: deferred until OpenTelemetry transitives validate 2.x.
- **hermes-agent `default_backend()` cleanup**: 3 files, ~30 min, before cryptography 49.0.0.
- Phase 2 of `/add-rule` and `/add-hook` skill updates: templates referenced; full automation deferred.

## [0.17.0] - 2026-04-25 — "Defense-in-Depth + Research-First"

### Added — ADR-065 Tech Radar Curation Pipeline

- `docs/adrs/ADR-065-radar-update-curation-pipeline.md` — design for `/radar-update` skill
- `skills/radar-update/SKILL.md` + `scripts/radar_merge.py` — Phase 1: skill + merge engine + dry-run
- `tests/unit/test_radar_merge.py` — 28 tests covering dedup, human-field preservation, classification routing, classification shift, fuzzy match, artifact parser, CHANGELOG updater, diff generation

### Added — ADR-066 Polyglot Language Boundaries

- `docs/adrs/ADR-066-polyglot-language-boundaries.md` — bash/Python/Go role matrix + naming conventions + migration triggers
- `rules/python-naming.md` + `tests/audit/test_python_naming.py` — Python `snake_case` enforcement
- `rules/bash-naming.md` + `tests/audit/test_bash_naming.py` — bash kebab-case enforcement
- `.github/workflows/go-quality.yml` — `gofmt -l` + `go vet` CI gates for 3 Go modules

### Added — ADR-067 SKILL.md Defense-in-Depth (Phase 1)

- `docs/adrs/ADR-067-frontmatter-defense-in-depth.md` — 3-layer defense pattern (template + hook + audit)
- `templates/skill-template.md` — canonical SKILL.md skeleton with explicit `<REQUIRED>` placeholders
- `hooks/skill-frontmatter-validator.sh` — PostToolUse Edit/Write hook (advisory by default, blocks on `COS_STRICT_SKILL_VALIDATION=1`); fast-path skips Python startup when input doesn't contain `SKILL.md` (17ms vs 70ms)
- `tests/audit/test_skill_descriptions_nonempty.py` — 3 audit tests using fixed `_fm()` parser
- Hook registered in 5 places (apply-efficiency-profile + set-security-profile + 3 hook-architecture-v2 profile JSONs)

### Added — ADR-068 Adaptive Test Runner Capacity

- `docs/adrs/ADR-068-adaptive-test-runner-capacity.md` — cross-platform heuristic for choosing `-n auto|N|0` based on CPU/memory/load/battery/CI

### Added — ADR-069 Research-First Protocol

- `docs/adrs/ADR-069-research-first-protocol.md` — 3-phase cycle (research → operator triage → implementation) for high-risk changes (4-dimensional risk scoring)
- `templates/agent-research-only.md` — boilerplate for research-only agent prompts
- `rules/research-first-protocol.md` + `tests/audit/test_research_reports_format.py` — operational policy + audit gate
- 3 research reports landed using the protocol:
  - `docs/reports/cos-init-migration-2026-04-24.md` — feasibility analysis (9 decision points)
  - `docs/reports/adr-067-phase-2-2026-04-24.md` — defense-in-depth Phase 2 scope (15 decisions)
  - `docs/reports/python-major-bumps-2026-04-24.md` — wrapt/rich/cryptography probe

### Added — Skills

- `/repo-scout` (renamed from `/eval-repo`, v2.0): scout external git repos for tech radar with bulk mode (`--batch <file>`), per-repo markdown artifacts, adoption signals (issue velocity, release cadence, CI health). Old `/eval-repo` kept as deprecated alias stub.
- `/radar-update` (Phase 1): merge `/repo-scout` evaluations into `docs/patterns/ecosystem-tools.md` + `docs/blocked-tools.md` with dry-run by default
- `/decision-triage`: aggregate unanswered operator decisions across research reports + ADRs into a single ranked view. Score-based urgency heuristic (initial 0/125 critical → 33/125 critical after improved scoring).
- `/deps-update`: automated audit + upgrade across Python deps, engram binary, Claude Code plugins, Docker images. Modes: `--audit` (default), `--apply`, `--apply --major`, `--dry-run`.

### Added — Auditing

- `tests/audit/test_python_naming.py`, `tests/audit/test_bash_naming.py` — naming convention enforcement
- `tests/audit/test_skill_descriptions_nonempty.py` — frontmatter contract enforcement
- `tests/audit/test_research_reports_format.py` — research report structure validation
- `tests/audit/test_packages_hooks_lib_symlinks.py` — packages/*/hooks/_lib symlink integrity
- `docs/architecture/parser-coverage-audit-2026-04-24.md` — audit of 12 sibling parsers for `_fm()`-class gaps

### Changed — Breaking (pre-1.0)

- **35 Python scripts renamed** from kebab-case to snake_case (`scripts/*-*.py` → `scripts/*_*.py`). 143 caller files updated atomically. Backward compat: zero (no aliases). See `rules/python-naming.md` for migration table.
- **`/eval-repo` → `/repo-scout`** (skill rename). Old name kept as deprecated alias.
- **`cognee` removed from `[dev]` extra** — moved to `[memory]` extra. Reason: `kuzu` (cognee transitive) fails to build with `make clean` errors, blocking normal `uv sync --extra dev`. Opt-in explicitly with `uv sync --extra memory`.

### Fixed

- **`lib/session_hygiene._fm()` parser**: regex required `^---` at absolute file start, but every SKILL.md begins with `<!-- SCOPE: ... -->\n---`. 18 skills appeared as "No description" in CATALOG.md. Fix: `re.MULTILINE` flag + multi-line block scalar handling. Result: 0 "No description" entries.
- **2 sibling parsers had same bug**: `lib/pattern_detector._parse_frontmatter_keys` + `lib/smart_access.get_skill_frontmatter`. Same fix applied.
- **`packages/quality-gates/hooks/_lib` symlink missing** — caused `completion-gate.sh` crash. Fix: created symlink + audit test. Bonus: 17 OTHER `packages/*/hooks/` directories had the same latent bug — all fixed in one pass.
- **35 hyphenated Python script names** caused pytest importlib hacks + Python 3.14 dataclass resolution failures. Fix: snake_case rename + enforcement rule.
- **17 `gofmt` debt files** — cleared with `gofmt -w` (precondition for go-quality.yml CI to be green).
- **5 perf flakes under `-n auto`** — `@pytest.mark.xdist_group("perf")` to serialize within xdist (not `@pytest.mark.flaky`).
- **Project registry pollution** (post-v0.16.0): 3 stale "target" duplicates from pytest fixtures removed. Registry: 10 → 7 real entries.
- **Hook bookkeeping after `skill-frontmatter-validator.sh` add**: scorecard 154→155, baselines regenerated, orphan-hooks contract restored.
- **Rule bookkeeping after `bash-naming.md` add**: classified in CORE_RULES, stale file refs in pedagogical examples removed.

### Documentation

- `docs/architecture/cos-update-vs-cos-cli-responsibility-analysis.md` — bash orchestrator vs Go package manager scope clarity (commit `583dc5c`)
- `rules/research-first-protocol.md` — when to use research-first vs background agents (4-dim scoring)

### Performance

- `hooks/contextual-rule-loader.sh` — already shipped in 0.16.0 (17x speedup); no regressions in 0.17.0
- `hooks/skill-frontmatter-validator.sh` fast-path — 70ms → 17ms per non-skill invocation
- `scripts/decision_triage.py` urgency heuristic — score-based (was returning 0 critical for 125 real decisions)

### Verified

- Python 7148/7154 unit tests pass (6 perf flakes confirmed under `-n auto`, all pass `-p no:xdist`)
- Shard-B 3967/3988 pass (21 pre-existing flakes from install-test resource contention, all pass `-p no:xdist`)
- 162 provider tests pass post-refactor

### Known issues (deferred)

- **Research report dual-location**: `.cognitive-os/reports/research/` (gitignored) vs `docs/reports/` — 3 reports exist in both, causing duplicates in `/decision-triage` output. Will be unified in next session.
- **rich 14→15 upgrade blocked**: `cognee[memory]` pins `rich<13.7.0`, breaking `[dev]+[memory]` combo. Reverted to `rich>=14`. Pending: cognee upstream upgrade.
- **wrapt 1→2** + **cryptography deprecated `default_backend()` in hermes-agent**: deferred per `docs/reports/python-major-bumps-2026-04-24.md`.
- **125 unanswered operator decisions** surfaced by `/decision-triage` (33 critical from today's research reports).

## [0.16.0] - 2026-04-24 — "Multi-Provider + Harness-Agnostic"

### Added — ADR-062 Multi-Provider Agent Loop

- `packages/llm-providers/` — 7 provider wrappers (qwen, openrouter, gemini, ollama, openai, deepseek, claude_sdk) behind uniform `REGISTRY` interface. Symlinked at `lib/providers`.
- `lib/openai_compatible_agent_loop.py` — generalized loop (renamed from `qwen_agent_loop.py`, which remains as a 65-line backward-compat shim).
- `lib/dispatch.py` — N-provider cascade with `ADVANCE_ON_ANY_FAILURE` vs `ADVANCE_ON_RATE_LIMIT_ONLY` policies; reads `llm_providers:` config block from `cognitive-os.yaml`.
- `scripts/smoke-multi-provider-fallback.sh` — per-provider smoke test with SIGALRM timeout (Unix-only).
- `/llm-status` skill v2.0.0 — provider inventory (tier, configured Y/N, advance policy, model_map); env key names detected (never values).
- Default cascade: `qwen,openrouter,gemini,ollama,claude` (zero ANTHROPIC_API_KEY path). `openai`, `deepseek`, `claude_sdk` are opt-in.

### Added — ADR-063 Agent() Replication Strategy

- `docs/adrs/ADR-063-agent-tool-replication-strategy.md` — reject full Agent() clone; adopt Python `claude-agent-sdk` (MIT) as triple-gated opt-in provider.
- `pyproject.toml` — `claude-sdk = ["claude-agent-sdk>=0.1"]` optional dep.

### Added — ADR-064 Harness-Agnostic Cognitive OS

- `docs/adrs/ADR-064-harness-agnostic-cognitive-os.md` — architectural decision for Codex/Cursor/bare-CLI support. Names 4 integration surfaces (event capture, hook registration, skill invocation, sub-agent spawning). 10-15 session roadmap.

### Added — ADR-058 Phoenix Observability

- Langfuse purged. Phoenix OTel replaces it as the observability backend.
- `/phoenix-trace-ui` skill.

### Added — ADR-060 Local-Only Policy

- `docs/adrs/ADR-060-local-only-optional-services.md` — pip-first, Docker-fallback, never-cloud-default.
- Opik removed. MemU wired with self-contained `memu-pg` backend.
- Profile-gated services: `cognee`, `nemo-guardrails`, `jupyter` behind `--profile memory|guardrails|jupyter`.
- `scripts/cos-bootstrap.sh` `--profile full` now correctly activates all three profiles (was silent no-op).

### Added — ADR-061 Focus Narrative + External Evidence

- `README.md` rewritten governance-first (leads with "governance layer for coding agents").
- `docs/vs-alternatives.md` — comparison with Hermes, Agent Zero, OpenClaw.
- `docs/migration-from/{vanilla-claude-code,hermes}.md` — recipe-style migration docs.
- `scripts/demo-governance.sh` — 5-minute governance value demo.
- `.github/workflows/weekly-public-metrics.yml` — Monday cron, updates badges (dogfood-score, REAL%, hook-wiring).

### Added — Measurement & Observability

- `/dogfood-score` — composite SO self-build maturity score (7 dimensions).
- `/component-reality-check` — drill-down into REAL/DORMANT/ASPIRATIONAL/METADATA classification.
- `aspirational-audit.py` — new `ON_DEMAND` classification label.
- `scripts/so-vs-vanilla-benchmark.py` — A/B test harness with `COS_DISABLE_ALL_GOVERNANCE=1` master kill-switch.

### Added — Dependency Maintenance

- `scripts/deps-update.sh` — automated audit + upgrade (Python/engram binary/plugins/Docker). Modes: `--audit` (default), `--apply`, `--apply --major`, `--dry-run`. Handles GOBIN-versioned-path trap.
- `/deps-update` skill (os-only, haiku).
- `/validate-release` paso 6: advisory deps audit call (non-blocking).

### Added — Project Scaffold

- 10 pilot skill unit tests (+7.12 skill_coverage): `audit-integrity`, `bump-version`, `compat-test`, `doc-sync`, `dod-check`, `evaluate-plan`, `exhaustive-prompt`, `invariant-check`, `session-backlog`, `validate-config`.

### Changed — Breaking (pre-1.0)

- **Langfuse removed** — replaced by Phoenix OTel (ADR-058).
- **Opik removed** — replaced by MemU self-contained backend (ADR-060).
- `lib/qwen_agent_loop.py` → `lib/openai_compatible_agent_loop.py` (shim preserves backward compat but file is now deprecated).
- `lib/providers/` is a symlink into `packages/llm-providers/lib/` (new package).

### Changed — Dependencies

- `uv sync --upgrade`: pydantic 2.12.5 → 2.13.3, openai 2.30.0 → 2.32.0, click 8.1.8 → 8.3.3, certifi 2026.2.25 → 2026.4.22 (CA bundle), +transitives. Skipped major bumps: wrapt 1→2, rich 14→15, cryptography 46→47 (queued for dedicated review).
- engram binary: `dev` build → `v1.13.1` (via `go install`). `~/.local/bin/engram v1.10.2` remains as MCP server path (macOS Operon sandbox blocks the go-installed binary — documented in code).

### Fixed

- **Hook chain 17x speedup**: `contextual-rule-loader.sh` 2200ms → 130ms. Root cause: O(n×m) subprocess forks iterating rules × patterns. Fix: in-process regex indent detection.
- **`completion-gate.sh` crash**: `packages/quality-gates/hooks/_lib` symlink to root `hooks/_lib` was missing. Fix: created symlink. Follow-up: audit other `packages/*/hooks/` for same bug.
- **Project registry pollution**: 241 stale pytest fixture entries in `~/.cognitive-os/installations.json` (251 → 10 real projects). Root cause: `tests/integration/test_install_scope.py` didn't set `COS_REGISTRY_FILE`. Fix: env var in tests + `PYTEST_CURRENT_TEST` guard in `cos_registry_register` as belt-and-suspenders.
- **engram roundtrip test**: failed after upgrade to v1.13.1. Root cause: macOS Operon sandbox SIGKILL'd `~/go/bin/engram` spawned from Claude Code. Fix: `_resolve_engram_bin()` prefers `~/.local/bin/engram` (has Gatekeeper allow-list) over `~/go/bin/engram`.
- `cos-bootstrap.sh --profile full` — was silent no-op for nemo/jupyter/cognee. Now passes the three profile flags.
- 15 unit perf test failures root-caused (not marked flaky). Result: 7155 pass / 0 fail.
- Empty-stdin fast-exit budget: 200ms → 500ms (documented with rationale).
- `observability-trace.sh` orphan symlink (post-ADR-058 cleanup).
- `test_profiled_services` post-Opik removal (ADR-060).
- `test_rules_enforcement`: registered 6 previously hook-enforced-BROKEN rules (audit-trail, auto-rollback, confidence-gate, confidentiality-protection, agent-identity, pre-dev-readiness-gate, reinvention-prevention).

### Documentation

- `docs/adrs/ADR-059-existential-validation.md` — 3-phase plan (prune humo / install-timing / core-extensions split).
- `docs/patterns/cross-harness-authoring.md` — self-check protocol for SO-path changes.
- Package migration plan — 10 integrations mapped to future `cos` packages.
- Plugin marketplace design — `cos install` with 6-gate security audit pipeline.
- `install.sh` dual-mode installer (local source auto-detection + `--from` flag).
- Tech radar update — 26 Claude Code ecosystem tools analyzed (7 ADOPT, 19 WATCH, 5 BLOCK).
- Multi-tool architecture — adapter layer for OpenCode, Aider, Cursor support (foundation for ADR-064).
- 7 ecosystem integrations documented (agnix, claude-code-action, parry, Trail of Bits, recall, Usage Monitor, hcom).
- 19 WATCH repos deep-analyzed — 22 extractable patterns prioritized (P0-P3).

## [0.15.0] - 2026-04-21 — "ADR-047 Phase A + Decision Depth Gate"

> Note: VERSION file was stale at 0.9.0 when this release was cut, but
> tags v0.10.0 through v0.14.2 already existed remotely (patch releases
> not documented in this CHANGELOG). Bumped to 0.15.0 as next available.
> This is the first documented release since 0.12.0; intervening patches
> exist as tags only.

### Added — ADR-047 Session Lifecycle Management (Phase A shipped)

- `scripts/so-session-watchdog.py` — Phase A log-only daemon. Classifies sessions (HEALTHY / IDLE_OVER_TTL / ORPHANED / RESUMED_RECENTLY), writes `session-watchdog.jsonl`. NEVER kills.
- `lib/session_watchdog_lib.py` — layered Phase B liveness predicate: `should_kill() = parent_dead OR (ttl_exceeded AND heartbeat_stale AND metric_writes_stale AND cpu_idle_sustained)`. 4 checks, each tested independently.
- `hooks/session-heartbeat.sh` — PRIMARY liveness signal. Fires on `UserPromptSubmit` + `PreToolUse` wildcard. Atomic epoch write to `.cognitive-os/sessions/{id}/heartbeat`. Distinct from `state-heartbeat.sh` (crash recovery) and `agent_bus_metrics` (sub-agent watchdog).
- `hooks/session-watchdog-launcher.sh` — SessionStart singleton launcher (mirrors reaper-daemon-launcher pattern). mkdir-lock + pidfile guard with cmdline verification. Respects `COS_SESSION_WATCHDOG_DISABLE=1` opt-out.
- 39 new unit tests + 12 E2E smoke tests (zero daemon leaks verified).

### Added — Decision Depth Gate

- `rules/decision-depth-gate.md` — Q1-Q4 coherence analysis mandatory before closing "two values inconsistent" findings. Caught a real threshold bug (Phase A 1.0% vs Phase B 5.0% CPU — Phase A was under-predicting Phase B kills).
- `skills/invariant-check/` — scans ADR+lib pairs, emits pytest assertions for proposed invariants. On ADR-047 produces 7 invariants.
- `hooks/surface-fix-detector.sh` — PostToolUse advisory. Detects ~100% additive diffs with clarify/note trigger words.
- Cross-phase invariant test: Phase A threshold ≥ Phase B threshold (enforced in CI).

### Added — cos-config-audit validator

- `scripts/cos-config-audit.sh` — reports each cognitive-os.yaml section as IMPL / PARTIAL / ASPIR by checking component wiring. Data-driven CONTRACTS list.
- `# STATUS:` annotations on 9 cognitive-os.yaml sections (indent-aware parser).
- `--strict` flag — exits 1 on DRIFT (annotation vs runtime mismatch).
- `meta.settings_freshness` contract — detects `apply-efficiency-profile.sh` changes without settings regen.
- CI workflow `.github/workflows/cos-config-audit.yml` — weekly cron + PR-triggered + drift comment.
- Current snapshot: **8 IMPL / 0 PARTIAL / 2 ASPIR** (ttft_watchdog + engram_mcp intentionally Phase B scope).

### Added — Startup Protocol

- `rules/startup-protocol.md` + `hooks/session-startup-protocol.sh` — 5-step checklist (mem_search → plans↔ADRs → work-queue → validator → execute). Fires on SessionStart, 55ms, advisory only.

### Added — Cross-platform CI discipline

- `hooks/_lib/portable.sh` — BSD/GNU abstraction with Python3 fallback (date arithmetic, sed in-place, stat mtime, readlink, timeout, sha256).
- 17 hooks + scripts migrated off direct BSD-only invocations.
- `.github/workflows/cross-platform.yml` + `Dockerfile.ci-linux` — Linux CI smoke job prevents regressions.
- `scripts/shellcheck-baseline.txt` captures known-acceptable violations.

### Added — Startup baseline + ADR-044 Phase 2

- `scripts/startup-benchmark.sh` + SLO 10 (≤50k tokens core payload) and SLO 11 (TTFT p95 <5s) in `rules/so-slo.md`.
- ADR-044 Phase 2: 85 skills gained `summary_line` frontmatter (-270 tokens / -8% in `CATALOG-COMPACT.md`).
- 4 slash commands (`/engram-help`, `/sdd-help`, `/skills-search`, `/rules-expand`) for lazy-load on demand.

### Added — `cos-update` auto-regen + runtime daemons visibility

- `cos-update.sh` auto-regenerates `.claude/settings.json` when `apply-efficiency-profile.sh` changes (SHA-tracked at `.cognitive-os/state/apply-efficiency-profile.sha`). Mirrors `uv sync` pattern.
- `hooks/cognitive-os-health.sh` + `scripts/cos-status.sh` gain Daemons section (watchdog, reaper) with PID/uptime/cmdline-match verification.
- `hooks/context-watchdog.sh` REGISTERED (was an existing gap: rule said "NOT registered" — now fires on PostToolUse wildcard with 50/70/85% thresholds).

### Fixed

- 4 files with unresolved merge conflict markers: `hooks/self-install.sh`, `hooks/_lib/dispatch_gate_check.py`, `lib/agent_health_monitor.py`, `lib/dispatch_helper.py`. Resolved favoring "Stashed changes" side.
- `tests/unit/test_nemo_integration.py::test_skill_has_frontmatter` — tolerates leading `<!-- SCOPE: -->` comment (scope-governance convention).
- `tests/unit/test_repomix_integration.py::test_config_in_yaml` — tolerates documented section removal.
- Reconciliation: 20 plans in `.cognitive-os/plans/features/` mapped against ADRs. 11 SUPERSEDED / 4 LIVE / 3 STALE. Summary at `docs/architecture/plans-reconciliation-2026-04-21.md`.
- ADR-038 + ADR-039 published to canonical `docs/adrs/` (publication gap closed).
- ADR-003 duplicate deleted (wrong path). ADR-027a 4 PENDING items resolved. ADR-028a 6 PENDING items resolved (6 done, 2 deferred, 1 partial).
- work-queue.json rotated (44 completed entries to Engram, 3 stale parked removed).

### Metrics this release

- **22 commits** over one session.
- 6177 / 6209 tests pass (99.5%). 32 remaining failures are pre-existing (tracked in `docs/reports/pre-existing-test-failures-2026-04-21.md`).
- Engram observations added: 15+ under `adr-047/*`, `cos-config-audit/*`, `plans-reconciliation/*`, `decision-depth-gate/*`.

---

## [0.12.0] - 2026-04-20 — "SO Reliability Framework"

### Added — ADR-028 (full 6-pillar reliability framework)

- **D1.A Observability foundation**: `lib/metric_event.py` (canonical JSONL event schema with ENOSPC-safe `append_event` returning bool), `docs/reports/metrics-census.md` (F-1..F-8 surfaced), rotation by size (>1 MiB) + age (>7 d) in `hooks/metrics-rotation.sh`, archive path aligned.
- **D1.B Process registry + reaper**: `lib/process_registry.py` + `ProcessRegistry` facade (register/deregister/cleanup_expired/detect_orphans), `scripts/so-reaper.sh`, `hooks/session-end-reap.sh`. 8 real call sites via `hooks/_lib/register-bg.sh`. Safe-kill contract: only registered PIDs can be terminated.
- **D1.C Agent liveness (via agent_bus adapter, ADR-028b)**: `lib/agent_bus_metrics.py` bridges `cos:agent:*:heartbeat` events to MetricEvent JSONL. No parallel heartbeat system — builds on existing `lib/agent_bus.py`. Proven end-to-end with orchestrator smoke test (commit `ae84bb8`).
- **D1.D Unified dashboard**: `scripts/so-vitals.sh` (human + `--json` modes) aggregates agents, registered processes, orphan suspects, JSONL sizes, Valkey reachability. Consumed by chaos and contract tests.
- **D2 Contract test suite**: `tests/contracts/test_orphan_hooks.py` (130 hooks → 0 orphans), `test_fd_invariant.py`, `test_ram_ceiling.py`, `test_p95_hook_latency.py`. 4 real contracts, all behavioral.
- **D3 Systematic audit**: `docs/reports/hook-audit-2026-04.md` — 130 hooks scanned, 18 findings (2 BLOCKER, 9 CONCERN, 7 SUGGESTION) with anti-pattern taxonomy.
- **D4 Systematic fix**: 2/2 BLOCKERs + 9/9 CONCERNs resolved. `test-baseline-diff.sh` deleted (WS11 Bug-1 pattern). `mlflow-sync` + 5 other hooks wrapped in `timeout 30`. `rate-limit-protection.sh` reduced to deprecation shim of `token-budget-monitor.sh`.
- **D5 SLOs + runbook + killswitch**: `rules/so-slo.md` (9 SLOs + error budget), `docs/runbooks/so-incident-runbook.md`, `scripts/so-emergency-stop.sh`, `hooks/_lib/killswitch_check.sh` sourced by 124 of 129 hooks.
- **D6 Chaos suite**: `tests/chaos/` 5 scenarios (MCP kill, hook timeout, disk-full ENOSPC, FD exhaustion, git-reset cascade detector). All behavioral, 1 found a real gap and flipped to pass after D4 fix.

### Added — ADR-027 (SO slimming)

- **Phase 1**: `hooks/global-verify.sh` (PreToolUse/PostToolUse Agent, targeted test resolver + baseline/after diff), `lib/targeted_test_resolver.py` + `TargetedTestResolver` facade.
- **Phase 2**: `lib/ref_key_loader.py` — on-demand `[\`key\`]` → `rules/<key>.md` expansion with miss logging. Enables contextual rule inclusion.

### Added — ADR-029 (anti-reinvention gate)

- `hooks/reinvention-check.sh` wired at PreToolUse Agent. Grep-based similarity check against existing modules before sub-agent writes new file. Advisory in Phase A; hard-block at ≥0.7 similarity planned for Phase B.

### Added — Infrastructure

- `hooks/valkey-ensure.sh` auto-starts Valkey via OrbStack when `ORCHESTRATOR_MODE=executor`.
- `scripts/orchestrator.py` — dogfood entry point that uses `ClaudeExecutor` + `agent_bus_metrics` instead of the native Agent tool. Self-hosting loop proven (see `docs/reports/orchestrator-dogfood-smoke-test-2026-04-20.md`).
- 5 MetricEvent writer migrations (cost-events, consequence, skill-archive, telemetry, learning, singularity). 100% of cost-events rows migrated via `scripts/backfill-cost-events.py`.

### Changed

- `rules/RULES-COMPACT.md`: added `[\`so-slo\`]` ref-key on Infra line so ADR-028 SLO catalogue is loadable via the ref-key loader.
- `templates/agent-preamble.md`: 100 → 34 lines (trim). ~60% reduction in sub-agent context overhead (see `docs/reports/sub-agent-context-trim-2026-04-20.md`).
- `hooks/blast-radius.sh`: CRITICAL now requires `(INFRA AND SECURITY) OR file_score > 100` (was: `INFRA OR SECURITY OR file_score > 50`). Message compressed to one line.
- `hooks/inject-phase-context.sh`: gotchas dedup per session (first agent gets full text, subsequent get pointer).
- `hooks/_lib/task_panel_adapter.py`: skip tasks already in native Task panel (no more duplicate blocks).
- `lib/rate_limit_protection.py` → renamed to `lib/token_budget_monitor.py` (name collision with rate-limiter killed).

### Removed

- `lib/task_dag.py`, `lib/pipeline_executor.py`, `lib/workload_scheduler.py` — 65KB of dead code (`workflow-engine`), zero production callers.
- `hooks/test-baseline-diff.sh` — WS11 Bug-1 pattern (unbounded pytest at Stop).
- `lib/rate_limit_protection.py` + `hooks/rate-limit-protection.sh` reduced to deprecation shims.
- `valkey>=5.0` from `pyproject.toml` (redundant; `redis>=5.0.0` speaks the Valkey wire protocol).

### Fixed

- **F-4 SESSION_ID propagation**: `hooks/session-init.sh` now explicitly `export`s `COGNITIVE_OS_SESSION_ID` so 7 previously-invisible JSONL files (error-learning, repair-outcomes, remediation-registry, repair-queue, repair-dispatch, session-audit, singularity-events) can be written.
- **Singularity path**: `lib/singularity.py` `_SINGULARITY_LOG` was pointing to a dead `metrics/` directory; now writes to `.cognitive-os/metrics/`.
- **Hook registration sweep (debt register P1)**: `audit-id-enricher`, `auto-rollback-trigger`, `confidence-gate`, `confidentiality-enforcer`, `predev-completeness-check` registered (were on disk but never fired).
- **`metric_event.append_event` ENOSPC**: now returns `False` instead of raising, preventing cascading failures under disk pressure. `tests/chaos/test_disk_full_metrics.py` flipped from xfail to pass.
- **`scripts/so-vitals.sh` `cwd` bug**: `sys.path.insert(0, ".")` replaced with `"$PROJECT_DIR"` so the script works when invoked from outside the repo root.

### Documentation

- 4 new ADRs: `ADR-027a`, `ADR-028a`, `ADR-028b`, `ADR-029`.
- 9 audit / report documents under `docs/reports/` (metrics census, hook audit, debt register, artifact verification, reconciliation audit, smoke test, context trim, D1B TODO, validation).

### Dependencies

- `pyproject.toml` version bumped from `0.8.4` (stale — had not tracked releases since April 10) to `0.12.0` (aligned with tag).

## [Unreleased — superseded by 0.12.0] — UX1 + UX8 installer overhaul (ADR-002)

### Changed

- **BREAKING CHANGE (ADR-002)**: collapsed the 3-tier install profile system
  (`--lean` / `--standard` / `--full`) to 2 tiers:
  - `default` (no flag): 10 curated core skills + ~29 standard hooks + 14 core
    rules (~8000 tokens/session). Installed out of the box with no flag — the
    vanilla DX matches `git`, `gh`, and `claude`.
  - `--full`: every skill, hook, and rule (~142000 tokens/session). For mature
    projects and COS contributors.
- Legacy flags (`--lean`, `--standard`, `--minimal`) are now silently remapped
  to `default` with a stderr migration note — existing deployments continue to
  work without manual intervention.
- `install.sh`: new flag surface (`--full`, `--profile=NAME`, `--from`,
  `--force`, `--help`) with explicit ENV override (`COS_PROFILE`). Auto-detection
  removed; default is always `default`. Post-install summary now reports the
  number of skills exposed under `.claude/skills/` and warns on zero.
- `scripts/cos-init.sh`: accepts `--default` and `--full`; legacy flags
  silently map to `--default`. Skill install no longer gated behind non-minimal
  (both tiers ship skills). `DEFAULT_SKILLS` lists the 10 curated entries.
- `scripts/apply-efficiency-profile.sh`: 2-tier profile builder. The default
  tier now explicitly registers `auto-verify.sh`, `auto-refine.sh`,
  `dod-gate.sh`, `session-sanity.sh`, and `confidentiality-enforcer.sh`
  (PostToolUse Edit|Write) — the last fixes a regression where the enforcer
  had been dropped from the generated settings.
- `scripts/auto-update-projects.sh`: normalizes legacy registry `mode` values
  (`lean`, `standard`, `minimal`) to `default` before re-running `cos-init.sh`,
  so projects upgrade automatically on the next cascade.
- `scripts/generate-project-settings.sh`: `--default` is the canonical flag;
  legacy flags silently alias. `DEFAULT_HOOKS` now contains
  `confidentiality-enforcer.sh` and `session-sanity.sh`.
- `cognitive-os.yaml`: `efficiency.profile: default` and the `profiles:` map
  now defines only `default` and `full`.
- `docs/usage/cos-status.md`: references updated to the 2-tier model.

### Migration

Users who previously ran `install.sh --lean` or `install.sh --standard` should
drop the flag. The new `default` tier is a strict superset of the old `lean`
tier and the same hook set as the old `standard` tier plus 10 curated skills.
See `docs/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md`.

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
