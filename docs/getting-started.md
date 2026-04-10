# Getting Started with Cognitive OS

> From zero to a fully managed AI agent operating system in your project.

---

## Prerequisites

| Requirement | Minimum Version | Purpose |
|-------------|----------------|---------|
| **Claude Code** | Latest | AI agent CLI (the runtime) |
| **Python** | 3.9+ | Library modules, test suite, singularity controller |
| **Go** | 1.21+ | TUI test runner (`cmd/cos-test`) |
| **Docker** | 24+ | Testcontainers, optional infrastructure services |
| **Git** | 2.30+ | Worktree isolation, version control |
| **gh CLI** | 2.0+ | GitHub integration (issues, PRs, webhooks) |
| **uv** | 0.1+ | Python package management (recommended over pip) |

Optional but recommended:

| Tool | Purpose |
|------|---------|
| **devbox** | Reproducible development environment |
| **jq** | JSON processing in hooks |

---

## Installation

> **Important**: The installer installs into the **current working directory**.
> Always `cd` into your project first, then run the installer.

### In a new project

```bash
# cd into YOUR PROJECT first
cd /path/to/your/project

# Option 1: Remote install (from GitHub)
curl -fsSL https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/install.sh | bash

# Option 2: Local install (from a cloned Cognitive OS repo)
/path/to/luum-agent-os/install.sh
```

Or manually:

```bash
git clone --depth 1 https://github.com/luum-home/luum-cognitive-os.git /tmp/cos
cp -r /tmp/cos/.cognitive-os .cognitive-os
cp /tmp/cos/cognitive-os.yaml cognitive-os.yaml
rm -rf /tmp/cos
```

### About the `--from` flag

The `--from PATH` flag tells the installer where the Cognitive OS source code is.
You only need it if the `install.sh` script was downloaded separately (not inside the repo).
When running the script directly from the repo, source detection is automatic.

### Coexistence with existing .claude/ config

Cognitive OS is designed to coexist safely with your project's existing `.claude/` configuration:

- **Rules are namespaced**: COS rules install to `.claude/rules/cos/`, not `.claude/rules/`. Your project-specific rules in `.claude/rules/*.md` are never touched.
- **Settings are merged**: If `.claude/settings.json` already exists, the installer merges COS hooks into your existing hook arrays without removing your hooks. Requires `jq`.
- **Your CLAUDE.md is preserved**: COS never overwrites `.claude/CLAUDE.md`.

```
.claude/
  rules/
    architecture.md          <-- your project rule (untouched)
    testing-conventions.md   <-- your project rule (untouched)
    cos/                     <-- COS rules (namespaced)
      trust-score.md
      cost-tracking.md
      license-policy.md
      ...
  settings.json              <-- merged: your hooks + COS hooks
  CLAUDE.md                  <-- yours (untouched)
```

To uninstall COS without affecting your project config:
1. Remove `.cognitive-os/` directory
2. Remove `.claude/rules/cos/` directory
3. Remove COS hook entries from `.claude/settings.json` (they reference `$CLAUDE_PROJECT_DIR/hooks/`)

### First run

```bash
# Open Claude Code
claude

# Initialize Cognitive OS for your project
/cognitive-os-init
```

The `/cognitive-os-init` skill:
1. Reads your project stack (package.json, go.mod, docker-compose.yml, Cargo.toml, etc.)
2. Auto-detects languages, frameworks, and infrastructure
3. Generates `.claude/rules/` with project-specific architecture rules
4. Merges `.claude/settings.json` with hook registrations (preserves existing hooks)
5. Updates `cognitive-os.yaml` with detected infrastructure
6. Saves a `detected-stack.json` for the skill auto-loader

### Optional: Start infrastructure services

Use the bootstrap script for a fully automated one-command setup:

```bash
bash scripts/cos-bootstrap.sh
```

This single command:
1. Creates `.env` from `env.example` (or merges new vars into your existing `.env`)
2. Generates `LANGFUSE_ENCRYPTION_KEY` if not set
3. Creates the `cognitive-os-network` Docker network
4. Starts Docker services based on the chosen profile
5. Waits for health checks to pass
6. Provisions Langfuse API keys automatically
7. Syncs rules and hooks symlinks
8. Creates the `.cognitive-os/` directory structure

#### Profiles

