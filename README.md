# Cognitive OS

[![CI](https://github.com/luum-home/luum-cognitive-os/actions/workflows/ci.yml/badge.svg)](https://github.com/luum-home/luum-cognitive-os/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](CHANGELOG.md)
<!-- BADGES:START -->
![Dogfood Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/.cognitive-os/metrics/badges/dogfood.json)
![REAL Primitives](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/.cognitive-os/metrics/badges/real-components.json)
![Harness Portability](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/.cognitive-os/metrics/badges/portability.json)
![Hook Wiring](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<org>/<repo>/main/.cognitive-os/metrics/badges/hook-wiring.json)
<!-- BADGES:END -->

Cognitive OS is a **governance layer for coding agents**. It is NOT an agent
framework (like pi-mono), NOT a skill catalog (like hermes-agent), NOT a
dashboard product. It sits ON TOP of your existing AI coding tool (Claude Code,
Codex, Cursor) and prevents fabricated results, destructive operations, and
unverified completions.

Before Cognitive OS: your coding agent can silently fabricate a passing test
result, overwrite a working file with a broken one, claim "done" without
verifying, or exhaust your API budget in an unchecked loop. After Cognitive
OS: a 14-layer safety mesh intercepts each failure mode at the right lifecycle
point — before launch, after completion, or on retry exhaustion.

Concrete examples of what it prevents:

- **Fabricated output** — `claim-validator.sh` blocks agents that report test
  results without running tests (Layer 6, blocks in production mode).
- **Unchecked destructive ops** — `blast-radius.sh` warns before a task
  touches more than a safe scope; `auto-rollback-trigger.sh` reverts on
  retry exhaustion (Layers 2 + 11).
- **Unverified completions** — `trust-score-validator.sh` requires a scored
  Trust Report with evidence before an agent can close a task (Layer 8).
- **Runaway cost loops** — `rate-limiter.sh` caps tool calls, agent spawns,
  and hourly spend before they overflow (Layer 4).

## 5-Minute Demo

```bash
bash scripts/demo-governance.sh
```

The script launches a minimal agent, intercepts a fabricated trust report, and
prints a single-screen summary of what hook fired and what was prevented.
See [docs/manual-tests/proof-paths.md](docs/manual-tests/proof-paths.md) for
the full walkthrough.

## Cognitive OS is NOT

- **NOT an agent framework** — it does not define how agents reason or call
  tools; it governs what they are allowed to do.
- **NOT a skill catalog** — skills are optional extensions, not the product.
- **NOT a multi-agent platform** — squads and teams are experimental layers,
  not the adoption path.
- **NOT an autonomous agent society** — there is no self-directed orchestration
  running without human approval.
- **NOT a dashboard product** — dashboards are optional; governance fires
  whether or not any UI is running.

## Quick Start

```bash
# Install into your project (run from YOUR project directory, not this repo)
cd /path/to/your/project

# Option A: remote
curl -sL https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/install.sh | bash -s -- --harness=claude

# Option B: local clone
/path/to/luum-agent-os/install.sh --harness=claude

# Verify the installation
COGNITIVE_OS_PROJECT_DIR="$PWD" bash /path/to/luum-agent-os/scripts/cos-status.sh

# Initialize project-specific rules and skills (Claude Code only)
claude
> /cognitive-os-init
```

After install, hooks fire automatically on every Claude Code session. No further
configuration is required for the governance layer to be active.

**Keeping up to date**: install git hooks once (`bash scripts/setup-git-hooks.sh`)
and all registered projects update when you `git pull` the source repo.

See [docs/getting-started.md](docs/getting-started.md) for detailed setup and
[docs/migration-from/from-vanilla-claude-code.md](docs/migration-from/from-vanilla-claude-code.md)
for a step-by-step migration from stock Claude Code.

## Why Cognitive OS instead of X?

See [docs/vs-alternatives.md](docs/vs-alternatives.md) for a grounded comparison
against Hermes-agent, pi-mono, Agent Zero, and OpenClaw — including where each
wins and when you should stack Cognitive OS on top rather than replace.

---

### Extended capabilities

The items below are real and available, but they are extensions of the governance
core — not the product center.

**Architecture** — Cognitive OS maps to a traditional OS: kernel
(`cognitive-os.yaml` + `hooks/_lib/`), process scheduler (hook chain), memory
management (Engram), device drivers (skills), system calls (rules), networking
(harness drivers), and self-healing (MAPE-K loop).

**3-Layer model**

```
Layer 1: Cognitive OS (universal)  → .cognitive-os/        (copy to any project)
Layer 2: Project extensions        → {project}/.claude/    (project-specific)
Layer 3: Generated from config     → /cognitive-os-init    (auto-detected)
```

**Optional Docker observability**

```bash
docker compose -f .cognitive-os/docker-compose.cognitive-os.yml up -d
```

Cognitive OS services are completely isolated — zero dependencies on your
application. Remove it with zero impact on your app.

**Configuration** — main config in `cognitive-os.yaml`:
`project.phase`, `project.name`, `project.type`, model routing, quality gates.

**Supported harnesses**: Claude Code, Codex, Cursor. Add a one-file adapter for
any harness that supports lifecycle hooks.

**Roadmap**: [docs/roadmap.md](docs/roadmap.md)
