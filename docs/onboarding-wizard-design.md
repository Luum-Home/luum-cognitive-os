# Onboarding Wizard Design

> Interactive TUI wizard for bootstrapping Cognitive OS in any project.
>
> Status: DESIGN | Updated: 2026-03-29

## Overview

The onboarding wizard replaces the current `scripts/cos-init.sh` (which accepts only `--minimal|--standard|--full`) with a comprehensive interactive TUI that detects the project environment, asks targeted questions, and generates a fully customized Cognitive OS installation. The wizard covers every configurable aspect of COS: 92 rules, 39 hooks, 94 skills, 26 packages, 21 Docker services, 6 package registries, and all `cognitive-os.yaml` settings.

## Design Goals

1. **Zero-knowledge start**: A user who has never seen COS should be able to install it in under 3 minutes
2. **Comprehensive but not overwhelming**: Present smart defaults based on detection; show advanced options only when asked
3. **Idempotent**: Running the wizard twice on the same project produces the same result (upgrade-safe)
4. **Reversible**: Every choice generates a config file; `cos uninstall` reverts everything
5. **Offline-capable**: All core installation works without network; package registry search is optional

## Relationship to Existing Scripts

| Script | Current Role | Post-Wizard Role |
|--------|-------------|------------------|
| `scripts/cos-init.sh` | Bootstrap with `--minimal\|--standard\|--full` | Backend called by wizard with generated config; retains CLI mode for non-interactive use |
| `scripts/set-security-profile.sh` | Switch hook profiles | Called by wizard during Phase 3; remains standalone |
| `scripts/apply-efficiency-profile.sh` | Switch efficiency profiles | Called by wizard during Phase 2; remains standalone |
| `scripts/install-pre-commit.sh` | Install git pre-commit hook | Called by wizard during Phase 7; remains standalone |
| `scripts/setup-git-hooks.sh` | Setup git hooks | Called by wizard during Phase 7; remains standalone |
| `scripts/install-aguara.sh` | Install aguara scanner | Called by wizard during Phase 4 if user opts in |
| `scripts/install-garak.sh` | Install garak scanner | Called by wizard during Phase 4 if user opts in |
| `scripts/install-mcp-scan.sh` | Install MCP scanner | Called by wizard during Phase 4 if user opts in |
| `scripts/install-promptfoo.sh` | Install promptfoo | Called by wizard during Phase 4 if user opts in |
| `scripts/install-tob-skills.sh` | Install Trail of Bits skills | Called by wizard during Phase 4 if user opts in |
| `scripts/upgrade.sh` | Upgrade COS version | Independent; wizard sets up auto-update hook |
| `scripts/uninstall.sh` | Remove COS from project | Independent; cleans up wizard output |

## TUI Library