| Profile | Services | Use when |
|---------|----------|----------|
| `minimal` | Langfuse stack (6 containers) | Low resource usage, observability only |
| `standard` | Langfuse + LiteLLM (default) | Recommended — cost control + observability |
| `full` | All services | Complete stack including Paperclip, Jupyter |

```bash
bash scripts/cos-bootstrap.sh --profile minimal   # lightweight
bash scripts/cos-bootstrap.sh --profile standard  # recommended (default)
bash scripts/cos-bootstrap.sh --profile full      # everything
bash scripts/cos-bootstrap.sh --dry-run           # preview without changes
```

The bootstrap script is **idempotent** — safe to run multiple times.

Services started by the standard profile:
- **Langfuse** (port 3100): Observability and tracing
- **LiteLLM** (port 4000): Cost control and model routing

Additional services available in the `full` profile:
- **NeMo Guardrails** (port 8088): Content safety
- **Paperclip** (port 3200): Governance dashboard
- **Jupyter** (port 8888): GPU/compute sandbox

These are optional. Cognitive OS works without them — they add observability and cost control.

#### Updating an existing installation

**Automatic updates (recommended):**

When you update the Cognitive OS source repo (`git pull` or `git push`), all
registered projects are updated automatically via git hooks:

- `git pull` triggers the `post-merge` hook — runs synchronously, projects are
  updated before you get your prompt back
- `git push` triggers the `pre-push` hook — runs in background after the push
  completes (2s delay), so the push is not delayed and projects get the version
  that was just pushed

Both hooks run `scripts/auto-update-projects.sh`, which:
1. Reads `~/.cognitive-os/installations.json` (the global registry)
2. Finds projects installed from this specific COS repo
3. Re-runs `cos-init.sh` with each project's original mode (minimal/standard/full)
4. Updates rules, hooks, skills, and templates without touching project-specific files

To install the git hooks (one-time setup):
```bash
bash scripts/setup-git-hooks.sh
```

**Manual update of a single project:**

```bash
cd /path/to/your-project
/path/to/luum-agent-os/install.sh --force
```

**Infrastructure update (Docker services):**

```bash
bash scripts/cos-update.sh
bash scripts/cos-update.sh --pull-images   # also pull latest Docker images
```

The infrastructure update merges new `.env` variables (never overwriting existing
values), restarts changed containers, and re-syncs rules and hooks.

#### How the project registry works

Every installation is registered in `~/.cognitive-os/installations.json` with:
- The project path and name
- The install mode (minimal/standard/full)
- The COS source repo path (for auto-update matching)
- The version at install time

View registered projects:
```bash
bash scripts/cos-registry.sh list
```

Clean up stale entries (projects that no longer exist on disk):
```bash
bash scripts/cos-registry.sh cleanup
```

---

## What Happens at Session Start

Every time you open Claude Code in a Cognitive OS project, the following hooks fire automatically:

```
SessionStart
    |
    +-- self-install.sh          Sync rules/hooks to .claude/ (dogfooding)
    +-- session-init.sh          Create session ID, register in active-sessions.json
    +-- session-resume.sh        Check for incomplete tasks from previous sessions
    +-- stack-detector.sh        Detect project languages and frameworks
    +-- inject-phase-context.sh  Load phase-specific rules (reconstruction/production/etc.)
    +-- engram-auto-import.sh    Load persistent memory from Engram
```

You will see a status line indicating the health of the installation:
```
Self-hosting: OK (55 rules, 57 hooks synced)
```

---

## Your First SDD Pipeline

SDD (Spec-Driven Development) is the structured pipeline for substantial changes. Here is a walkthrough:

### 1. Start a new change

```
/sdd-new add-user-authentication
```

This runs two phases:
- **Explore**: Analyzes the codebase to understand current state
- **Propose**: Generates a formal proposal with scope, risks, and approach

### 2. Continue the pipeline

```
/sdd-continue add-user-authentication
```

Each invocation runs the next phase in the dependency chain:

```
explore -> propose -> spec -> design -> tasks -> apply -> verify -> archive
```

### 3. Fast-forward (skip to implementation)

```
/sdd-ff add-user-authentication
```

Runs all planning phases in sequence: propose -> spec -> design -> tasks.

### 4. Apply the implementation

```
/sdd-apply add-user-authentication
```

Launches a sub-agent that reads the task breakdown and implements each task.

### 5. Verify

```
/sdd-verify add-user-authentication
```

Runs adversarial review against the spec. If CRITICAL issues are found, the verify-apply loop retries up to 3 times.

