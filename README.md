# Cognitive OS

> **Read first:** [TRANSPARENCY.md](TRANSPARENCY.md) — what changed before
> public flip, what was preserved, and how to verify any claim in this
> repository against your own clone.

[![CI](https://img.shields.io/badge/CI-local%20(ADR--131)-blue.svg)](docs/adrs/ADR-131-local-ci-migration.md)
[![License: FSL-1.1-MIT](https://img.shields.io/badge/License-FSL--1.1--MIT-orange.svg)](docs/legal/license-faq.md)
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
OS: a 14-layer safety mesh ([details](docs/safety-mesh.md): 11 fire as PreTool/PostTool hooks, 3 are library/conditional) intercepts each failure mode at the right lifecycle
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
- **NOT a dashboard product** — governance fires whether or not any UI is
  running. The operator-facing surface is four cooperating layers (CLI,
  Phoenix traces, Engram Cloud memory, Obsidian/markdown reader), not a
  single web dashboard. See [ADR-172](docs/adrs/ADR-172-multi-surface-ui-architecture.md).

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

**Local CI** (only relevant when contributing to *this* repo): GitHub
Actions workflows are suspended (see ADR-130). The replacement runs
locally via a tracked pre-push hook. Wire it up once after clone:

```bash
bash scripts/install-git-hooks.sh        # pre-push gate (ADR-131)
bash scripts/install-launchd-jobs.sh     # 3 weekly schedules (macOS)
```

After install, `git push` runs `scripts/cos-ci-local.sh quick` (~30s).
Use `COS_PRE_PUSH_TIER=full git push` for a deeper gate, or `--no-verify`
to bypass for a single push. PR review is on demand:
`bash scripts/cos-pr-review.sh prep <PR>`. Full architecture in
[ADR-131](docs/adrs/ADR-131-local-ci-migration.md).

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
(harness drivers), and advisory self-healing patterns (MAPE-K-inspired loop, not autonomous production mutation).

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

**Headless / cloud-worker container** (alternative deployment path)

If you want to evaluate Cognitive OS without installing it onto your shell
profile, or you need a CI / cloud worker that runs the same hooks the
maintainer's machine runs, use the ADR-140 worker container:

```bash
bash scripts/cos-cloud-worker-bootstrap.sh self-test
```

Cross-OS (Linux / macOS / Windows + WSL2). BYOK credentials per ADR-139.
Full stack with engram-cloud replication via `up-full`. See the operator
runbook: [`docs/runbooks/run-cos-in-docker.md`](docs/runbooks/run-cos-in-docker.md).

**Configuration** — main config in `cognitive-os.yaml`:
`project.phase`, `project.name`, `project.type`, model routing, quality gates.

**Supported harnesses**: Claude Code, Codex, Cursor. Add a one-file adapter for
any harness that supports lifecycle hooks.

**Feature status legend**: capabilities throughout the docs are tagged
**REAL** (production, hook-enforced), **DORMANT** (code present but
feature-flagged off / opt-in), or **ASPIRATIONAL** (scaffolded, loop not
yet closed). The reconciliation lives in
[`docs/legal/h1-feature-status-audit.md`](docs/legal/h1-feature-status-audit.md);
the public-facing matrix in [`docs/business/features.md`](docs/business/features.md)
is annotated. In particular, "self-improvement" and "self-healing"
(MAPE-K, singularity) are propose-only and human-gated — autonomous
production mutation is **not** claimed.

**Roadmap**: [docs/roadmap.md](docs/roadmap.md)

**Research catalog**: [docs/research/INDEX.md](docs/research/INDEX.md) — navigable index of ~325 research artifacts (prior-art reports, gap analyses, external-tool deep dives, operational audits, postmortems).

**Contributing**: see [CONTRIBUTING.md](CONTRIBUTING.md) — AI-authorship policy, commit conventions, DCO sign-off.

**License**: FSL-1.1-MIT — see [LICENSE](LICENSE) and the [License FAQ](docs/legal/license-faq.md).
