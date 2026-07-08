---
type: concept-synthesis
source: docs/04-Concepts/root/onboarding-wizard-design.md
status: "DESIGN"
provenance: "Replaces the current `scripts/cos-init.sh`, which only accepts `--minimal|--standard|--full`, with a comprehensive interactive TUI covering all 92 rules, 39 hooks, 94 skills, 26 packages, 21 Docker services, 6 registries, and every cognitive-os.yaml setting."
---

## What it is
Design for an interactive TUI wizard (recommended stack: Go + bubbletea/huh/lipgloss, invoked as `cos setup`/`cos wizard`) that bootstraps a full, customized Cognitive OS install in under 3 minutes via 10 phases of detection and guided configuration.

## Key mechanics
- 10 phases: (1) Detection — auto-detects language, package manager, existing `.claude/`, Docker, git, CI/CD, test framework, monorepo, existing COS version, project name; (2) Core Config — install scope (project/global+project/global-only), project phase (reconstruction/stabilization/production/maintenance, default stabilization), efficiency profile (lean ~6K tokens / standard ~8K / full ~142K, default standard), security profile (minimal 10 hooks / standard 20 / paranoid 39+, default standard), model capability level (2/3/4, default 3); (3) Feature Selection — core (Engram, error learning, crash recovery, smart reader, result truncation, prompt capture — all default on), workflow (SDD, agent escalation, auto-refine, cognitive load, singularity, plan-first), quality (acceptance criteria, DoD gates, trust score, adversarial review, assumption tracking, broken window), agent governance (Agent Teams, Agent Bus/Valkey, KPIs, squad protocol, customizations); (4) Security Tools (optional: Aguara, Semgrep+AI rules, MCP-Scan, Promptfoo, Garak, Trail of Bits, Parry Guard); (5) Infrastructure (optional Docker: Langfuse, LiteLLM, Bifrost, NeMo Guardrails, Valkey, Jupyter, Opik, Cognee, Memu, Automaker, Webhook Trigger — Smart Start on-demand by default); (6) Package Registries (default: cos-official, luum-org, local, cos-builtin, skills.sh, MCP Registry); (7) Git Integration (pre-commit gate, auto-update on pull, post-merge hook); (8) Budget/Resource Limits (defaults: $200/mo, $10/day alert, $0.50/session, 5 max parallel agents, 300s timeout); (9) Project-specific config (Go/Node/Python/Rust build/test/lint/coverage commands); (10) Summary + Install (12-step installation sequence, idempotent).
- Presets for one-click setup: `--solo-dev`, `--team`, `--enterprise`, `--ci`, `--learning`.
- Non-interactive mode: `cos setup --preset team --non-interactive`, `--config cos-setup.yaml`, or individual flags.
- Upgrade path detects an existing install and offers upgrade-in-place / reconfigure / fresh-install.

## Relations & where used
Wraps/calls existing standalone scripts: `cos-init.sh`, `set-security-profile.sh`, `apply-efficiency-profile.sh`, `install-pre-commit.sh`, `setup-git-hooks.sh`, `install-aguara.sh`, `install-garak.sh`, `install-mcp-scan.sh`, `install-promptfoo.sh`, `install-tob-skills.sh`, `upgrade.sh`, `uninstall.sh`. Generates `cognitive-os.yaml`, `.claude/settings.json`, `.claude/rules/cos/`, `.cognitive-os/` directories.

## Status / caveats
Explicitly marked Status: DESIGN (not implemented). Listed future enhancements are all unbuilt: web-based wizard, `cos doctor`, profile export/import, plugin marketplace, guided tour, telemetry opt-in, IDE integration.