### 6. Archive

```
/sdd-archive add-user-authentication
```

Creates a permanent record of the change with lessons learned.

### Resume after interruption

If a session crashes or you close it mid-pipeline:

```
/sdd-continue add-user-authentication
```

The state is stored in Engram. It loads the last completed phase and continues from there.

---

## Running Tests

### Unified test runner (recommended)

```bash
bash scripts/test-all.sh              # Full suite: unit (parallel) + integration + bash
bash scripts/test-all.sh --unit       # Unit tests only (~30s with xdist)
bash scripts/test-all.sh --no-docker  # Skip Docker-dependent tests
bash scripts/test-all.sh --parallel 8 # Force 8 parallel workers
bash scripts/test-all.sh -v           # Verbose output
```

The unified runner uses `pytest-xdist` for parallel unit test execution (auto-detects CPUs),
runs integration tests sequentially (Docker containers), and finishes with bash layer tests.

### Python test suite (direct pytest)

```bash
# Full suite (3500+ tests)
python3 -m pytest tests/ -n auto      # Parallel with xdist

# By layer
python3 -m pytest tests/unit/ -n auto         # Fast, parallel, no dependencies
python3 -m pytest tests/integration/ -v       # Requires Docker (testcontainers)
python3 -m pytest tests/behavior/ -v          # Simulates hook behavior
python3 -m pytest tests/system/ -v            # End-to-end pipelines

# Single file
python3 -m pytest tests/unit/test_record_completion.py -v
```

### Infrastructure tests (bash, fast)

```bash
bash tests/infra/test-hooks.sh    # Hook existence, permissions, syntax
bash tests/infra/test-skills.sh   # Skill structure, catalog sync
bash tests/infra/test-rules.sh    # Rule existence, RULES-COMPACT sync
bash tests/infra/test-config.sh   # YAML validation
```

### From within Claude Code

```
/cognitive-os-test
```

This skill runs the full test suite and reports results.

---

## Setting Up Notifications

Cognitive OS can send notifications via Telegram, Slack, or generic webhooks when pipelines complete, errors occur, or issues are processed.

### Telegram

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Set environment variables:

```bash
export NOTIFY_PROVIDER=telegram
export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
export TELEGRAM_CHAT_ID=123456789
```

### Slack

1. Create an incoming webhook in your Slack workspace
2. Set environment variables:

```bash
export NOTIFY_PROVIDER=slack
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

### Generic webhook

```bash
export NOTIFY_PROVIDER=webhook
export WEBHOOK_URL=https://your-endpoint.com/notify
```

Notifications are sent as JSON POST requests. The `notify.sh` hook and `lib/notifications.py` module handle delivery.

---

## Key Concepts

### Concept Map

```
                    cognitive-os.yaml
                         |
              +----------+----------+
              |          |          |
           HOOKS      RULES      SKILLS
         (runtime)  (contracts)  (knowledge)
              |          |          |
              +----+-----+----+----+
                   |          |
                ENGRAM     METRICS
              (memory)    (data)
                   |          |
              SINGULARITY CONTROLLER
              (autonomous loop)
