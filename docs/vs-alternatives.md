# Cognitive OS vs Alternatives

This doc answers a single question: **if I already use X, why add Cognitive OS?**

Cognitive OS is a governance layer, not a replacement for your existing coding
tool or agent framework. In most cases the right answer is "use both" — your
current tool handles what it does well, and Cognitive OS adds the verification,
safety, and portability discipline it lacks.

See [ADR-059](adrs/ADR-059-existential-validation.md) and
[docs/business/durable-product-master-plan.md](business/durable-product-master-plan.md)
for the product strategy that drives this framing.

---

## Feature Matrix

| Dimension | Cognitive OS | Hermes-agent | pi-mono | Agent Zero | OpenClaw |
|---|---|---|---|---|---|
| **Primary scope** | Governance layer for coding agents | Self-improving general-purpose agent | TypeScript coding agent framework (monorepo) | Multi-agent autonomous operation | Agent orchestration platform |
| **Orientation** | Depth on governance + verification | Breadth on skills + UX | Framework depth (TypeScript) | Autonomy breadth | Orchestration breadth |
| **Governance hooks** | 14-layer safety mesh (clarification gate → blast-radius → rate-limiter → claim-validator → trust-score → auto-rollback + 8 more) | None dedicated | Limited (no hook chain) | Limited | Limited |
| **Verification gates** | trust-score-validator, claim-validator, confidence-gate, completion-gate, auto-verify | — | — | — | — |
| **Multi-provider portability** | Qwen + Claude + Codex + Cursor via harness adapters (ADR-049, ADR-051) | Any model via OpenRouter / NVIDIA NIM / Nous Portal | Multi-provider LLM API (`pi-ai` package) | Own runtime | Own runtime |
| **Local-first policy** | ADR-060 enforced: no data leaves without explicit opt-in | Partly — cloud runs available | Yes (npm packages, no mandatory cloud) | — | — |
| **Install surface** | pip-first + opt-in Docker (`docker-compose.cognitive-os.yml`) | `curl | bash` (Linux/macOS/WSL2) | npm workspaces monorepo | — | — |
| **Test coverage ratio** | 1.26 tests/file (circa 2026-04) | 0.31 | 0.21 | — | — |
| **Self-improvement loop** | Error-learning JSONL → pattern detection → skill rewrite suggestions | Built-in: skill creation from experience, FTS5 session search | — | — | — |
| **Harness-agnostic** | Yes — one adapter file per harness | No — own TUI / gateway | Partial | No | No |

*Agent Zero and OpenClaw figures are best-effort circa 2026-04; see
[github.com/daveshap/AgentZero](https://github.com/daveshap/AgentZero) and
[github.com/OpenClaw/OpenClaw](https://github.com/OpenClaw/OpenClaw) for
current state.*

---

## Per-Alternative Analysis

### Hermes-agent (Nous Research)

**What Hermes wins on**

- Broader skill catalog — supports 128+ skills across vertical domains (coding,
  research, scheduling, messaging).
- Superior UX — full TUI, Telegram/Discord/Slack/WhatsApp gateway, voice memo
  transcription.
- Honcho dialectic user modeling — builds a persistent model of you across
  sessions.
- Runs on any model via OpenRouter, NVIDIA NIM, Xiaomi MiMo, and 200+ others.
- Scheduled automations built-in; no external cron required.

**What Cognitive OS adds on top of Hermes**

Hermes has no dedicated governance layer. Its skills run without verification
gates, trust reports, or claim validation. If a Hermes skill fabricates a result,
nothing stops it propagating.

Stacking Cognitive OS on a Hermes project adds the 14-layer safety mesh to every
skill invocation. Hooks fire at the harness lifecycle points Hermes exposes;
they do not conflict with Hermes's own skill runner.

**When to use both**: your project needs the skill breadth Hermes provides AND
you want verifiable, audited execution.

See [docs/migration-from/from-hermes.md](migration-from/from-hermes.md).

---

### pi-mono (badlogic)

**What pi-mono wins on**

- Mature TypeScript coding agent framework — clean monorepo with well-separated
  packages: `pi-agent-core` (runtime), `pi-ai` (unified LLM API),
  `pi-coding-agent` (interactive CLI), `pi-tui` (terminal UI).
- Multi-provider LLM API with a single unified interface — swap OpenAI,
  Anthropic, Google without code changes.
- Strong npm ecosystem integration — familiar tooling for TypeScript projects.
- Open session sharing / RL training data pipeline via `pi-share-hf`.

**What Cognitive OS adds on top of pi-mono**

pi-mono is a framework for building agents; it is not opinionated about
operational discipline. There are no completion gates, trust-score requirements,
or blast-radius checks in the framework itself.

Cognitive OS adds the governance layer that fires on the hooks pi-mono exposes.
Because pi-mono is hook-agnostic, the harness adapter is thin (one file).

**When to use both**: you are building or running a TypeScript coding agent on
pi-mono and want measurable, verified execution without building governance
infrastructure yourself.

---

### Agent Zero

**What Agent Zero wins on**

- Stronger autonomous operation — designed for long-horizon tasks with minimal
  human checkpoints.
- Richer multi-agent delegation patterns — hierarchical agent spawning is a
  first-class feature.
- Broad runtime scope — filesystem, shell, browser, code execution.

**What Cognitive OS adds on top of Agent Zero**

Agent Zero's autonomous model is its strength and its governance gap. Long-horizon
autonomous operation without verification gates is where fabricated results and
undetected failures accumulate.

Cognitive OS does not attempt to replicate Agent Zero's autonomy features. It adds
the verification mesh that makes autonomous operation auditable: trust reports,
claim validation, rollback on failure.

**When to use both**: you want Agent Zero's autonomy with Cognitive OS's
verification discipline layered on top. Current integration is best-effort;
the harness adapter for Agent Zero is not yet shipped.

---

### OpenClaw

**What OpenClaw wins on**

- Richer orchestration patterns — composable pipeline primitives.
- Broader plugin ecosystem.
- `hermes claw migrate` command from Hermes suggests active Hermes compatibility.

**What Cognitive OS adds on top of OpenClaw**

Similar to the Agent Zero analysis: orchestration breadth without dedicated
governance depth. Cognitive OS adds the safety mesh on top of OpenClaw's
pipeline execution.

**When to use both**: you rely on OpenClaw's orchestration patterns and want
governance on the output of each step.

---

## When NOT to Use Cognitive OS

Be honest: Cognitive OS adds overhead. Skip it when:

- **Your project is exploratory / throwaway** — governance discipline costs more
  than the risk you are managing.
- **You need a complete autonomous agent** with no human-in-the-loop checkpoints.
  Cognitive OS is designed to keep humans informed, not to operate fully
  unattended.
- **Your harness has no lifecycle hook support** — Cognitive OS requires at least
  PreToolUse and PostToolUse hook registration. If your harness does not support
  hooks, the safety mesh cannot fire.
- **You only need skill breadth** — if your use case is covered by Hermes's 128+
  vertical-domain skills and you do not care about verification, use Hermes alone.

---

## Summary: Where Cognitive OS Wins

Cognitive OS wins on **governance depth, verification evidence, harness
portability, and measurable reliability**. Those properties are:

- harder to fake (you either have a Trust Report or you do not)
- easier to test (each hook has a contract test)
- more durable under provider churn (the governance layer is provider-agnostic)

That is the wedge. Everything else is an extension.