**Recommendation: [bubbletea](https://github.com/charmbracelet/bubbletea) (Go)**

Rationale:
- COS already has Go tooling (garagon ecosystem: aguara, tero, mantis)
- bubbletea + [huh](https://github.com/charmbracelet/huh) provides form-based wizards with minimal code
- [lipgloss](https://github.com/charmbracelet/lipgloss) for styling
- Cross-platform (macOS, Linux, Windows)
- Active maintenance (Charm ecosystem)
- Compiles to a single binary: `cos setup` or `cos wizard`

Alternative for Python-only environments: [textual](https://github.com/Textualize/textual) (Python TUI framework).

Future: Web-based wizard via a local HTTP server serving a React/Svelte form that generates `cognitive-os.yaml`. Useful for team onboarding dashboards and SaaS product configuration.

---

## Wizard Phases

### Phase 1: Detection (automatic, no user input)

Runs silently on launch. Results displayed as a summary before questions begin.

#### What is detected

| Signal | Detection Method | Config Affected |
|--------|-----------------|-----------------|
| **Project language** | `go.mod` (Go), `package.json` (Node/TS), `pyproject.toml`/`requirements.txt`/`setup.py` (Python), `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin) | `project.stack`, quality gate commands |
| **Package manager** | `package-lock.json` (npm), `yarn.lock` (yarn), `bun.lockb` (bun), `pnpm-lock.yaml` (pnpm), `Pipfile.lock` (pipenv), `poetry.lock` (poetry), `uv.lock` (uv) | Test/build/lint commands in quality gates |
| **Existing .claude/** | Directory exists with `settings.json` or `settings.local.json` | Fresh install vs upgrade path; merge strategy |
| **Docker availability** | `command -v docker` + `docker info` | Phase 5 Docker services |
| **Docker Compose files** | `docker-compose.yml`, `docker-compose.yaml`, `compose.yml` | Infrastructure detection |
| **Git repository** | `.git/` directory exists | Required; wizard exits with error if missing |
| **CI/CD system** | `.github/workflows/` (GitHub Actions), `.gitlab-ci.yml` (GitLab), `Jenkinsfile`, `.circleci/` | Suggest CI integration, auto-update hooks |
| **Existing tests** | `pytest.ini`, `pyproject.toml [tool.pytest]`, `jest.config.*`, `vitest.config.*`, `*_test.go` files | Quality gate commands, coverage thresholds |
| **Test framework** | Jest/Vitest/Mocha (JS), pytest (Python), `go test` (Go), JUnit/TestNG (Java) | DoD verification commands |
| **Monorepo** | `workspaces` in package.json, `lerna.json`, `nx.json`, `turbo.json`, `go.work` | Multi-service awareness, scope detection |
| **Existing COS version** | `.cognitive-os/version`, `cognitive-os.yaml` | Upgrade vs fresh install |
| **Project name** | `package.json .name`, `go.mod module`, `pyproject.toml name`, directory name (fallback) | `project.name` |

#### Detection output

```
Cognitive OS Setup Wizard v0.2.1

  Detected environment:
    Project:    my-awesome-api
    Language:   Go (go.mod found)
    Tests:      go test (42 test files found)
    Docker:     Available (Docker 27.x)
    Git:        Clean working tree (main branch)
    CI:         GitHub Actions (3 workflows)
    COS:        Not installed (fresh setup)
```

---

### Phase 2: Core Configuration

These are the foundational choices that affect everything else.

#### 2.1 Install Scope

```
? Install scope:
  > Project only         Install rules/hooks in .claude/ (recommended for most projects)
    Global + Project     Universal rules in ~/.claude/, project-specific in .claude/
    Global only          User-wide defaults (for shared laptop/CI runner)
```

| Choice | Files Created | Who Uses This |
|--------|--------------|---------------|
| Project only | `.claude/rules/cos/`, `.claude/settings.json` | Single project, team collaborates via git |
| Global + Project | `~/.claude/rules/cos-global/` + `.claude/rules/cos/` | Developer who works on many projects |
| Global only | `~/.claude/rules/cos-global/`, `~/.claude/settings.json` | CI runners, shared environments |

**Default**: Project only

**What it affects**:
- Where rules are symlinked/copied
- Where `settings.json` hooks are registered
- Whether `cognitive-os.yaml` is per-project or global
- Merge behavior per Claude Code's 4-scope system (Managed > Local > Project > User)

#### 2.2 Project Phase

```
? Project phase:
    Reconstruction       Building/rebuilding. Max speed, min governance. Rewrite over patch.
  > Stabilization        Establishing standards. Balanced speed and governance.
    Production           Live system. Max governance, feature flags required.
    Maintenance          Bug fixes and security patches only. Minimal changes.
```

| Phase | Governance | Hook Behavior | Auto-Repair | HALT Scope |
|-------|-----------|---------------|-------------|------------|
| Reconstruction | Minimal | WARN on violations | Full autonomy | Data-destructive only |
| Stabilization | Balanced | WARN on violations | Full autonomy | + Cross-service |
| Production | Maximum | BLOCK on violations | Infra-only | All ambiguous tasks |
| Maintenance | Maximum | BLOCK on violations | Infra-only | All + non-trivial |

**Default**: Stabilization (safest general-purpose default)

**What it affects**:
- `cognitive-os.yaml -> project.phase`
- Hook enforcement severity (WARN vs BLOCK)
- Auto-repair scope (`auto_repair.phase_gates`)
- HALT triggers in closed-loop prompts
- DoD enforcement (WARNING vs BLOCK on missing criteria)
- Rate limit modifiers (reconstruction 1.5x, production 0.75x)

#### 2.3 Efficiency Profile

```
? Efficiency profile:
    Lean                 Minimum overhead (~6K tokens). For experienced users.
  > Standard             Balanced governance (~8K tokens). Recommended.
    Full                 Maximum observability (~142K tokens). For COS development.
```

| Profile | Rules Loaded | Hooks | Capability Level | Token Overhead |
|---------|-------------|-------|-----------------|----------------|
| Lean | RULES-COMPACT.md only | Minimal (10) | Level 4 | ~6K tokens |
| Standard | RULES-COMPACT.md + on-demand | Standard (20) | Level 3 | ~8K tokens |
| Full | All 92 rules | All (39+) | Level 2 | ~142K tokens |

**Default**: Standard

**What it affects**:
- `cognitive-os.yaml -> efficiency.profile`
- Which rules are loaded at session start vs on-demand
- Number of registered hooks
- Capability level (which safety nets auto-disable)
- Token budget per session

#### 2.4 Security Profile

```
? Security profile:
    Minimal              10 hooks. Fast development, error capture + secrets only.
  > Standard             20 hooks. Critical safety gates + quality checks.
    Paranoid             39+ hooks. Full safety mesh + external scanners.
```

| Profile | Hooks | Safety Mesh Layers | Overhead/Call | External Scanners |
|---------|-------|-------------------|---------------|-------------------|
| Minimal | 10 | 0/12 | ~100-200ms | None |
| Standard | 20 | 5/12 | ~300-500ms | None |
| Paranoid | 39+ | 12/12 | ~2-5s | Aguara, Semgrep, etc. |

**Default**: Standard

**What it affects**:
- `.claude/settings.json` hook registrations (via `scripts/set-security-profile.sh`)
- Which quality gates are active (clarification-gate, blast-radius, claim-validator, etc.)
- Whether external security scanners are triggered
- Content policy enforcement on writes
- Scope creep detection

#### 2.5 Model Capability Level

```
? Model capability level:
    Level 2: Good        All safety nets active. For less capable models.
  > Level 3: Excellent   Context management auto-disabled. For Claude Opus 4.6.
    Level 4: Autonomous  Multiple safety nets disabled. For highly capable models.
```

| Level | Auto-Disabled Components | Use Case |
|-------|------------------------|----------|
| 2 | None | Claude Sonnet, GPT-4o, weaker models |
| 3 | context-management | Claude Opus 4.6 (recommended) |
| 4 | + clarification-gate, assumption-tracking, confidence-gate, model-routing, blast-radius | Future autonomous agents |

**Default**: Level 3

**What it affects**:
- `cognitive-os.yaml -> model_capability.level`
- Which hooks self-disable at runtime regardless of registration
- Agent governance depth

---

### Phase 3: Feature Selection

Toggle features on/off. Organized into categories with smart defaults based on Phase 2 choices.

#### 3.1 Core Features

```
? Enable core features: (space to toggle, enter to confirm)
  [x] Engram persistent memory              Save decisions/bugs/discoveries across sessions
  [x] Error learning                         Auto-capture test/build/lint failures
  [x] Crash recovery                         Auto-checkpoint via git stash every 5min
  [x] Smart file reader                      Auto-pagination for files >40KB
  [x] Result truncation                      Limit large command output to 5K chars
  [x] User prompt capture                    Save user intent to memory for future sessions
```

**All on by default.** These are foundational features with negligible overhead.

| Feature | Config Key | Files Affected |
|---------|-----------|----------------|
| Engram persistent memory | `memory.provider: engram` | `cognitive-os.yaml` |
| Error learning | `hooks.error_learning: true` | `hooks/error-pipeline.sh` registered |
| Crash recovery | (always on in minimal+) | `hooks/auto-checkpoint.sh`, `hooks/crash-recovery.sh` |
| Smart file reader | (behavioral rule) | `rules/result-management.md` loaded |
| Result truncation | `resources.tokens.result_truncation.enabled` | Hook registered |
| User prompt capture | (behavioral rule) | `hooks/user-prompt-capture.sh` registered |

#### 3.2 Development Workflow Features

```
? Enable workflow features: (space to toggle)
  [x] SDD Pipeline                           Spec-Driven Development (propose/spec/design/tasks/apply/verify)
  [ ] Agent escalation protocol              Agents self-detect when stuck and escalate
  [x] Auto-refine loop                       Agents retry on failure (max 3 attempts)
  [ ] Cognitive load monitoring              Detect agent quality degradation over time
  [ ] Singularity autonomous loop            MAPE-K control loop for codebase health (advanced)
  [x] Plan-first protocol                    Require plans for medium+ tasks
```

| Feature | Config Key | Overhead | Dependencies |
|---------|-----------|----------|-------------|
| SDD Pipeline | SDD skills loaded | ~3K tokens per phase | Engram (for state persistence) |
| Agent escalation | `rules/agent-escalation.md` loaded | ~1K tokens | Closed-loop prompts |
| Auto-refine | `auto_refine.enabled: true` | ~200ms per agent completion | Error learning |
| Cognitive load | `rules/cognitive-load.md` loaded | ~500 tokens | Trust score |
| Singularity | `rules/singularity.md` loaded | Variable | Many (budget, error-learning, KPIs) |
| Plan-first | `rules/plan-first.md` loaded | ~500 tokens | None |

#### 3.3 Quality and Verification Features

```
? Enable quality features: (space to toggle)
  [x] Acceptance criteria enforcement        Every agent prompt must include verifiable criteria
  [x] Definition of Done gates              5 DoD levels (trivial/small/medium/large/critical)
  [x] Trust score reporting                  Agents report confidence with evidence
  [ ] Adversarial review protocol            Reviews must produce at least one finding
  [ ] Assumption tracking                    Detect when agents make assumptions vs verified facts
  [ ] Broken window policy                   Fix pre-existing issues when discovered
```

| Feature | Config Key | Overhead |
|---------|-----------|----------|
| Acceptance criteria | `quality.auto_verify: true` | ~500ms on agent completion |
| DoD gates | `definition_of_done.*` | ~200ms on completion |
| Trust score | `rules/trust-score.md` loaded | ~500 tokens per report |
| Adversarial review | `rules/adversarial-review.md` loaded | ~500 tokens |
| Assumption tracking | Hook: `assumption-tracker.sh` | ~100ms per agent completion |
| Broken window | `rules/broken-window-policy.md` loaded | ~300 tokens |

#### 3.4 Agent Governance Features

```
? Enable agent governance: (space to toggle)
  [ ] Agent Teams (experimental)             Lateral teammate communication between agents
  [ ] Agent Bus (Valkey pub/sub)             Real-time heartbeat and progress tracking
  [ ] Agent KPIs                             Track agent performance metrics and OKRs
  [ ] Squad protocol                         Team-based agent organization and evaluation
  [ ] Agent customization overrides          Per-agent model/tool/budget overrides
```

| Feature | Config Key | Dependencies |
|---------|-----------|-------------|
| Agent Teams | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in env | Claude Code experimental flag |
| Agent Bus | `AGENT_BUS_ENABLED=true` | Valkey Docker service |
| Agent KPIs | `rules/agent-kpis.md` loaded | Skill metrics, error learning |
| Squad protocol | `rules/squad-protocol.md` loaded | Agent KPIs, Paperclip |
| Agent customization | `.cognitive-os/customizations/` directory | Agent definitions |

---

### Phase 4: Security Tools (optional external tools)

Only shown if security profile is Standard or Paranoid.

```
? Install security tools: (space to toggle, all optional)
  [ ] Aguara                 Deterministic AI agent scanner (189 rules, 14 categories) [Go]
  [ ] Semgrep + AI rules     SAST for generated code (58 AI-specific rules) [Python]
  [ ] MCP-Scan               MCP server configuration scanner [Python/Node]
  [ ] Promptfoo              Red team testing for agent prompts [Node]
  [ ] Garak                  LLM vulnerability scanner (179 probes) [Python]
  [ ] Trail of Bits skills   62 professional security audit skills [Git submodule]
  [ ] Parry Guard            ML-based prompt injection detection [Rust]
```

| Tool | Install Command | Size | Config Key |
|------|----------------|------|-----------|
| Aguara | `go install github.com/garagon/aguara@latest` | ~15MB | `security.aguara.enabled: true` |
| Semgrep | `pip install semgrep` or `brew install semgrep` | ~200MB | `SEMGREP_ENABLED=true` |
| MCP-Scan | `pip install mcp-scan` | ~50MB | `security.mcp_scan.enabled: true` |
| Promptfoo | `npm install -g promptfoo` | ~100MB | `security.promptfoo.enabled: true` |
| Garak | `pip install garak` | ~500MB | N/A (CLI tool) |
| Trail of Bits | `bash scripts/install-tob-skills.sh` | ~5MB | Git submodule |
| Parry Guard | `brew install vaporif/tap/parry-guard` | ~50MB | `security.parry.enabled: true` |

**What it affects**:
- Runs install scripts for selected tools
- Updates `cognitive-os.yaml` security section
- Registers additional hooks in `.claude/settings.json` (aguara-scan, semgrep-scan, mcp-scan)
- For Trail of Bits: clones git submodule to `.claude/plugins/trailofbits-skills/`

**Graceful degradation**: All tools are optional. If a tool is not installed, its hook silently exits (exit 0). The wizard shows install progress but does not fail if a tool install fails.

---

### Phase 5: Infrastructure (Docker services)

Only shown if Docker was detected in Phase 1.

```
? Docker services to enable: (space to toggle)
  [ ] Langfuse              LLM observability, tracing, and metrics
  [ ] LiteLLM               Model routing proxy (multi-provider)
  [ ] Bifrost               High-performance AI gateway
  [ ] NeMo Guardrails       Content safety and PII detection
  [ ] Valkey                Agent Bus communication (Redis-compatible)
  [ ] Paperclip             Governance and compliance dashboard
  [ ] Jupyter               Notebook environment for data analysis
  [ ] Opik                  LLM tracing backend (alternative to Langfuse)
  [ ] Cognee                Knowledge graph and RAG engine
  [ ] Memu                  Cross-session memory sync service
  [ ] Automaker             UI automation service
  [ ] Webhook Trigger       Event-driven automation listener
```

| Service | Docker Profile | Dependencies | Port |
|---------|---------------|-------------|------|
| Langfuse | default | langfuse-pg, langfuse-valkey, langfuse-clickhouse, langfuse-seaweedfs, langfuse-worker | 3100 |
| LiteLLM | default | (standalone) | 4000 |
| Bifrost | default | (standalone) | 8081 |
| NeMo Guardrails | default | (standalone) | 8000 |
| Valkey | default | (standalone) | 6379 |
| Paperclip | default | paperclip-pg | 3200 |
| Jupyter | default | (standalone) | 8888 |
| Opik | observability | opik-mysql, opik-frontend | 5173 |
| Cognee | memory | (standalone) | 8003 |
| Memu | memory | (standalone) | 8765 |
| Automaker | ui | (standalone) | 3050 |
| Webhook Trigger | automation | (standalone) | 9090 |

```
? Smart Start: Auto-start services when a skill needs them? [Y/n]
  (Services start on-demand and stop after idle timeout)
```

**Default**: Smart Start enabled, no services pre-selected.

**What it affects**:
- `cognitive-os.yaml -> resources.infrastructure.services` (mode: on_demand vs always)
- `cognitive-os.yaml -> resources.infrastructure.smart_start: true`
- Docker Compose profile selection
- Skill-to-service mapping in config

---

### Phase 6: Package Registries

Configure where `cos search` and `cos install` look for packages.

```
? Package registries: (space to toggle)
  [x] cos-official          GitHub topic: cos-package (curated COS packages)
  [x] luum-org              GitHub org: Luum-Home (first-party packages)
  [ ] garagon-tools          GitHub org: garagon (security scanners)
  [ ] antigravity-skills     1,331+ community skills (large, opt-in)
  [ ] trail-of-bits          Security audit skills (62 skills)
  [x] local                  ~/.cognitive-os/local-packages/ (your own packages)
```

```
? External skill sources: (space to toggle)
  [x] cos-builtin           Built-in COS agentic primitives
  [x] skills.sh             Vercel's agent skills registry (83K+ skills)
  [x] MCP Registry          Official MCP server registry
  [ ] SkillsMP              Community skills marketplace (350K+ skills)
```

**Default**: cos-official, luum-org, local, cos-builtin, skills.sh, MCP Registry.

**What it affects**:
- `cognitive-os.yaml -> packages.registries` list
- `cognitive-os.yaml -> sources.registries` list
- Which results appear in `cos search`

---

### Phase 7: Git Integration and Auto-Update

```
? Git integration: (space to toggle)
  [x] Pre-commit gate       Block commits on test failure, warn on coverage <80%
  [x] Auto-update on pull   Sync COS updates when you pull the repo
  [ ] Post-merge hook        Run cos upgrade after git merge
```

| Feature | What It Does | Script |
|---------|-------------|--------|
| Pre-commit gate | Runs tests before commit; blocks on failure | `scripts/install-pre-commit.sh` |
| Auto-update on pull | Post-merge hook triggers `scripts/upgrade.sh` | `scripts/setup-git-hooks.sh` |
| Post-merge hook | Runs `cos upgrade` after merging | `scripts/auto-update-projects.sh` |

**Default**: Pre-commit gate and auto-update enabled.

**What it affects**:
- `.git/hooks/pre-commit` symlinked to `hooks/pre-commit-gate.sh`
- `.git/hooks/post-merge` created to run upgrade
- `COVERAGE_THRESHOLD` environment variable set

---

### Phase 8: Budget and Resource Limits

```
? Resource limits:
  Monthly budget cap (USD):    [200]
  Daily alert threshold (USD): [10]
  Per-session target (USD):    [0.50]
  Max parallel agents:         [5]
  Agent timeout (seconds):     [300]
```

**Defaults**: As shown (from current `cognitive-os.yaml`).

**What it affects**:
- `cognitive-os.yaml -> resources.budget.*`
- `cognitive-os.yaml -> resources.compute.*`
- Model downgrade chain behavior
- Rate limit thresholds

---

### Phase 9: Project-Specific Configuration

Dynamic phase based on detected language from Phase 1.

#### For Go projects:

```
? Go configuration:
  Build command:    [go build ./...]
  Test command:     [go test ./...]
  Lint command:     [golangci-lint run ./...]
  Coverage command: [go test -coverprofile=coverage.out ./...]
```

#### For Node/TypeScript projects:

```
? Node configuration:
  Package manager:  (auto-detected: yarn)
  Build command:    [yarn build]
  Test command:     [yarn test]
  Lint command:     [yarn lint]
  Coverage command: [yarn test --coverage]
```

#### For Python projects:

```
? Python configuration:
  Package manager:  (auto-detected: poetry)
  Test command:     [pytest]
  Lint command:     [ruff check .]
  Coverage command: [pytest --cov]
```

#### For Rust projects:

```
? Rust configuration:
  Build command:    [cargo build]
  Test command:     [cargo test]
  Lint command:     [cargo clippy]
```

**What it affects**:
- `cognitive-os.yaml -> quality.gates` array (build/test/lint/coverage commands)
- Quality gate verification commands used by agents
- Pre-commit hook test command
- DoD verification commands

---

### Phase 10: Summary and Install

#### Summary Display

```
  Cognitive OS v0.2.1 Installation Summary

  CORE
    Scope:           Project only
    Phase:           Stabilization
    Efficiency:      Standard (compact rules + 20 hooks)
    Security:        Standard (5/12 safety mesh layers)
    Capability:      Level 3 (Excellent - Claude Opus 4.6)

  COMPONENTS
    Rules:           14 always-loaded + 78 on-demand = 92 available
    Hooks:           20 registered (standard profile)
    Skills:          55 project + 8 both = 63 available
    Packages:        26 optional packages (install with cos install)

  FEATURES
    Core:            Engram, Error Learning, Crash Recovery, Smart Reader,
                     Result Truncation, User Prompt Capture
    Workflow:        SDD Pipeline, Auto-Refine, Plan-First
    Quality:         Acceptance Criteria, DoD Gates, Trust Score
    Governance:      (none selected)

  SECURITY TOOLS
    (none selected - install later with cos install @luum/aguara-security)

  DOCKER SERVICES
    Smart Start:     Enabled (services start on-demand)
    Pre-selected:    None

  REGISTRIES
    Packages:        cos-official, luum-org, local
    Sources:         cos-builtin, skills.sh, MCP Registry

  GIT INTEGRATION
    Pre-commit:      Enabled (block on test failure)
    Auto-update:     Enabled (sync on pull)

  RESOURCES
    Monthly budget:  $200.00
    Daily alert:     $10.00
    Max agents:      5 parallel

  ESTIMATED OVERHEAD
    Token overhead:  ~20K tokens at session start (2% of 1M context window)
    Hook overhead:   ~300-500ms per tool call

  ? Proceed with installation? [Y/n]
```

#### Installation Steps

On confirmation, the wizard executes in order:

```
Installing Cognitive OS v0.2.1...

  [1/12] Creating directory structure
         .claude/rules/cos/
         .claude/commands/
         .cognitive-os/metrics/
         .cognitive-os/sessions/
         .cognitive-os/tasks/
         .cognitive-os/templates/

  [2/12] Installing rules (14 core + RULES-COMPACT.md)
         Copied 15 rule files to .claude/rules/cos/

  [3/12] Installing hooks (20 standard profile)
         Registered 20 hooks in .claude/settings.json

  [4/12] Installing skills (63 available)
         Copied CATALOG.md + 19 core skills
         Package skills available via cos install

  [5/12] Installing templates
         Copied 4 templates to .cognitive-os/templates/

  [6/12] Generating cognitive-os.yaml
         Project: my-awesome-api
         Phase: stabilization
         Stack: go

  [7/12] Configuring quality gates
         Build:    go build ./...
         Test:     go test ./...
         Lint:     golangci-lint run ./...
         Coverage: go test -coverprofile=coverage.out ./...

  [8/12] Setting security profile (standard)
         Backed up existing settings.json

  [9/12] Installing git hooks
         Pre-commit gate: .git/hooks/pre-commit
         Auto-update: .git/hooks/post-merge

  [10/12] Installing security tools
          (none selected)

  [11/12] Configuring Docker services
          Smart Start enabled (no pre-start)

  [12/12] Registering in COS registry
          Updated ~/.cognitive-os/projects.json

  Done! Cognitive OS v0.2.1 installed.

  Quick start:
    cos status        Check installation health
    cos search        Find packages to install
    /scout            Explore your codebase
    /run-tests        Run your test suite
    /sdd-new          Start a new feature with SDD

  Documentation: https://github.com/Luum-Home/luum-agent-os/docs/getting-started.md
```

---

## Files Created/Modified

### Always created

| File | Purpose |
|------|---------|
| `cognitive-os.yaml` | Single source of truth for COS configuration |
| `.claude/rules/cos/RULES-COMPACT.md` | Compressed rule index (always loaded) |
| `.claude/rules/cos/*.md` | Individual rule files (count depends on profile) |
| `.claude/settings.json` | Hook registrations (merged with existing if present) |
| `.cognitive-os/metrics/` | Directory for metrics JSONL files |
| `.cognitive-os/sessions/` | Directory for session isolation |
| `.cognitive-os/tasks/` | Directory for task tracking |
| `.cognitive-os/version` | Installed COS version |

### Conditionally created

| File | Condition |
|------|-----------|
| `.cognitive-os/templates/*.md` | Standard or Full profile |
| `.cognitive-os/skills/CATALOG.md` | Standard or Full profile |
| `.cognitive-os/skills/*/SKILL.md` | Standard or Full profile |
| `.cognitive-os/hooks/*.sh` | Hook files for registered hooks |
| `.cognitive-os/hooks/_lib/` | Hook utility library |
| `.git/hooks/pre-commit` | Pre-commit gate enabled |
| `.git/hooks/post-merge` | Auto-update enabled |
| `~/.claude/rules/cos-global/` | Global scope selected |
| `~/.cognitive-os/projects.json` | Project registry entry |

### Modified (merged)

| File | Merge Strategy |
|------|---------------|
| `.claude/settings.json` | Deep merge hooks; preserve existing env/permissions |
| `.gitignore` | Append `.cognitive-os/sessions/`, `.cognitive-os/rate-limit-state.json`, `.cognitive-os/checkpoints/` |

---

## Configuration Mapping

### Phase 2 choices to cognitive-os.yaml

| Wizard Choice | YAML Path | Values |
|---------------|-----------|--------|
| Install scope | N/A (affects file placement) | project, global+project, global |
| Project phase | `project.phase` | reconstruction, stabilization, production, maintenance |
| Efficiency profile | `efficiency.profile` | lean, standard, full |
| Security profile | N/A (affects settings.json) | minimal, standard, paranoid |
| Capability level | `model_capability.level` | 2, 3, 4 |

### Phase 3 features to cognitive-os.yaml

| Feature | YAML Path |
|---------|-----------|
| Engram | `memory.provider: engram` |
| Error learning | `hooks.error_learning: true` |
| Crash recovery | (always on) |
| Smart reader | `resources.tokens.result_truncation.enabled: true` |
| User prompt capture | (behavioral rule) |
| SDD Pipeline | SDD skills installed |
| Agent escalation | `rules/agent-escalation.md` installed |
| Auto-refine | `auto_refine.enabled: true` |
| Cognitive load | `rules/cognitive-load.md` installed |
| Singularity | `rules/singularity.md` installed |
| Plan-first | `rules/plan-first.md` installed |
| Acceptance criteria | `quality.auto_verify: true` |
| DoD gates | `/dod-check` skill (config flag removed) |
| Trust score | `rules/trust-score.md` installed |
| Adversarial review | `rules/adversarial-review.md` installed |
| Assumption tracking | Hook registered |
| Broken window | `rules/broken-window-policy.md` installed |
| Agent Teams | `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` |
| Agent Bus | `AGENT_BUS_ENABLED: true` in env |
| Agent KPIs | `rules/agent-kpis.md` installed |
| Squad protocol | `rules/squad-protocol.md` installed |
| Agent customization | `.cognitive-os/customizations/` created |

### Phase 5 Docker services to cognitive-os.yaml

| Service | YAML Path | Mode |
|---------|-----------|------|
| Any selected | `resources.infrastructure.services.{name}.mode` | `on_demand` or `always` |
| Smart Start | `resources.infrastructure.smart_start` | `true` or `false` |

### Phase 8 budgets to cognitive-os.yaml

| Setting | YAML Path |
|---------|-----------|
| Monthly limit | `resources.budget.monthly_limit_usd` |
| Daily alert | `resources.budget.daily_alert_usd` |
| Per-session target | `resources.budget.per_session_target_usd` |
| Max parallel agents | `resources.compute.max_parallel_agents` |
| Agent timeout | `resources.compute.agent_timeout_seconds` |

---

## Preset Configurations

For users who want a one-click setup, offer presets that skip interactive questions:

| Preset | Phase | Efficiency | Security | Features | Use Case |
|--------|-------|-----------|----------|----------|----------|
| `--solo-dev` | Reconstruction | Lean | Minimal | Core only | Solo developer, speed first |
| `--team` | Stabilization | Standard | Standard | Core + SDD + Quality | Team project, balanced |
| `--enterprise` | Production | Standard | Paranoid | All features | Enterprise, compliance |
| `--ci` | Production | Lean | Standard | Core + Quality | CI/CD runner |
| `--learning` | Reconstruction | Full | Standard | All features | Learning COS, see everything |

Usage: `cos setup --preset team` skips the wizard and applies the preset.

---

## Upgrade Path

When the wizard detects an existing COS installation:

```
  Detected: Cognitive OS v0.2.0 installed (upgrade available: v0.2.1)

  ? Upgrade action:
    > Upgrade in-place       Keep your config, update components
      Reconfigure            Re-run wizard with current config as defaults
      Fresh install          Remove existing and start over
```

Upgrade in-place:
1. Read existing `cognitive-os.yaml`
2. Merge new defaults (add new keys, preserve existing values)
3. Update rules/hooks/skills to new versions
4. Preserve customizations in `.cognitive-os/customizations/`
5. Run `scripts/upgrade.sh` for version-specific migrations

---

## Non-Interactive Mode

For CI/CD and scripting:

```bash
# Use preset
cos setup --preset team --non-interactive

# Use config file
cos setup --config cos-setup.yaml --non-interactive

# Use individual flags
cos setup --phase production --security paranoid --capability 3 --non-interactive
```

The `cos-setup.yaml` file mirrors wizard choices:

```yaml
scope: project
phase: stabilization
efficiency: standard
security: standard
capability_level: 3
features:
  engram: true
  sdd_pipeline: true
  auto_refine: true
  plan_first: true
  acceptance_criteria: true
  # dod_gates: removed (use /dod-check skill instead)
  trust_score: true
security_tools: []
docker_services: []
smart_start: true
registries:
  - cos-official
  - luum-org
  - local
git:
  pre_commit: true
  auto_update: true
budget:
  monthly_limit_usd: 200
  daily_alert_usd: 10
```

---

## Error Handling

| Error | Wizard Behavior |
|-------|----------------|
| Not a git repo | Exit with error: "COS requires a git repository. Run git init first." |
| No write permission | Exit with error: "Cannot write to .claude/. Check permissions." |
| Docker not available | Skip Phase 5, note in summary |
| Tool install fails | Warn but continue; note in summary |
| Existing config conflict | Show diff, ask user to merge or overwrite |
| Network unavailable | Skip registry validation, proceed with local install |

---

## Future Enhancements

1. **Web-based wizard**: Local HTTP server with React/Svelte UI for team onboarding
2. **`cos doctor`**: Post-install health check that validates the configuration
3. **Profile export/import**: Share team configurations via `cos-setup.yaml`
4. **Plugin marketplace**: Browse and install packages directly from the wizard
5. **Guided tour**: Post-install interactive walkthrough of key features
6. **Telemetry opt-in**: Anonymous usage data to improve defaults
7. **IDE integration**: VS Code extension that triggers the wizard on project open