```

### Hooks

Hooks intercept every tool call in Claude Code. They fire at four lifecycle points:

| Point | When | Examples |
|-------|------|---------|
| `SessionStart` | When Claude Code opens | session-init, stack-detector, session-resume |
| `PreToolUse` | Before any tool runs | error-pattern-detector, completeness-check |
| `PostToolUse` | After any tool runs | error-learning, auto-verify, skill-tracker |
| `Stop` | When session ends | session-cleanup, kpi-trigger |

Hooks are bash scripts that run in <100ms and have zero dependencies.

### Rules

Rules are always-on behavioral contracts. They constrain agent behavior across all sessions. Examples:

- **Phase-aware agents**: Behavior changes based on project phase (reconstruction vs production)
- **License policy**: Block AGPL/SSPL dependencies
- **Error learning**: Auto-capture failures to JSONL
- **Cost tracking**: Alert on expensive agent runs
- **Acceptance criteria**: Every agent prompt must include measurable criteria

Rules are loaded in compact form (~1,500 tokens) at session start. Full rules load contextually when triggered.

### Skills

Skills are domain-specific knowledge packages. Each skill is a `SKILL.md` file with structured instructions, triggers, and references. Skills are the "device drivers" of Cognitive OS -- they tell agents how to interact with specific tools and domains.

Loading priority: project skills > global skills > auto-generated skills.

### Engram

Engram is the persistent memory layer. It stores decisions, discoveries, bug fixes, SDD artifacts, and session summaries across all sessions. Think of it as a knowledge base that the agent builds over time.

### Metrics

Metrics are append-only JSONL files that track agent performance:

| File | Content |
|------|---------|
| `skill-metrics.jsonl` | Execution data per skill invocation |
| `error-learning.jsonl` | Error patterns and recurrence |
| `trust-scores.jsonl` | Per-agent confidence scores |
| `cost-events.jsonl` | Token usage and cost per agent |

### Phases

Every project has a lifecycle phase that affects agent behavior:

| Phase | Behavior |
|-------|----------|
| `reconstruction` | Rewrite over patch, break backwards compat, fix everything |
| `stabilization` | Standards enforced, fix remaining issues |
| `production` | Feature flags required, no breaking changes |
| `maintenance` | Bug fixes and security patches only |

Set in `cognitive-os.yaml` under `project.phase`.

---

## What Works Without Docker?

Most of Cognitive OS runs with zero external dependencies. Here is what each feature requires:

| Feature | Needs Docker? | Needs Python? | Needs Go? |
|---------|---------------|---------------|-----------|
| Core rules + hooks | No | No | No |
| SDD pipeline | No | No | No |
| Safety mesh | No | No | No |
| Error learning | No | No | No |
| cos-test TUI | No | No | Yes (to build) |
| cos CLI | No | No | Yes (to build) |
| Performance monitor | No | Yes | No |
| Cost dashboard | No | Yes | No |
| Testcontainers | Yes | Yes | No |
| Langfuse/Opik | Yes | No | No |
| Agent Bus (Valkey) | Yes | Yes | No |

For a faster start, see the [Quickstart](quickstart.md) guide.

---

## Using with Other IDEs

Cognitive OS is designed for Claude Code but provides partial support for other AI coding IDEs through rule bridging.

### Generate IDE-specific configs

```bash
# For Cursor: creates .cursor/rules/ with individual rule files
bash scripts/ide-bridge.sh cursor

# For Windsurf: creates .windsurfrules with concatenated rules
bash scripts/ide-bridge.sh windsurf

# For Aider: creates .aider.conf.yml with key conventions
bash scripts/ide-bridge.sh aider
```

### What works in other IDEs

Other IDEs receive the **rules layer only** -- behavioral contracts that tell the AI what to do and what to avoid. This includes license policy, acceptance criteria, phase-aware behavior, and quality standards.

### What does NOT work in other IDEs

| Feature | Why It Requires Claude Code |
|---------|----------------------------|
| Safety mesh (hooks) | Hooks need PreToolUse/PostToolUse lifecycle events |
| Error learning | Requires PostToolUse hooks to capture failures |
| Metrics and KPIs | Requires hooks to log execution data |
| Engram memory | Requires MCP server integration |
| SDD pipeline automation | Skills are readable but not enforceable without hooks |
| Trust scores | Requires PostToolUse validation hooks |

For the full compatibility matrix, see [ide-compatibility.md](ide-compatibility.md).

---

## Self-Repair System

COS monitors every agent that completes and automatically adjusts its own behavior. No configuration needed.

After each agent finishes, COS reads its output and extracts a quality score (0-100). Based on that score:

- **Score ≥ 85, five times in a row** — skill is *promoted*: a snapshot of its best state is saved
- **Score 60-84** — no action, skill continues as-is
- **Score < 60 once** — skill is *warned*, still runs normally
- **Score < 60 twice** — skill is *degraded*: next launch uses a cheaper/faster model
- **Score < 60 three times** — skill is *disabled*: launches are blocked until you run `/optimize-skill`

When this happens you'll see messages like:

```
CONSEQUENCE: DEGRADE — model downgraded (sonnet → haiku)
DISPATCH GATE: Skill 'flaky-parser' is DISABLED by consequence engine.
  Run /optimize-skill flaky-parser to fix it.
```

For the full guide — including every message you'll see, how to monitor the metrics files, and how to intervene — read [Self-Repair System Guide](self-repair-guide.md).

---

## Next Steps

- Read the [FAQ](faq.md) for answers to common questions
- Read the [Architecture Overview](architecture.md) for the full system diagram
- Read [How to Extend](how-to-extend.md) to add hooks, rules, and skills
- Read [Overview](overview.md) for the complete component inventory
